"""
Similarity Calculation Engine

Functions for calculating musical similarity between songs using various
distance metrics and recommendation algorithms.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Set
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from rich.console import Console

console = Console()


class SimilarityEngine:
    """
    Engine for calculating similarities and generating recommendations.
    """
    
    def __init__(self, similarity_metric: str = 'cosine'):
        """
        Initialize similarity engine.
        
        Args:
            similarity_metric: 'cosine', 'euclidean', or 'combined'
        """
        self.similarity_metric = similarity_metric
        
        if similarity_metric not in ['cosine', 'euclidean', 'combined']:
            raise ValueError(f"Unknown similarity metric: {similarity_metric}")
    
    def calculate_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate similarity matrix for all embeddings.
        
        Args:
            embeddings: 2D array of embeddings (n_samples, n_features)
            
        Returns:
            Similarity matrix (n_samples, n_samples)
        """
        if self.similarity_metric == 'cosine':
            return cosine_similarity(embeddings)
        elif self.similarity_metric == 'euclidean':
            # Convert distances to similarities (higher = more similar)
            distances = euclidean_distances(embeddings)
            max_distance = np.max(distances)
            return 1 - (distances / max_distance)
        elif self.similarity_metric == 'combined':
            # Combine cosine and euclidean similarities
            cosine_sim = cosine_similarity(embeddings)
            
            distances = euclidean_distances(embeddings)
            max_distance = np.max(distances)
            euclidean_sim = 1 - (distances / max_distance)
            
            # Weighted average (cosine gets more weight)
            return 0.7 * cosine_sim + 0.3 * euclidean_sim
    
    def calculate_playlist_similarities(self, 
                                     playlist_embeddings: List[np.ndarray], 
                                     reference_embeddings: np.ndarray,
                                     aggregation: str = 'mean') -> np.ndarray:
        """
        Calculate similarities between a playlist and reference songs.
        
        Args:
            playlist_embeddings: List of embeddings from playlist songs
            reference_embeddings: 2D array of reference embeddings
            aggregation: How to aggregate playlist embeddings ('mean', 'max', 'weighted')
            
        Returns:
            1D array of similarity scores for each reference song
        """
        if not playlist_embeddings:
            raise ValueError("No playlist embeddings provided")
        
        playlist_array = np.array(playlist_embeddings)
        
        if aggregation == 'mean':
            # Simple mean of playlist embeddings
            playlist_centroid = np.mean(playlist_array, axis=0)
            similarities = self._calculate_similarities_to_point(playlist_centroid, reference_embeddings)
            
        elif aggregation == 'max':
            # Maximum similarity to any song in the playlist
            similarities = np.zeros(len(reference_embeddings))
            for playlist_embedding in playlist_embeddings:
                song_similarities = self._calculate_similarities_to_point(playlist_embedding, reference_embeddings)
                similarities = np.maximum(similarities, song_similarities)
                
        elif aggregation == 'weighted':
            # Weighted average based on recency (more recent songs get higher weight)
            weights = np.linspace(0.5, 1.0, len(playlist_embeddings))
            weights = weights / np.sum(weights)
            
            playlist_centroid = np.average(playlist_array, axis=0, weights=weights)
            similarities = self._calculate_similarities_to_point(playlist_centroid, reference_embeddings)
            
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation}")
        
        return similarities
    
    def _calculate_similarities_to_point(self, point: np.ndarray, reference_embeddings: np.ndarray) -> np.ndarray:
        """Calculate similarities from a single point to reference embeddings"""
        if self.similarity_metric == 'cosine':
            return cosine_similarity([point], reference_embeddings)[0]
        elif self.similarity_metric == 'euclidean':
            distances = euclidean_distances([point], reference_embeddings)[0]
            max_distance = np.max(distances)
            return 1 - (distances / max_distance)
        elif self.similarity_metric == 'combined':
            cosine_sim = cosine_similarity([point], reference_embeddings)[0]
            distances = euclidean_distances([point], reference_embeddings)[0]
            max_distance = np.max(distances) if np.max(distances) > 0 else 1
            euclidean_sim = 1 - (distances / max_distance)
            return 0.7 * cosine_sim + 0.3 * euclidean_sim


def calculate_similarity_scores(playlist_embeddings: List[np.ndarray], 
                               reference_embeddings: pd.DataFrame,
                               similarity_metric: str = 'cosine',
                               aggregation: str = 'mean') -> pd.DataFrame:
    """
    Calculate similarity scores between playlist songs and reference library.
    
    Args:
        playlist_embeddings: List of embedding vectors from playlist songs
        reference_embeddings: DataFrame with reference song embeddings
        similarity_metric: Similarity calculation method
        aggregation: How to combine playlist embeddings
        
    Returns:
        DataFrame with similarity scores added
    """
    engine = SimilarityEngine(similarity_metric)
    
    # Get reference embedding vectors
    reference_vectors = np.stack(reference_embeddings['embedding_vector'].values)
    
    # Calculate similarities
    similarities = engine.calculate_playlist_similarities(
        playlist_embeddings, 
        reference_vectors, 
        aggregation
    )
    
    # Add similarity scores to dataframe
    result_df = reference_embeddings.copy()
    result_df['similarity_score'] = similarities
    
    return result_df.sort_values('similarity_score', ascending=False)


def select_top_similar_songs(similarity_df: pd.DataFrame, 
                           existing_uris: Set[str], 
                           n_songs: int,
                           diversity_factor: float = 0.0,
                           min_similarity: float = 0.0) -> List[Dict]:
    """
    Select top N similar songs with optional diversity and filtering.
    
    Args:
        similarity_df: DataFrame with similarity scores
        existing_uris: Set of URIs already in the playlist
        n_songs: Number of songs to select
        diversity_factor: 0-1, higher values increase diversity
        min_similarity: Minimum similarity threshold
        
    Returns:
        List of selected songs with metadata
    """
    selected_songs = []
    selected_embeddings = []
    
    # Filter by minimum similarity and existing songs
    candidates_df = similarity_df[
        (similarity_df['similarity_score'] >= min_similarity) &
        (~similarity_df['song_uri'].isin(existing_uris))
    ].copy()
    
    if len(candidates_df) == 0:
        console.print("⚠️  No suitable candidates found with current filters", style="yellow")
        return []
    
    for _, row in candidates_df.iterrows():
        if len(selected_songs) >= n_songs:
            break
        
        # If diversity factor is 0, just pick top songs
        if diversity_factor == 0.0:
            selected_songs.append({
                'name': row['song_name'],
                'artist': row['artist'],
                'uri': row['song_uri'],
                'similarity_score': row['similarity_score']
            })
        else:
            # Consider diversity - check similarity to already selected songs
            should_add = True
            
            if selected_embeddings and diversity_factor > 0:
                current_embedding = row['embedding_vector']
                
                # Calculate similarity to already selected songs
                selected_array = np.array(selected_embeddings)
                similarities_to_selected = cosine_similarity([current_embedding], selected_array)[0]
                
                # If too similar to already selected songs, skip (based on diversity factor)
                max_similarity_to_selected = np.max(similarities_to_selected)
                diversity_threshold = 1.0 - diversity_factor  # Higher diversity_factor = lower threshold
                
                if max_similarity_to_selected > diversity_threshold:
                    should_add = False
            
            if should_add:
                selected_songs.append({
                    'name': row['song_name'],
                    'artist': row['artist'],
                    'uri': row['song_uri'],
                    'similarity_score': row['similarity_score']
                })
                selected_embeddings.append(row['embedding_vector'])
    
    return selected_songs


def find_similar_songs_by_clustering(reference_embeddings: pd.DataFrame,
                                    target_songs: List[str],
                                    n_clusters: int = 20,
                                    n_songs_per_cluster: int = 5) -> Dict[int, List[Dict]]:
    """
    Find similar songs by clustering the reference library and finding target songs' clusters.
    
    Args:
        reference_embeddings: DataFrame with reference song embeddings
        target_songs: List of song URIs to find similar songs for
        n_clusters: Number of clusters for K-means
        n_songs_per_cluster: Number of songs to return per cluster
        
    Returns:
        Dictionary mapping cluster IDs to song lists
    """
    # Get embeddings and perform clustering
    embeddings = np.stack(reference_embeddings['embedding_vector'].values)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    # Add cluster labels to dataframe
    df_with_clusters = reference_embeddings.copy()
    df_with_clusters['cluster'] = cluster_labels
    
    # Find clusters containing target songs
    target_clusters = set()
    for uri in target_songs:
        target_rows = df_with_clusters[df_with_clusters['song_uri'] == uri]
        if len(target_rows) > 0:
            target_clusters.update(target_rows['cluster'].values)
    
    # Get songs from target clusters
    similar_songs_by_cluster = {}
    
    for cluster_id in target_clusters:
        cluster_songs = df_with_clusters[df_with_clusters['cluster'] == cluster_id]
        
        # Remove target songs from results
        cluster_songs = cluster_songs[~cluster_songs['song_uri'].isin(target_songs)]
        
        # Sort by similarity to cluster center (approximate)
        cluster_center = kmeans.cluster_centers_[cluster_id]
        cluster_embeddings = np.stack(cluster_songs['embedding_vector'].values)
        
        if len(cluster_embeddings) > 0:
            similarities = cosine_similarity([cluster_center], cluster_embeddings)[0]
            cluster_songs = cluster_songs.copy()
            cluster_songs['cluster_similarity'] = similarities
            cluster_songs = cluster_songs.sort_values('cluster_similarity', ascending=False)
            
            # Take top N songs from cluster
            top_songs = []
            for _, row in cluster_songs.head(n_songs_per_cluster).iterrows():
                top_songs.append({
                    'name': row['song_name'],
                    'artist': row['artist'],
                    'uri': row['song_uri'],
                    'cluster_similarity': row['cluster_similarity']
                })
            
            similar_songs_by_cluster[cluster_id] = top_songs
    
    return similar_songs_by_cluster


def analyze_playlist_diversity(embeddings: List[np.ndarray]) -> Dict[str, float]:
    """
    Analyze the diversity of a playlist based on embeddings.
    
    Args:
        embeddings: List of embedding vectors
        
    Returns:
        Dictionary with diversity metrics
    """
    if len(embeddings) < 2:
        return {'diversity_score': 0.0, 'avg_pairwise_distance': 0.0}
    
    embeddings_array = np.array(embeddings)
    
    # Calculate pairwise similarities
    similarities = cosine_similarity(embeddings_array)
    
    # Remove diagonal (self-similarities)
    np.fill_diagonal(similarities, np.nan)
    
    # Calculate diversity metrics
    avg_similarity = np.nanmean(similarities)
    diversity_score = 1.0 - avg_similarity  # Higher diversity = lower average similarity
    
    # Also calculate pairwise distances
    distances = euclidean_distances(embeddings_array)
    np.fill_diagonal(distances, np.nan)
    avg_distance = np.nanmean(distances)
    
    return {
        'diversity_score': diversity_score,
        'avg_similarity': avg_similarity,
        'avg_pairwise_distance': avg_distance,
        'n_songs': len(embeddings)
    }


def recommend_diverse_playlist(reference_embeddings: pd.DataFrame,
                             seed_songs: List[str],
                             target_size: int,
                             diversity_factor: float = 0.3) -> List[Dict]:
    """
    Create a diverse playlist recommendation starting from seed songs.
    
    Args:
        reference_embeddings: DataFrame with reference song embeddings
        seed_songs: List of seed song URIs
        target_size: Target playlist size
        diversity_factor: 0-1, balance between similarity and diversity
        
    Returns:
        List of recommended songs
    """
    # Start with seed songs
    playlist_uris = set(seed_songs)
    playlist_embeddings = []
    
    # Get embeddings for seed songs
    for uri in seed_songs:
        song_rows = reference_embeddings[reference_embeddings['song_uri'] == uri]
        if len(song_rows) > 0:
            playlist_embeddings.append(song_rows.iloc[0]['embedding_vector'])
    
    recommended_songs = []
    
    # Iteratively add songs
    while len(playlist_uris) < target_size:
        # Calculate similarities to current playlist
        if playlist_embeddings:
            engine = SimilarityEngine('cosine')
            reference_vectors = np.stack(reference_embeddings['embedding_vector'].values)
            similarities = engine.calculate_playlist_similarities(
                playlist_embeddings, 
                reference_vectors, 
                'mean'
            )
            
            result_df = reference_embeddings.copy()
            result_df['similarity_score'] = similarities
            
            # Select next song with diversity consideration
            candidates = select_top_similar_songs(
                result_df, 
                playlist_uris, 
                1,  # Just get one song at a time
                diversity_factor=diversity_factor
            )
            
            if candidates:
                next_song = candidates[0]
                recommended_songs.append(next_song)
                playlist_uris.add(next_song['uri'])
                
                # Add embedding to playlist
                song_row = reference_embeddings[reference_embeddings['song_uri'] == next_song['uri']]
                if len(song_row) > 0:
                    playlist_embeddings.append(song_row.iloc[0]['embedding_vector'])
            else:
                # No more suitable candidates
                break
        else:
            break
    
    return recommended_songs