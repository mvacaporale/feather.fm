# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

feather.fm is a music clustering and Spotify playlist creation tool that:
- Fetches songs from public Spotify playlists
- Downloads audio previews 
- Generates multiple types of embeddings (CLAP, Gemini, OpenAI) from audio analysis
- Performs clustering analysis to group similar songs
- Automatically creates Spotify playlists based on clusters

## Dependencies and Package Management

This is a Python project using `uv` as the package manager with `pyproject.toml`.

### Key Dependencies
- `google-genai` for Gemini API interactions (text and audio analysis)
- `transformers` and `torch` for CLAP embeddings
- `librosa` for audio processing
- `scikit-learn` and `hdbscan` for clustering algorithms
- `requests` for Spotify API
- `rich` for CLI progress bars

There's also a minimal Node.js component that uses `spotify-preview-finder` for downloading previews.

## Environment Variables

All required API keys are stored in `~/.zshrc`:
- `SPOTIFY_CLIENT_ID` - Required for Spotify API
- `SPOTIFY_CLIENT_SECRET` - Required for Spotify API 
- `SPOTIFY_ACCESS_TOKEN` - Generated after first authentication
- `SPOTIFY_REFRESH_TOKEN` - Auto-refresh token
- `SPOTIFY_TOKEN_EXPIRES_AT` - Token expiry timestamp
- `GEMINI_API_KEY` - For Gemini embeddings

## Core Workflow Components

### 1. Playlist Reading (`playlist_reader.py`)
- Fetches tracks from Spotify playlists using client credentials or user auth
- Supports both public and private playlists
- Returns simplified track data (name, artists, external_url)

### 2. Preview Download 
- `enhanced_preview_downloader.py` - Node.js-based preview downloader
- `download_playlist_previews.py` - Python wrapper for batch downloading
- Files saved to `previews/` directory with format: `{song_name} - {artist}.mp3`

### 3. Embedding Generation (`generate_embeddings.py`)
- **CLAP Embeddings**: Audio-based embeddings using transformer models
- **Gemini Embeddings**: Audio analysis via Google's Gemini API (primary method)
- **OpenAI Embeddings**: Alternative audio analysis provider
- Supports parallel processing with configurable thread pools
- Outputs CSV files: `{provider}_embeddings.csv` and `{provider}_embeddings_descriptions.txt`

### 4. Clustering Analysis (`group_playlist.py`)
- **Algorithms**: K-means (default) and HDBSCAN clustering
- **Preprocessing**: StandardScaler normalization (optional)
- **Optimization**: Automatic optimal k-finding using silhouette scores
- **Concatenated Embeddings**: Can combine multiple embedding types for clustering
- **Playlist Creation**: Direct Spotify playlist creation from clusters

### 5. Spotify Integration (`create_playlist.py`)
- Persistent authentication with token refresh
- Batch playlist creation with single auth session
- Private playlist creation by default

## Common Commands

```bash
# Install dependencies
uv sync

# Test Spotify connection
uv run python test_token_persistence.py

# Generate embeddings (default: Gemini)
uv run python generate_embeddings.py --playlist PLAYLIST_ID

# Generate embeddings with test mode (3 songs only)
uv run python generate_embeddings.py --test --playlist PLAYLIST_ID

# Perform clustering and create playlists
uv run python group_playlist.py gemini_embeddings.csv --create-playlists

# Create playlists from existing clustering results
uv run python group_playlist.py --playlist-only clustered_songs.csv

# Use HDBSCAN clustering with custom parameters
uv run python group_playlist.py gemini_embeddings.csv --algorithm hdbscan --min-cluster-size 5

# Combine multiple embedding types for clustering
uv run python group_playlist.py gemini_embeddings.csv clap_embeddings.csv --create-playlists
```

## Architecture Notes

### Embedding Pipeline
1. **Playlist → Tracks**: `playlist_reader.py` fetches track metadata
2. **Tracks → Audio**: Preview downloaders get MP3 files
3. **Audio → Embeddings**: Multiple embedding providers analyze audio
4. **Embeddings → Clusters**: Clustering algorithms group similar songs
5. **Clusters → Playlists**: Spotify playlists created from clusters

### File Naming Convention
- Audio files: `{song_name} - {artist}.mp3`
- Embedding CSVs: `{provider}_embeddings.csv`
- Clustering output: `clustered_songs.csv`
- Analysis descriptions: `{provider}_embeddings_descriptions.txt`

### Spotify Authentication Flow
1. First run: OAuth browser flow, tokens printed for shell configuration
2. Subsequent runs: Automatic token refresh using saved environment variables
3. Manual fallback: Re-authentication if refresh fails

### Clustering Flexibility
- Supports both unsupervised (K-means) and density-based (HDBSCAN) clustering
- Can process single or multiple concatenated embedding types
- Automatic parameter optimization with visualization output
- Handles noise points in HDBSCAN (cluster label = -1)