# 🎵 Playlist Enhancement System

An AI-powered system for enhancing Spotify playlists with similar songs based on audio characteristics, not just metadata.

## 🚀 Features

- **AI Audio Analysis**: Uses Gemini AI to analyze musical characteristics
- **Smart Recommendations**: Finds similar songs based on audio embeddings
- **Diversity Control**: Balance between similarity and variety in recommendations
- **Multiple Similarity Metrics**: Cosine, Euclidean, and combined approaches
- **Batch Processing**: Efficient parallel processing of multiple tracks
- **Caching System**: Avoids recomputing embeddings for better performance
- **Rich CLI Interface**: Beautiful command-line interface with progress tracking

## 📁 Project Structure

```
feather.fm/
├── enhance_playlist.py          # Main enhancement script
├── utils/
│   ├── embedding_manager.py     # Embedding generation and caching
│   ├── similarity_engine.py     # Similarity calculation algorithms  
│   └── common.py               # Shared utility functions
├── test_enhance_playlist.py     # Comprehensive test suite
├── demo_enhance_playlist.py     # Demo and examples
└── gemini_embeddings.csv       # Reference song library
```

## 🛠️ Installation

1. **Install dependencies**:
   ```bash
   uv sync  # or pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   # In ~/.zshrc or ~/.bashrc
   export GEMINI_API_KEY="your_gemini_api_key"
   export SPOTIPY_CLIENT_ID="your_spotify_client_id"
   export SPOTIPY_CLIENT_SECRET="your_spotify_client_secret"
   ```

3. **Prepare reference embeddings**:
   ```bash
   # Make sure gemini_embeddings.csv exists
   # Or generate new embeddings:
   python generate_embeddings.py your_source_playlist_url
   ```

## 🎯 Quick Start

### Basic Enhancement
```bash
python enhance_playlist.py "https://open.spotify.com/playlist/YOUR_PLAYLIST_ID" --count 10
```

### Advanced Options
```bash
python enhance_playlist.py "your_playlist_url" \\
    --count 15 \\
    --diversity 0.3 \\
    --similarity-metric combined \\
    --output-name "My Enhanced Mix"
```

## 📚 Command Reference

### Required Arguments
- `playlist_url`: Spotify playlist URL or playlist ID
- `--count, -n`: Number of songs to add (required)

### Optional Arguments
- `--mode {new,append}`: Create new playlist or append to existing (default: new)
- `--output-name`: Custom name for output playlist
- `--diversity FLOAT`: Diversity factor 0.0-1.0 (default: 0.0)
- `--similarity-metric {cosine,euclidean,combined}`: Similarity calculation method

### Examples

1. **Basic Enhancement**:
   ```bash
   python enhance_playlist.py "37i9dQZF1DXcBWIGoYBM5M" --count 5
   ```

2. **Diverse Recommendations**:
   ```bash
   python enhance_playlist.py "playlist_id" --count 10 --diversity 0.2
   ```

3. **Advanced Similarity**:
   ```bash
   python enhance_playlist.py "playlist_url" --count 15 \\
       --similarity-metric combined --output-name "Enhanced Vibes"
   ```

## 🧠 How It Works

### 1. Audio Analysis
- Downloads 30-second preview tracks from Spotify
- Uses Gemini AI to analyze musical characteristics:
  - Rhythm, tempo, and time signature
  - Musical style and genre elements
  - Instrumentation and arrangement
  - Vocal characteristics and mood
  - Production quality and effects

### 2. Embedding Generation
- Converts audio analysis into high-dimensional vectors (768 dimensions)
- Captures nuanced musical relationships
- Caches embeddings for performance

### 3. Similarity Calculation
- **Cosine Similarity**: Measures angle between vectors (good for general similarity)
- **Euclidean Distance**: Measures direct distance (precise matching)
- **Combined Method**: Weighted combination (70% cosine + 30% euclidean)

### 4. Smart Selection
- Filters out songs already in the playlist
- Applies diversity factor to avoid too-similar recommendations
- Ranks by similarity score
- Returns top N recommendations

## 📊 Understanding Diversity

The diversity factor (0.0-1.0) controls recommendation variety:

- **0.0**: Maximum similarity (coherent, mono-genre playlists)
- **0.1-0.3**: Slight variety while maintaining playlist coherence
- **0.4-0.6**: Balanced mix of similar and diverse songs
- **0.7-1.0**: High diversity (multi-genre, experimental playlists)

### When to Use Different Diversity Levels

| Playlist Type | Diversity | Example |
|---------------|-----------|---------|
| Workout/Focus | 0.0-0.1 | Consistent energy/mood |
| Daily Listen | 0.2-0.3 | Coherent but not monotonous |
| Discovery | 0.4-0.5 | Explore new styles |
| Party Mix | 0.3-0.4 | Variety within danceable songs |

## 🔧 Advanced Usage

### Using the Utils Modules

```python
from utils.embedding_manager import load_reference_embeddings, get_or_create_embedding
from utils.similarity_engine import calculate_similarity_scores, SimilarityEngine
from utils.common import extract_spotify_id, sanitize_filename

# Load reference library
ref_df = load_reference_embeddings("gemini_embeddings.csv")

# Generate embedding for a single song
embedding = get_or_create_embedding("Song Name", "Artist", "spotify:track:...")

# Calculate similarities with custom settings
engine = SimilarityEngine(similarity_metric='combined')
similarities = engine.calculate_playlist_similarities(
    playlist_embeddings, 
    reference_embeddings,
    aggregation='weighted'  # 'mean', 'max', or 'weighted'
)
```

### Batch Processing

```python
from utils.embedding_manager import batch_generate_embeddings

# Process multiple tracks efficiently
tracks = [
    {'name': 'Song 1', 'artist': 'Artist 1', 'uri': 'spotify:track:...'},
    {'name': 'Song 2', 'artist': 'Artist 2', 'uri': 'spotify:track:...'},
]

results = batch_generate_embeddings(
    tracks, 
    provider='gemini',
    use_cache=True,
    max_workers=4
)
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_enhance_playlist.py
```

Tests cover:
- Embedding loading and parsing
- Similarity calculations  
- Song selection algorithms
- Error handling
- Edge cases

## 🎮 Demo

Try the interactive demo:

```bash
python demo_enhance_playlist.py
```

The demo showcases:
- Basic enhancement workflow
- Advanced features and options
- Similarity metric comparisons
- Reference library statistics
- Best practices and tips

## 🔍 Troubleshooting

### Common Issues

1. **Missing embeddings file**:
   ```
   Error: Reference embeddings file 'gemini_embeddings.csv' not found
   ```
   **Solution**: Ensure gemini_embeddings.csv exists, or generate new embeddings

2. **No preview downloads**:
   ```
   Warning: Could not download preview for [song]
   ```
   **Solution**: Some songs don't have previews available, this is normal

3. **API errors**:
   ```
   Error: Spotify API error
   ```
   **Solution**: Check your API credentials and internet connection

4. **No recommendations found**:
   ```
   Error: No suitable recommendations found
   ```
   **Solution**: Try lowering diversity factor or expanding reference library

### Performance Tips

- Use embedding cache to avoid recomputing
- Start with smaller counts (5-10) for testing
- Use parallel processing for large playlists
- Keep reference library updated with diverse songs

## 🤝 Contributing

### Adding New Features

1. **New similarity metrics**: Add to `utils/similarity_engine.py`
2. **New embedding providers**: Extend `utils/embedding_manager.py`
3. **CLI improvements**: Update `enhance_playlist.py`

### Running Tests

```bash
# Run all tests
python test_enhance_playlist.py

# Run specific test
python -m unittest test_enhance_playlist.TestPlaylistEnhancement.test_similarity_scores
```

### Code Style

- Use type hints
- Add docstrings to all functions
- Follow existing error handling patterns
- Include console output for user feedback

## 📜 License

This project is part of the feather.fm audio analysis system.

## 🙏 Acknowledgments

- **Gemini AI** for audio analysis capabilities
- **Spotify API** for playlist and preview access
- **Rich** library for beautiful CLI interface
- **scikit-learn** for similarity calculations