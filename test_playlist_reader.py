#!/usr/bin/env python3

from playlist_reader import get_playlist_tracks
import json

def test_playlist_function():
    """Test the get_playlist_tracks function with a public playlist"""
    
    # Using a popular public Spotify playlist (Today's Top Hits)
    test_playlist_url = "https://open.spotify.com/playlist/3kHKc76hZqTDJVKk2ENK4V"
    
    print("Testing get_playlist_tracks function")
    print("===================================")
    print(f"Playlist URL: {test_playlist_url}")
    print("\nFetching tracks...")
    
    try:
        # Get tracks using the new function
        tracks = get_playlist_tracks(test_playlist_url)
        
        print(f"\nSuccessfully fetched {len(tracks)} tracks!")
        print("\nFirst 5 tracks:")
        print("-" * 50)
        
        # Display first 5 tracks with simplified structure
        for i, track in enumerate(tracks[:5], 1):
            print(f"{i}. {track['name']}")
            print(f"   Artists: {', '.join(track['artists'])}")
            print(f"   Spotify URL: {track['external_url']}")
            print()
        
        # Show the data structure
        print("Sample track data structure:")
        print(json.dumps(tracks[0], indent=2))
        
        # Test with just playlist ID
        print("\n" + "="*50)
        print("Testing with playlist ID only...")
        playlist_id = "3kHKc76hZqTDJVKk2ENK4V"
        tracks_by_id = get_playlist_tracks(playlist_id)
        print(f"Fetched {len(tracks_by_id)} tracks using playlist ID")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nThis might be due to:")
        print("1. Missing Spotify API credentials in .env file")
        print("2. Network connectivity issues")
        print("3. Playlist privacy settings")

if __name__ == "__main__":
    test_playlist_function()