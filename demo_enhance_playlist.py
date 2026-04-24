#!/usr/bin/env python3
"""
Demo script showing how to use the playlist enhancement system.

This script demonstrates the key functionality with example playlists
and showcases different enhancement strategies.
"""

import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import our enhancement functions
from enhance_playlist import enhance_playlist
from utils.embedding_manager import load_reference_embeddings
from utils.similarity_engine import SimilarityEngine
from utils.common import extract_spotify_id, validate_spotify_uri

console = Console()


def demo_basic_enhancement():
    """Demonstrate basic playlist enhancement"""
    console.print(Panel.fit("📀 Basic Playlist Enhancement Demo", style="bold blue"))
    
    # Example playlist URL (replace with actual playlist)
    example_playlist = "37i9dQZF1DXcBWIGoYBM5M"  # Today's Top Hits
    
    console.print(f"""
This demo shows how to enhance a playlist with similar songs.

Example command:
    python enhance_playlist.py "{example_playlist}" --count 10

What this does:
1. 📋 Reads the existing playlist tracks
2. 🎧 Downloads and analyzes audio previews
3. 🧠 Generates AI embeddings for musical similarity
4. 🔍 Finds similar songs from the reference library
5. 📝 Creates a new enhanced playlist

Try it with your own playlist!
    """)


def demo_advanced_features():
    """Demonstrate advanced enhancement features"""
    console.print(Panel.fit("🚀 Advanced Features Demo", style="bold green"))
    
    features_table = Table(title="Advanced Enhancement Options")
    features_table.add_column("Feature", style="cyan")
    features_table.add_column("Command", style="yellow")
    features_table.add_column("Description", style="white")
    
    features_table.add_row(
        "Diversity Control",
        "--diversity 0.3",
        "Add variety to recommendations (0.0-1.0)"
    )
    
    features_table.add_row(
        "Similarity Method",
        "--similarity-metric combined",
        "Use advanced similarity calculation"
    )
    
    features_table.add_row(
        "Custom Playlist Name",
        '--output-name "My Chill Mix"',
        "Set a custom name for the new playlist"
    )
    
    features_table.add_row(
        "Append Mode",
        "--mode append",
        "Add songs to existing playlist (coming soon)"
    )
    
    console.print(features_table)
    
    console.print(f"""
🎯 Example with all features:
    python enhance_playlist.py "your_playlist_url" \\
        --count 15 \\
        --diversity 0.2 \\
        --similarity-metric combined \\
        --output-name "Enhanced Vibes" \\
        --mode new

💡 Pro tips:
- Use diversity 0.1-0.3 for varied but coherent playlists
- Try 'combined' similarity for more nuanced matching
- Start with small counts (5-10) to test the system
    """)


def demo_similarity_comparison():
    """Show different similarity metrics"""
    console.print(Panel.fit("🔬 Similarity Metrics Comparison", style="bold magenta"))
    
    similarity_table = Table(title="Similarity Calculation Methods")
    similarity_table.add_column("Metric", style="cyan")
    similarity_table.add_column("Best For", style="green")
    similarity_table.add_column("Description", style="white")
    
    similarity_table.add_row(
        "cosine",
        "General use",
        "Measures angle between embedding vectors (default)"
    )
    
    similarity_table.add_row(
        "euclidean", 
        "Precise matching",
        "Measures direct distance between embeddings"
    )
    
    similarity_table.add_row(
        "combined",
        "Best results",
        "Weighted combination of cosine (70%) + euclidean (30%)"
    )
    
    console.print(similarity_table)


def demo_reference_library_info():
    """Show information about the reference library"""
    console.print(Panel.fit("📚 Reference Library Information", style="bold cyan"))
    
    try:
        # Load reference embeddings to show stats
        df = load_reference_embeddings()
        
        stats_table = Table(title="Reference Library Stats")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        
        stats_table.add_row("Total Songs", str(len(df)))
        stats_table.add_row("Unique Artists", str(df['artist'].nunique()))
        stats_table.add_row("Embedding Dimension", str(len(df.iloc[0]['embedding_vector'])))
        stats_table.add_row("Data Source", "Gemini AI Analysis")
        
        console.print(stats_table)
        
        console.print(f"""
📊 The reference library contains {len(df)} songs that have been analyzed
by Gemini AI for musical characteristics like:
- Rhythm and tempo
- Musical style and genre
- Instrumentation and mood  
- Vocal characteristics
- Production style

💡 To expand the library:
    python generate_embeddings.py your_playlist_url
    """)
        
    except Exception as e:
        console.print(f"⚠️  Could not load reference embeddings: {e}", style="yellow")
        console.print("\nMake sure gemini_embeddings.csv exists in the current directory.")


def demo_playlist_diversity_analysis():
    """Demonstrate playlist diversity analysis"""
    console.print(Panel.fit("📈 Playlist Diversity Analysis", style="bold yellow"))
    
    console.print("""
The system can analyze how diverse your playlist is:

🎯 Diversity Score: 0.0-1.0
- 0.0 = Very similar songs (mono-genre)  
- 1.0 = Very diverse songs (multi-genre)

💡 Use this to understand your playlist and adjust recommendations:
- Low diversity playlist → Use diversity factor 0.0-0.2
- High diversity playlist → Use diversity factor 0.3-0.5

The diversity analysis runs automatically during enhancement!
    """)


def main():
    """Run the demo"""
    console.print("""
🎵 Welcome to the Feather.fm Playlist Enhancement System Demo! 🎵

This system uses AI to analyze your playlists and recommend similar songs
based on musical characteristics, not just metadata.
    """, style="bold blue")
    
    # Show different demo sections
    demo_basic_enhancement()
    console.print()
    
    demo_advanced_features() 
    console.print()
    
    demo_similarity_comparison()
    console.print()
    
    demo_reference_library_info()
    console.print()
    
    demo_playlist_diversity_analysis()
    console.print()
    
    # Final recommendations
    console.print(Panel.fit("""
🚀 Ready to start? Try these commands:

1. Basic enhancement:
   python enhance_playlist.py "your_playlist_url" --count 5

2. With diversity:
   python enhance_playlist.py "your_playlist_url" --count 10 --diversity 0.2

3. Advanced features:
   python enhance_playlist.py "your_playlist_url" --count 15 \\
       --diversity 0.3 --similarity-metric combined \\
       --output-name "My Enhanced Playlist"

Need help? Run: python enhance_playlist.py --help
    """, title="🎯 Get Started", style="bold green"))


if __name__ == "__main__":
    main()