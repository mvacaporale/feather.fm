#!/usr/bin/env python3
"""
Playlist Enhancement Script

This script analyzes an existing Spotify playlist and recommends similar songs
based on audio embeddings. It can either append to the existing playlist or 
create a new enhanced playlist.

Usage:
    python enhance_playlist.py <playlist_url> --count <n> [--mode append|new] [--output-name "Enhanced Playlist"]
"""

import argparse
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.table import Table

# Import existing modules
from playlist_reader import get_playlist_tracks, extract_playlist_id
from create_playlist import create_spotify_playlist, SpotifyPlaylistCreator

# Import new utility modules
from utils.embedding_manager import load_reference_embeddings, get_or_create_embedding, batch_generate_embeddings
from utils.similarity_engine import calculate_similarity_scores, select_top_similar_songs, analyze_playlist_diversity
from utils.common import extract_spotify_id, validate_spotify_uri, format_duration

console = Console()




def create_enhanced_playlist(original_tracks: List[Dict], 
                           recommended_tracks: List[Dict], 
                           playlist_name: str,
                           mode: str = 'new') -> bool:
    """
    Create or update playlist with recommended songs.
    
    Args:
        original_tracks: Original playlist tracks
        recommended_tracks: Recommended tracks to add
        playlist_name: Name for the playlist
        mode: 'new' to create new playlist, 'append' to add to existing
        
    Returns:
        True if successful, False otherwise
    """
    def convert_url_to_uri(url_or_uri: str) -> str:
        """Convert Spotify URL to URI format"""
        if url_or_uri.startswith('spotify:'):
            return url_or_uri
        # Extract track ID from URL and convert to URI
        import re
        match = re.search(r'/track/([a-zA-Z0-9]{22})', url_or_uri)
        if match:
            return f"spotify:track:{match.group(1)}"
        return url_or_uri  # Return as-is if can't convert
    
    try:
        if mode == 'new':
            # Create new playlist with both original and recommended tracks
            all_tracks = original_tracks + recommended_tracks
            track_uris = [convert_url_to_uri(track['uri']) for track in all_tracks]
            
            result = create_spotify_playlist(playlist_name, track_uris)
            if result:
                console.print(f"✓ Created new playlist '{playlist_name}' with {len(all_tracks)} tracks", style="green")
                return True
                
        elif mode == 'append':
            # Add recommended tracks to existing playlist
            # Note: This would require additional Spotify API implementation
            # For now, we'll create a new playlist as fallback
            console.print("⚠️  Append mode not yet implemented, creating new playlist instead", style="yellow")
            return create_enhanced_playlist(original_tracks, recommended_tracks, 
                                          f"{playlist_name} Enhanced", 'new')
            
        return False
        
    except Exception as e:
        console.print(f"❌ Error creating playlist: {e}", style="red")
        return False


def enhance_playlist(playlist_url: str, n_songs: int, mode: str = 'new', 
                    output_name: Optional[str] = None, 
                    diversity_factor: float = 0.0,
                    similarity_metric: str = 'cosine') -> bool:
    """
    Main function to enhance a playlist with similar songs.
    
    Args:
        playlist_url: Spotify playlist URL or ID
        n_songs: Number of songs to recommend
        mode: 'new' or 'append'
        output_name: Custom name for output playlist
        diversity_factor: 0-1, higher values increase diversity in recommendations
        similarity_metric: Similarity calculation method
        
    Returns:
        True if successful, False otherwise
    """
    console.print(f"🎵 Starting playlist enhancement process...", style="bold blue")
    
    # Step 1: Extract playlist tracks
    console.print("📋 Reading original playlist...")
    try:
        tracks = get_playlist_tracks(playlist_url)
        if not tracks:
            console.print("❌ No tracks found in playlist", style="red")
            return False
            
        console.print(f"✓ Found {len(tracks)} tracks in original playlist", style="green")
        
    except Exception as e:
        console.print(f"❌ Error reading playlist: {e}", style="red")
        return False
    
    # Step 2: Load reference embeddings
    console.print("📊 Loading reference embeddings...")
    try:
        reference_df = load_reference_embeddings()
    except Exception as e:
        console.print(f"❌ Error loading reference embeddings: {e}", style="red")
        return False
    
    # Step 3: Normalize track data structure
    console.print("🔧 Normalizing track data...")
    normalized_tracks = []
    for track in tracks:
        normalized_track = track.copy()
        
        # Handle different artist field formats
        if 'artists' in track and isinstance(track['artists'], list):
            normalized_track['artist'] = ', '.join(track['artists'])
        elif 'artist' not in track:
            normalized_track['artist'] = 'Unknown Artist'
            
        # Ensure URI field exists
        if 'uri' not in track:
            if 'external_url' in track:
                # Extract track ID from URL and create URI
                import re
                match = re.search(r'/track/([a-zA-Z0-9]{22})', track['external_url'])
                if match:
                    normalized_track['uri'] = f"spotify:track:{match.group(1)}"
                else:
                    console.print(f"⚠️  Could not extract URI for {track['name']}", style="yellow")
                    continue
            else:
                console.print(f"⚠️  No URI or external_url for {track['name']}", style="yellow")
                continue
        
        normalized_tracks.append(normalized_track)
    
    console.print(f"✓ Normalized {len(normalized_tracks)} tracks", style="green")
    
    # Step 4: Match playlist tracks against reference library
    console.print("🔍 Matching playlist tracks with reference library...")
    playlist_embeddings = []
    existing_uris = set()
    matched_tracks = []
    unmatched_tracks = []
    
    for track in normalized_tracks:
        existing_uris.add(track['uri'])
        
        # Try to find this track in the reference library
        matched = reference_df[
            (reference_df['song_name'].str.lower() == track['name'].lower()) |
            (reference_df['song_uri'] == track['uri'])
        ]
        
        if len(matched) > 0:
            # Found in reference library
            embedding = matched.iloc[0]['embedding_vector']
            playlist_embeddings.append(embedding)
            matched_tracks.append(track)
            console.print(f"✓ Found {track['name']} by {track['artist']} in reference library", style="green")
        else:
            unmatched_tracks.append(track)
            console.print(f"⚠️  {track['name']} by {track['artist']} not in reference library", style="yellow")
    
    # If we have some matches, proceed. If no matches, we could optionally analyze the unmatched tracks
    if not playlist_embeddings:
        console.print("❌ No playlist tracks found in reference library", style="red")
        
        # Optional: Ask user if they want to analyze unmatched tracks
        console.print("Would you like to analyze the unmatched tracks? This will download previews and may take time.", style="cyan")
        console.print("For now, we'll skip this to keep the demo fast.", style="yellow")
        return False
        
    console.print(f"✓ Found {len(matched_tracks)} playlist tracks in reference library", style="green")
    if unmatched_tracks:
        console.print(f"ℹ️  {len(unmatched_tracks)} tracks not in reference library (will be excluded from analysis)", style="blue")
    
    # Step 5: Analyze playlist diversity
    diversity_stats = analyze_playlist_diversity(playlist_embeddings)
    console.print(f"📈 Playlist diversity score: {diversity_stats['diversity_score']:.3f}", style="cyan")
    
    # Step 6: Calculate similarities
    console.print("🔍 Calculating song similarities...")
    similarity_df = calculate_similarity_scores(
        playlist_embeddings, 
        reference_df, 
        similarity_metric=similarity_metric
    )
    
    # Step 7: Select recommendations with diversity consideration
    console.print(f"🎯 Selecting top {n_songs} recommendations...")
    recommended_songs = select_top_similar_songs(
        similarity_df, 
        existing_uris, 
        n_songs,
        diversity_factor=diversity_factor
    )
    
    if not recommended_songs:
        console.print("❌ No suitable recommendations found", style="red")
        return False
    
    # Display recommendations
    table = Table(title="🎵 Recommended Songs")
    table.add_column("Song", style="cyan", max_width=30)
    table.add_column("Artist", style="magenta", max_width=25) 
    table.add_column("Similarity", style="green", justify="right")
    
    for song in recommended_songs:
        table.add_row(
            song['name'], 
            song['artist'], 
            f"{song['similarity_score']:.3f}"
        )
    
    console.print(table)
    
    # Step 8: Create enhanced playlist
    playlist_name = output_name or f"{normalized_tracks[0].get('playlist_name', 'Playlist')} Enhanced"
    
    console.print(f"📝 Creating enhanced playlist...")
    success = create_enhanced_playlist(normalized_tracks, recommended_songs, playlist_name, mode)
    
    if success:
        console.print(f"🎉 Successfully enhanced playlist with {len(recommended_songs)} new songs!", style="bold green")
        
        # Show final stats
        console.print(f"📊 Final playlist: {len(normalized_tracks)} original + {len(recommended_songs)} new = {len(normalized_tracks) + len(recommended_songs)} total tracks", style="blue")
        
        return True
    else:
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Enhance Spotify playlists with AI-recommended similar songs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enhance_playlist.py "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M" --count 10
  python enhance_playlist.py 37i9dQZF1DXcBWIGoYBM5M -n 5 --mode append
  python enhance_playlist.py playlist_id --count 15 --output-name "My Enhanced Mix"
        """
    )
    
    parser.add_argument(
        "playlist_url",
        help="Spotify playlist URL or playlist ID"
    )
    
    parser.add_argument(
        "--count", "-n",
        type=int,
        required=True,
        help="Number of songs to add to the playlist"
    )
    
    parser.add_argument(
        "--mode",
        choices=["new", "append"],
        default="new",
        help="Mode: 'new' creates a new playlist, 'append' adds to existing (default: new)"
    )
    
    parser.add_argument(
        "--output-name",
        help="Custom name for the output playlist (default: '[Original Name] Enhanced')"
    )
    
    parser.add_argument(
        "--diversity",
        type=float,
        default=0.0,
        help="Diversity factor (0.0-1.0): higher values increase variety in recommendations (default: 0.0)"
    )
    
    parser.add_argument(
        "--similarity-metric",
        choices=["cosine", "euclidean", "combined"],
        default="cosine",
        help="Similarity calculation method (default: cosine)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.count <= 0:
        console.print("❌ Count must be a positive number", style="red")
        return 1
    
    if not (0.0 <= args.diversity <= 1.0):
        console.print("❌ Diversity factor must be between 0.0 and 1.0", style="red")
        return 1
    
    # Run enhancement
    try:
        success = enhance_playlist(
            args.playlist_url,
            args.count,
            args.mode,
            args.output_name,
            args.diversity,
            args.similarity_metric
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        console.print("\n⏹️  Process interrupted by user", style="yellow")
        return 1
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="red")
        return 1


if __name__ == "__main__":
    sys.exit(main())