"""
Embedding Management Utilities

Centralized functions for loading, caching, and generating embeddings
across the feather.fm system.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from rich.console import Console

# Import existing modules
from audio_analysis import get_audio_embeddings
from enhanced_preview_downloader import search_and_download

console = Console()


class EmbeddingCache:
    """
    Cache for storing and retrieving embeddings to avoid recomputation.
    """
    
    def __init__(self, cache_file: str = "embedding_cache.csv"):
        self.cache_file = cache_file
        self._cache = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load existing cache from disk"""
        if os.path.exists(self.cache_file):
            try:
                df = pd.read_csv(self.cache_file)
                for _, row in df.iterrows():
                    key = f"{row['song_name']}|{row['artist']}"
                    self._cache[key] = {
                        'embedding': np.fromstring(row['embedding'].strip('[]'), sep=', '),
                        'provider': row.get('provider', 'unknown')
                    }
                console.print(f"✓ Loaded {len(self._cache)} embeddings from cache", style="green")
            except Exception as e:
                console.print(f"⚠️  Could not load embedding cache: {e}", style="yellow")
    
    def get(self, song_name: str, artist: str, provider: str = 'gemini') -> Optional[np.ndarray]:
        """Get embedding from cache"""
        key = f"{song_name}|{artist}"
        cached = self._cache.get(key)
        if cached and cached['provider'] == provider:
            return cached['embedding']
        return None
    
    def set(self, song_name: str, artist: str, embedding: np.ndarray, provider: str = 'gemini'):
        """Store embedding in cache"""
        key = f"{song_name}|{artist}"
        self._cache[key] = {
            'embedding': embedding,
            'provider': provider
        }
    
    def save(self):
        """Save cache to disk"""
        try:
            rows = []
            for key, data in self._cache.items():
                song_name, artist = key.split('|', 1)
                rows.append({
                    'song_name': song_name,
                    'artist': artist,
                    'embedding': str(data['embedding'].tolist()),
                    'provider': data['provider']
                })
            
            df = pd.DataFrame(rows)
            df.to_csv(self.cache_file, index=False)
            console.print(f"✓ Saved {len(rows)} embeddings to cache", style="green")
        except Exception as e:
            console.print(f"❌ Error saving embedding cache: {e}", style="red")


# Global cache instance
_embedding_cache = EmbeddingCache()


def load_reference_embeddings(embeddings_file: str = "gemini_embeddings.csv") -> pd.DataFrame:
    """
    Load reference embeddings from CSV file with improved error handling.
    
    Args:
        embeddings_file: Path to the embeddings CSV file
        
    Returns:
        DataFrame with reference embeddings
        
    Raises:
        FileNotFoundError: If embeddings file doesn't exist
        ValueError: If embeddings file format is invalid
    """
    if not os.path.exists(embeddings_file):
        raise FileNotFoundError(f"Reference embeddings file '{embeddings_file}' not found")
    
    try:
        df = pd.read_csv(embeddings_file)
        
        # Validate required columns
        required_columns = ['song_name', 'artist', 'song_uri', 'embedding']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Parse embedding strings into numpy arrays
        def parse_embedding(embedding_str):
            try:
                return np.fromstring(embedding_str.strip('[]'), sep=', ')
            except Exception as e:
                raise ValueError(f"Invalid embedding format: {embedding_str[:50]}...")
        
        df['embedding_vector'] = df['embedding'].apply(parse_embedding)
        
        console.print(f"✓ Loaded {len(df)} reference songs with embeddings", style="green")
        return df
        
    except pd.errors.EmptyDataError:
        raise ValueError(f"Embeddings file '{embeddings_file}' is empty")
    except Exception as e:
        raise ValueError(f"Error parsing embeddings file: {e}")


def get_or_create_embedding(song_name: str, 
                          artist: str, 
                          song_uri: str,
                          provider: str = 'gemini',
                          use_cache: bool = True) -> Optional[np.ndarray]:
    """
    Get embedding for a song, either from cache or by creating new one.
    
    Args:
        song_name: Name of the song
        artist: Artist name
        song_uri: Spotify URI for the song
        provider: Embedding provider ('gemini', 'openai', 'clap')
        use_cache: Whether to use/update cache
        
    Returns:
        Embedding vector as numpy array, or None if failed
    """
    # Check cache first
    if use_cache:
        cached_embedding = _embedding_cache.get(song_name, artist, provider)
        if cached_embedding is not None:
            return cached_embedding
    
    try:
        # Download preview if not exists
        preview_path = search_and_download(song_name, artist)
        
        if not preview_path or not os.path.exists(preview_path):
            console.print(f"⚠️  Could not download preview for {song_name} by {artist}", style="yellow")
            return None
        
        # Generate embedding based on provider
        if provider == 'gemini':
            embedding = get_audio_embeddings(preview_path, "gemini")
        elif provider == 'openai':
            embedding = get_audio_embeddings(preview_path, "openai")
        elif provider == 'clap':
            from clap_embeddings import get_clap_embeddings
            embedding = get_clap_embeddings(preview_path)
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")
        
        # Cache the result
        if embedding is not None and use_cache:
            _embedding_cache.set(song_name, artist, embedding, provider)
        
        return embedding
        
    except Exception as e:
        console.print(f"❌ Error processing {song_name} by {artist}: {e}", style="red")
        return None


def batch_generate_embeddings(tracks: List[Dict], 
                             provider: str = 'gemini',
                             use_cache: bool = True,
                             max_workers: int = 4) -> List[Tuple[Dict, Optional[np.ndarray]]]:
    """
    Generate embeddings for multiple tracks in parallel.
    
    Args:
        tracks: List of track dictionaries with 'name', 'artist', 'uri'
        provider: Embedding provider to use
        use_cache: Whether to use embedding cache
        max_workers: Number of parallel workers
        
    Returns:
        List of tuples (track_dict, embedding_array)
    """
    from concurrent.futures import ThreadPoolExecutor
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Generating embeddings...", total=len(tracks))
        
        def process_track(track):
            embedding = get_or_create_embedding(
                track['name'], 
                track['artist'], 
                track['uri'],
                provider,
                use_cache
            )
            progress.update(task, advance=1)
            return (track, embedding)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_track, tracks))
    
    # Save cache after batch processing
    if use_cache:
        _embedding_cache.save()
    
    return results


def validate_embedding_format(embedding_str: str) -> bool:
    """
    Validate that an embedding string is in the correct format.
    
    Args:
        embedding_str: String representation of embedding
        
    Returns:
        True if valid format, False otherwise
    """
    try:
        # Should be able to parse as numpy array
        arr = np.fromstring(embedding_str.strip('[]'), sep=', ')
        # Should have reasonable dimensionality (not empty, not too large)
        return 0 < len(arr) < 10000
    except:
        return False


def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """
    Normalize embeddings to unit vectors for better similarity comparison.
    
    Args:
        embeddings: 2D array of embeddings (n_samples, n_features)
        
    Returns:
        Normalized embeddings
    """
    from sklearn.preprocessing import normalize
    return normalize(embeddings, norm='l2', axis=1)


def save_embeddings_to_csv(embeddings_data: List[Dict], 
                          output_file: str,
                          include_descriptions: bool = False):
    """
    Save embeddings and metadata to CSV file.
    
    Args:
        embeddings_data: List of dicts with song metadata and embeddings
        output_file: Output CSV filename
        include_descriptions: Whether to include text descriptions
    """
    try:
        rows = []
        for data in embeddings_data:
            row = {
                'song_name': data['song_name'],
                'artist': data['artist'],
                'song_uri': data['song_uri'],
                'embedding': str(data['embedding'].tolist())
            }
            
            if include_descriptions and 'description' in data:
                row['description'] = data['description']
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False)
        console.print(f"✓ Saved {len(rows)} embeddings to {output_file}", style="green")
        
    except Exception as e:
        console.print(f"❌ Error saving embeddings: {e}", style="red")
        raise