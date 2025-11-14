#!/usr/bin/env python3

import os
import requests
import re
import json
import subprocess
from urllib.parse import urlparse

def sanitize_filename(filename):
    """Remove or replace characters that are invalid in filenames"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[^\w\s\-_.]', '', filename)
    filename = filename.strip()
    return filename[:100]  # Limit length

def find_preview_with_nodejs(song_name, artist_name):
    """Use Node.js spotify-preview-finder to search for preview URLs"""
    try:
        # Run the Node.js script
        result = subprocess.run(
            ['node', 'preview_finder.js', song_name, artist_name],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode != 0:
            print(f"Node.js script error: {result.stderr}")
            return None
        
        # Parse the output to extract the JSON result
        output = result.stdout
        
        # Find JSON between markers
        start_marker = 'JSON_RESULT_START'
        end_marker = 'JSON_RESULT_END'
        
        start_idx = output.find(start_marker)
        end_idx = output.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            print("Could not find JSON markers in output")
            return None
        
        json_str = output[start_idx + len(start_marker):end_idx].strip()
        
        if json_str == 'null':
            return None
        
        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return None
        
    except Exception as e:
        print(f"Error running Node.js preview finder: {e}")
        return None

def download_preview(preview_url, filename):
    """Download a preview file from URL"""
    try:
        response = requests.get(preview_url, stream=True)
        response.raise_for_status()
        
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        return True
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return False

def search_and_download(song_name, artist_name, output_dir="previews"):
    """Search for a song and download its preview"""
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Searching for: \"{song_name}\" by \"{artist_name}\"")
    
    # Use Node.js package to find preview
    search_result = find_preview_with_nodejs(song_name, artist_name)
    
    if not search_result or not search_result.get('success'):
        print("✗ No results found")
        return False
    
    results = search_result.get('results', [])
    if not results:
        print("✗ No tracks found in results")
        return False
    
    # Use the first (most relevant) result
    track = results[0]
    print(f"Found: {track['name']}")
    print(f"Album: {track['albumName']}")
    print(f"Release Date: {track['releaseDate']}")
    print(f"Popularity: {track['popularity']}/100")
    
    preview_urls = track.get('previewUrls', [])
    if not preview_urls:
        print("✗ No preview URLs available")
        return False
    
    # Use the first preview URL
    preview_url = preview_urls[0]
    print(f"Preview URL: {preview_url}")
    
    # Create safe filename
    safe_filename = sanitize_filename(f"{song_name} - {artist_name}")
    filepath = os.path.join(output_dir, f"{safe_filename}.mp3")
    
    if os.path.exists(filepath):
        print(f"File already exists: {filepath}")
        return True
    
    print(f"Downloading to: {filepath}")
    success = download_preview(preview_url, filepath)
    
    if success:
        print("✓ Download successful")
        return True
    else:
        print("✗ Download failed")
        return False

def batch_search_and_download(songs_list, output_dir="previews"):
    """Download previews for a list of songs"""
    os.makedirs(output_dir, exist_ok=True)
    
    successful = 0
    failed = 0
    
    for i, (song_name, artist_name) in enumerate(songs_list, 1):
        print(f"\n{i}/{len(songs_list)} - Processing: \"{song_name}\" by \"{artist_name}\"")
        print("-" * 60)
        
        if search_and_download(song_name, artist_name, output_dir):
            successful += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total songs: {len(songs_list)}")
    print(f"Successfully downloaded: {successful}")
    print(f"Failed: {failed}")

def main():
    print("Enhanced Spotify Preview Downloader")
    print("Uses spotify-preview-finder for advanced search")
    print("=" * 50)
    print("1. Search and download single song")
    print("2. Batch download from list")
    
    choice = input("\nChoose an option (1 or 2): ").strip()
    
    if choice == "1":
        song_name = input("Enter song name: ").strip()
        artist_name = input("Enter artist name: ").strip()
        output_dir = input("Output directory (default: 'previews'): ").strip() or "previews"
        
        search_and_download(song_name, artist_name, output_dir)
    
    elif choice == "2":
        print("\nEnter songs one by one. Press Enter with empty song name to finish.")
        songs_list = []
        
        while True:
            song_name = input(f"Song {len(songs_list) + 1} name (or Enter to finish): ").strip()
            if not song_name:
                break
            artist_name = input(f"Artist name: ").strip()
            if artist_name:
                songs_list.append((song_name, artist_name))
        
        if songs_list:
            output_dir = input("Output directory (default: 'previews'): ").strip() or "previews"
            batch_search_and_download(songs_list, output_dir)
        else:
            print("No songs entered.")
    
    else:
        print("Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main()