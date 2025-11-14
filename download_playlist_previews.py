#!/usr/bin/env python3

from playlist_reader import get_playlist_tracks
from enhanced_preview_downloader import search_and_download

def main():
    playlist_id = "3kHKc76hZqTDJVKk2ENK4V"
    output_dir = "previews"
    
    print(f"Fetching tracks from playlist {playlist_id}...")
    tracks = get_playlist_tracks(playlist_id)
    
    print(f"Found {len(tracks)} tracks. Starting downloads...")
    
    successful = 0
    failed = 0
    
    for i, track in enumerate(tracks, 1):
        song_name = track['name']
        artist_name = ', '.join(track['artists'])
        
        print(f"\n{i}/{len(tracks)} - Processing: \"{song_name}\" by \"{artist_name}\"")
        print("-" * 60)
        
        if search_and_download(song_name, artist_name, output_dir):
            successful += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total songs: {len(tracks)}")
    print(f"Successfully downloaded: {successful}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    main()