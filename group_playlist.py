#!/usr/bin/env python3

import argparse
import csv
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import seaborn as sns
import ast
from pathlib import Path
from create_playlist import SpotifyPlaylistCreator
import hdbscan

def load_clustered_csv(csv_path):
    """
    Load already clustered songs from CSV file.
    
    Args:
        csv_path (str): Path to the CSV file with clustering results
        
    Returns:
        pd.DataFrame: DataFrame with song info and cluster labels
    """
    try:
        df = pd.read_csv(csv_path)
        required_columns = ['song_name', 'artist', 'song_uri', 'cluster']
        
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        print(f"Loaded {len(df)} songs with clusters from '{csv_path}'")
        print(f"Found {df['cluster'].nunique()} unique clusters")
        
        return df
        
    except Exception as e:
        raise Exception(f"Error loading clustered CSV: {e}")

def convert_http_to_spotify_uri(http_url):
    """
    Convert HTTP Spotify URL to Spotify URI format.
    
    Args:
        http_url (str): HTTP URL like 'https://open.spotify.com/track/0B67ukIysEipoSjuDGtNMM'
        
    Returns:
        str: Spotify URI like 'spotify:track:0B67ukIysEipoSjuDGtNMM'
    """
    if http_url.startswith('spotify:track:'):
        return http_url
    
    if 'open.spotify.com/track/' in http_url:
        track_id = http_url.split('track/')[-1].split('?')[0]
        return f'spotify:track:{track_id}'
    
    return None

def load_embeddings_from_csv(csv_path):
    """
    Load embeddings from CSV file with the format:
    song_name,artist,song_uri,embedding
    
    Args:
        csv_path (str): Path to the CSV file
        
    Returns:
        tuple: (dataframe with song info, numpy array of embeddings)
    """
    songs_data = []
    embeddings = []
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # Parse the embedding string back to a list of floats
            try:
                embedding = ast.literal_eval(row['embedding'])
                embeddings.append(embedding)
                
                songs_data.append({
                    'song_name': row['song_name'],
                    'artist': row['artist'],
                    'song_uri': row['song_uri']
                })
            except (ValueError, SyntaxError) as e:
                print(f"Error parsing embedding for {row['song_name']}: {e}")
                continue
    
    # Convert to numpy array and pandas DataFrame
    embeddings_array = np.array(embeddings)
    songs_df = pd.DataFrame(songs_data)
    
    print(f"Loaded {len(songs_data)} songs with {embeddings_array.shape[1]}-dimensional embeddings from {csv_path}")
    
    return songs_df, embeddings_array

def load_and_concatenate_embeddings(csv_paths):
    """
    Load embeddings from multiple CSV files and concatenate them for the same songs.
    
    Args:
        csv_paths (list): List of paths to CSV files with embeddings
        
    Returns:
        tuple: (dataframe with song info, numpy array of concatenated embeddings)
    """
    if len(csv_paths) == 1:
        return load_embeddings_from_csv(csv_paths[0])
    
    print(f"Loading embeddings from {len(csv_paths)} CSV files...")
    
    # Load data from all CSV files
    all_songs_data = {}  # key: (song_name, artist), value: {song_info, embeddings_list}
    
    for i, csv_path in enumerate(csv_paths):
        print(f"Processing file {i+1}/{len(csv_paths)}: {csv_path}")
        songs_df, embeddings_array = load_embeddings_from_csv(csv_path)
        
        for idx, row in songs_df.iterrows():
            song_key = (row['song_name'], row['artist'])
            embedding = embeddings_array[idx]
            
            if song_key not in all_songs_data:
                all_songs_data[song_key] = {
                    'song_info': {
                        'song_name': row['song_name'],
                        'artist': row['artist'],
                        'song_uri': row['song_uri']
                    },
                    'embeddings': [embedding]
                }
            else:
                all_songs_data[song_key]['embeddings'].append(embedding)
    
    # Filter songs that have embeddings from all CSV files
    complete_songs = {}
    for song_key, data in all_songs_data.items():
        if len(data['embeddings']) == len(csv_paths):
            complete_songs[song_key] = data
        else:
            print(f"Warning: Song '{data['song_info']['song_name']}' by '{data['song_info']['artist']}' "
                  f"only found in {len(data['embeddings'])}/{len(csv_paths)} files - skipping")
    
    if not complete_songs:
        raise ValueError("No songs found with embeddings in all CSV files")
    
    # Create final dataset with concatenated embeddings
    final_songs_data = []
    concatenated_embeddings = []
    
    for song_key, data in complete_songs.items():
        final_songs_data.append(data['song_info'])
        # Concatenate all embeddings for this song
        concatenated_embedding = np.concatenate(data['embeddings'])
        concatenated_embeddings.append(concatenated_embedding)
    
    # Convert to numpy array and pandas DataFrame
    embeddings_array = np.array(concatenated_embeddings)
    songs_df = pd.DataFrame(final_songs_data)
    
    print(f"\nSuccessfully matched {len(final_songs_data)} songs across all {len(csv_paths)} files")
    print(f"Concatenated embedding dimension: {embeddings_array.shape[1]} "
          f"(average {embeddings_array.shape[1] // len(csv_paths)} per file)")
    
    return songs_df, embeddings_array

def find_optimal_k(embeddings, max_k=10):
    """
    Find optimal number of clusters using elbow method and silhouette score.
    
    Args:
        embeddings (np.array): The embedding vectors
        max_k (int): Maximum number of clusters to test
        
    Returns:
        tuple: (optimal_k, inertias, silhouette_scores)
    """
    inertias = []
    silhouette_scores = []
    k_range = range(2, min(max_k + 1, len(embeddings)))
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        inertias.append(kmeans.inertia_)
        silhouette_scores.append(silhouette_score(embeddings, cluster_labels))
    
    # Find optimal k (highest silhouette score)
    optimal_k = k_range[np.argmax(silhouette_scores)]
    
    return optimal_k, list(k_range), inertias, silhouette_scores

def perform_hdbscan_clustering(songs_df, embeddings, min_cluster_size=5, min_samples=None, cluster_selection_epsilon=0.0, normalize=True):
    """
    Perform HDBSCAN clustering on the embeddings.
    
    Args:
        songs_df (pd.DataFrame): DataFrame with song information
        embeddings (np.array): The embedding vectors
        min_cluster_size (int): Minimum cluster size for HDBSCAN
        min_samples (int): Number of samples in a neighborhood for a point to be core
        cluster_selection_epsilon (float): Distance threshold for cluster selection
        normalize (bool): Whether to normalize embeddings before clustering
        
    Returns:
        tuple: (songs_df with cluster labels, clusterer model, scaler)
    """
    # Normalize embeddings if requested
    if normalize:
        scaler = StandardScaler()
        embeddings_scaled = scaler.fit_transform(embeddings)
    else:
        scaler = None
        embeddings_scaled = embeddings
    
    # Perform HDBSCAN clustering
    print(f"Performing HDBSCAN clustering with min_cluster_size={min_cluster_size}...")
    if min_samples is None:
        min_samples = min_cluster_size
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=cluster_selection_epsilon
    )
    cluster_labels = clusterer.fit_predict(embeddings_scaled)
    
    # Add cluster labels to the dataframe
    songs_df_clustered = songs_df.copy()
    songs_df_clustered['cluster'] = cluster_labels
    
    # Calculate clustering statistics
    n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
    n_noise = list(cluster_labels).count(-1)
    
    print(f"Number of clusters: {n_clusters}")
    print(f"Number of noise points: {n_noise}")
    
    # Show actual cluster sizes
    if n_clusters > 0:
        cluster_sizes = {}
        for label in set(cluster_labels):
            if label != -1:  # Exclude noise
                cluster_sizes[label] = list(cluster_labels).count(label)
        
        print("Actual cluster sizes:")
        for cluster_id, size in sorted(cluster_sizes.items()):
            print(f"  Cluster {cluster_id}: {size} songs")
    
    # Check if the minimum cluster size constraint was respected
    if n_clusters > 0:
        min_actual_cluster_size = min(cluster_sizes.values()) if cluster_sizes else 0
        if min_actual_cluster_size < min_cluster_size:
            print(f"⚠️  Warning: Found clusters smaller than min_cluster_size={min_cluster_size}")
        else:
            print(f"✅ All clusters meet minimum size requirement of {min_cluster_size}")
    
    # Calculate silhouette score if we have more than one cluster
    if n_clusters > 1:
        # Exclude noise points (-1) from silhouette calculation
        mask = cluster_labels != -1
        if np.sum(mask) > 1:
            silhouette_avg = silhouette_score(embeddings_scaled[mask], cluster_labels[mask])
            print(f"Silhouette Score (excluding noise): {silhouette_avg:.3f}")
    
    return songs_df_clustered, clusterer, scaler

def perform_kmeans_clustering(songs_df, embeddings, n_clusters=None, normalize=True):
    """
    Perform K-means clustering on the embeddings.
    
    Args:
        songs_df (pd.DataFrame): DataFrame with song information
        embeddings (np.array): The embedding vectors
        n_clusters (int): Number of clusters. If None, will find optimal k
        normalize (bool): Whether to normalize embeddings before clustering
        
    Returns:
        tuple: (songs_df with cluster labels, kmeans model, scaler)
    """
    # Normalize embeddings if requested
    if normalize:
        scaler = StandardScaler()
        embeddings_scaled = scaler.fit_transform(embeddings)
    else:
        scaler = None
        embeddings_scaled = embeddings
    
    # Find optimal number of clusters if not specified
    if n_clusters is None:
        print("Finding optimal number of clusters...")
        optimal_k, k_range, inertias, silhouette_scores = find_optimal_k(embeddings_scaled)
        print(f"Optimal number of clusters: {optimal_k}")
        n_clusters = optimal_k
        
        # Plot elbow curve and silhouette scores
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        ax1.plot(k_range, inertias, 'bo-')
        ax1.set_xlabel('Number of Clusters (k)')
        ax1.set_ylabel('Inertia')
        ax1.set_title('Elbow Method')
        ax1.grid(True)
        
        ax2.plot(k_range, silhouette_scores, 'ro-')
        ax2.set_xlabel('Number of Clusters (k)')
        ax2.set_ylabel('Silhouette Score')
        ax2.set_title('Silhouette Score vs k')
        ax2.grid(True)
        ax2.axvline(x=optimal_k, color='g', linestyle='--', label=f'Optimal k={optimal_k}')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig('cluster_optimization.png', dpi=300, bbox_inches='tight')
        print("Cluster optimization plots saved to 'cluster_optimization.png'")
        plt.close()
    
    # Perform K-means clustering
    print(f"Performing K-means clustering with {n_clusters} clusters...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings_scaled)
    
    # Add cluster labels to the dataframe
    songs_df_clustered = songs_df.copy()
    songs_df_clustered['cluster'] = cluster_labels
    
    # Calculate silhouette score
    silhouette_avg = silhouette_score(embeddings_scaled, cluster_labels)
    print(f"Silhouette Score: {silhouette_avg:.3f}")
    
    return songs_df_clustered, kmeans, scaler

def analyze_clusters(songs_df_clustered):
    """
    Analyze and display cluster information.
    
    Args:
        songs_df_clustered (pd.DataFrame): DataFrame with cluster labels
    """
    print("\n" + "="*50)
    print("CLUSTER ANALYSIS")
    print("="*50)
    
    # Cluster sizes
    cluster_counts = songs_df_clustered['cluster'].value_counts().sort_index()
    print(f"\nCluster sizes:")
    for cluster_id, count in cluster_counts.items():
        print(f"  Cluster {cluster_id}: {count} songs")
    
    # Display songs in each cluster
    print(f"\nSongs by cluster:")
    for cluster_id in sorted(songs_df_clustered['cluster'].unique()):
        cluster_songs = songs_df_clustered[songs_df_clustered['cluster'] == cluster_id]
        print(f"\n--- Cluster {cluster_id} ({len(cluster_songs)} songs) ---")
        
        for _, song in cluster_songs.iterrows():
            print(f"  • {song['song_name']} - {song['artist']}")

def create_playlists_from_clusters(songs_df_clustered, base_name="Cluster"):
    """
    Create Spotify playlists for each cluster using a single authentication.
    
    Args:
        songs_df_clustered (pd.DataFrame): DataFrame with cluster labels
        base_name (str): Base name for the playlists
    """
    print("\n" + "="*50)
    print("CREATING SPOTIFY PLAYLISTS")
    print("="*50)
    
    # Prepare playlist data for batch creation
    playlist_data = []
    
    for cluster_id in sorted(songs_df_clustered['cluster'].unique()):
        cluster_songs = songs_df_clustered[songs_df_clustered['cluster'] == cluster_id]
        
        # Convert HTTP URLs to Spotify URIs
        track_uris = []
        invalid_uris = []
        
        for _, song in cluster_songs.iterrows():
            spotify_uri = convert_http_to_spotify_uri(song['song_uri'])
            if spotify_uri:
                track_uris.append(spotify_uri)
            else:
                invalid_uris.append(song['song_uri'])
        
        if invalid_uris:
            print(f"Warning: {len(invalid_uris)} invalid URIs in cluster {cluster_id}")
        
        if not track_uris:
            print(f"Skipping cluster {cluster_id}: No valid Spotify URIs")
            continue
        
        # Add to playlist data
        playlist_name = f"{base_name} {cluster_id}"
        description = f"Auto-generated playlist from K-means clustering. Contains {len(track_uris)} similar songs."
        
        playlist_data.append({
            'name': playlist_name,
            'track_uris': track_uris,
            'description': description,
            'public': False  # Make playlists private by default
        })
    
    if not playlist_data:
        print("\n❌ No valid playlists to create.")
        return []
    
    # Create all playlists with single authentication
    try:
        print(f"\nAuthenticating with Spotify for {len(playlist_data)} playlists...")
        spotify_creator = SpotifyPlaylistCreator()
        results = spotify_creator.create_multiple_playlists(playlist_data)
        
        # Process results
        created_playlists = []
        for i, result in enumerate(results):
            if 'failed' not in result:
                created_playlists.append({
                    'cluster_id': i,
                    'playlist_name': result['name'],
                    'playlist_id': result['id'],
                    'playlist_url': result['url'],
                    'track_count': result['tracks_added']
                })
        
        # Summary
        if created_playlists:
            print(f"\n🎉 Successfully created {len(created_playlists)} playlists!")
            print("\nPlaylist Summary:")
            for playlist in created_playlists:
                print(f"  • Cluster {playlist['cluster_id']}: {playlist['playlist_name']} ({playlist['track_count']} tracks)")
        else:
            print("\n❌ No playlists were created.")
        
        return created_playlists
        
    except Exception as e:
        print(f"❌ Failed to authenticate or create playlists: {e}")
        return []

def save_results(songs_df_clustered, output_path='clustered_songs.csv'):
    """
    Save clustering results to CSV.
    
    Args:
        songs_df_clustered (pd.DataFrame): DataFrame with cluster labels
        output_path (str): Output file path
    """
    songs_df_clustered.to_csv(output_path, index=False)
    print(f"\nClustering results saved to '{output_path}'")

def main():
    parser = argparse.ArgumentParser(description='Perform clustering analysis on song embeddings or create playlists from existing clusters')
    parser.add_argument('csv_files', nargs='+', help='Path(s) to CSV file(s) with embeddings or clustered results. Multiple files will have their embeddings concatenated.')
    parser.add_argument('-k', '--clusters', type=int, default=None,
                        help='Number of clusters for K-means (if not specified, optimal k will be found)')
    parser.add_argument('--algorithm', choices=['kmeans', 'hdbscan'], default='kmeans',
                        help='Clustering algorithm to use (default: kmeans)')
    parser.add_argument('--min-cluster-size', type=int, default=3,
                        help='Minimum cluster size for HDBSCAN (default: 3)')
    parser.add_argument('--hdbscan-epsilon', type=float, default=0.0,
                        help='HDBSCAN epsilon for more/fewer clusters: higher=fewer clusters, lower=more clusters (default: 0.0)')
    parser.add_argument('--no-normalize', action='store_true',
                        help='Skip normalization of embeddings')
    parser.add_argument('-o', '--output', default='clustered_songs.csv',
                        help='Output CSV file (default: clustered_songs.csv)')
    parser.add_argument('--create-playlists', action='store_true',
                        help='Create Spotify playlists for each cluster')
    parser.add_argument('--playlist-name', default='Music Cluster',
                        help='Base name for created playlists (default: Music Cluster)')
    parser.add_argument('--playlist-only', action='store_true',
                        help='Create playlists from existing clustered CSV (skip clustering step)')
    parser.add_argument('--from-clustered', action='store_true',
                        help='Alias for --playlist-only (for backwards compatibility)')
    
    args = parser.parse_args()
    
    # Handle aliases
    if args.from_clustered:
        args.playlist_only = True
    
    # Check if input files exist
    for csv_file in args.csv_files:
        if not Path(csv_file).exists():
            print(f"Error: File '{csv_file}' not found")
            return
    
    # Playlist-only mode: load clustered CSV and create playlists
    if args.playlist_only:
        if len(args.csv_files) > 1:
            print("Error: Playlist-only mode supports only one CSV file")
            return
        
        csv_file = args.csv_files[0]
        print(f"Loading clustered songs from '{csv_file}'...")
        try:
            songs_df_clustered = load_clustered_csv(csv_file)
            
            # Show cluster summary
            print(f"\n" + "="*50)
            print("CLUSTER SUMMARY")
            print("="*50)
            cluster_counts = songs_df_clustered['cluster'].value_counts().sort_index()
            for cluster_id, count in cluster_counts.items():
                print(f"  Cluster {cluster_id}: {count} songs")
            
            # Create playlists
            create_playlists_from_clusters(songs_df_clustered, args.playlist_name)
            
        except Exception as e:
            print(f"Error: {e}")
        return
    
    # Regular clustering mode
    if len(args.csv_files) == 1:
        print(f"Loading embeddings from '{args.csv_files[0]}'...")
        songs_df, embeddings = load_embeddings_from_csv(args.csv_files[0])
    else:
        print(f"Loading and concatenating embeddings from {len(args.csv_files)} files...")
        songs_df, embeddings = load_and_concatenate_embeddings(args.csv_files)
    
    if len(songs_df) == 0:
        print("No valid embeddings found in the CSV file")
        return
    
    # Perform clustering
    normalize = not args.no_normalize
    
    if args.algorithm == 'kmeans':
        songs_df_clustered, model, scaler = perform_kmeans_clustering(
            songs_df, embeddings, n_clusters=args.clusters, normalize=normalize
        )
    elif args.algorithm == 'hdbscan':
        songs_df_clustered, model, scaler = perform_hdbscan_clustering(
            songs_df, embeddings, min_cluster_size=args.min_cluster_size, 
            cluster_selection_epsilon=args.hdbscan_epsilon, normalize=normalize
        )
    else:
        raise ValueError(f"Unknown algorithm: {args.algorithm}")
    
    # Analyze results
    analyze_clusters(songs_df_clustered)
    
    # Create playlists if requested
    if args.create_playlists:
        create_playlists_from_clusters(songs_df_clustered, args.playlist_name)
    
    # Save results
    save_results(songs_df_clustered, args.output)

if __name__ == "__main__":
    main()