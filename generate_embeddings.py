#!/usr/bin/env python3

import argparse
import csv
import os
import re
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from clap_embeddings import get_clap_embeddings
from audio_analysis import get_audio_embeddings
from playlist_reader import get_playlist_tracks
from enhanced_preview_downloader import search_and_download

def sanitize_filename(song_name, artist):
    """Create filename from song and artist name."""
    filename = f"{song_name} - {artist}"
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[^\w\s\-_.]', '', filename)
    filename = filename.strip()
    return filename[:100]  # Limit length

def find_existing_file(song_name, artist, previews_dir):
    """Find existing file for song/artist combo."""
    expected_filename = sanitize_filename(song_name, artist) + ".mp3"
    filepath = previews_dir / expected_filename
    return filepath if filepath.exists() else None

def parse_filename(filename):
    """Parse song name and artist from filename."""
    stem = Path(filename).stem
    
    if ' - ' in stem:
        parts = stem.split(' - ', 1)
        song_name = parts[0].strip()
        artist = parts[1].strip()
    else:
        song_name = stem
        artist = "Unknown"
    
    return song_name, artist

def generate_clap_csv(track_files, output_path, test_mode=False):
    """Generate CSV with CLAP embeddings."""
    if test_mode:
        track_files = track_files[:3]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['song_name', 'artist', 'song_uri', 'embedding']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for track_data in track_files:
            try:
                print(f"Processing {track_data['filepath']} with CLAP...")
                embedding = get_clap_embeddings(track_data['filepath'])
                
                writer.writerow({
                    'song_name': track_data['name'],
                    'artist': ', '.join(track_data['artists']),
                    'song_uri': track_data['external_url'],
                    'embedding': embedding.tolist()
                })
                
            except Exception as e:
                print(f"Error processing {track_data['filepath']}: {e}")

def process_single_embedding(track_data, embedding_provider):
    """Process a single track to generate embeddings."""
    try:
        description, embedding = get_audio_embeddings(track_data['filepath'], embedding_provider)
        
        return {
            'success': True,
            'data': {
                'song_name': track_data['name'],
                'artist': ', '.join(track_data['artists']),
                'song_uri': track_data['external_url'],
                'embedding': list(embedding)
            },
            'description': description,
            'track': track_data
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'track': track_data
        }

def generate_audio_embeddings_csv(track_files, output_path, embedding_provider='gemini', test_mode=False, max_workers=8):
    """Generate CSV with audio embeddings using specified provider with parallel processing."""
    if test_mode:
        track_files = track_files[:3]
    
    # Thread lock for writing to files
    write_lock = threading.Lock()
    
    # Create descriptions output file path
    descriptions_path = output_path.replace('.csv', '_descriptions.txt')
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile, \
         open(descriptions_path, 'w', encoding='utf-8') as descriptions_file:
        
        fieldnames = ['song_name', 'artist', 'song_uri', 'embedding']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write header for descriptions file
        descriptions_file.write(f"AUDIO DESCRIPTIONS - {embedding_provider.upper()} ANALYSIS\n")
        descriptions_file.write("=" * 80 + "\n\n")
        
        # Set up rich progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Processing embeddings..."),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn()
        ) as progress:
            
            task = progress.add_task(
                f"Generating {embedding_provider} embeddings", 
                total=len(track_files)
            )
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_track = {
                    executor.submit(process_single_embedding, track_data, embedding_provider): track_data
                    for track_data in track_files
                }
                
                # Process completed tasks
                for future in future_to_track:
                    result = future.result()
                    
                    if result['success']:
                        # Write to CSV and descriptions file with thread lock
                        with write_lock:
                            writer.writerow(result['data'])
                            
                            # Write description to text file
                            song_name = result['data']['song_name']
                            artist = result['data']['artist']
                            descriptions_file.write(f"SONG: {song_name}\n")
                            descriptions_file.write(f"ARTIST: {artist}\n")
                            descriptions_file.write("-" * 40 + "\n")
                            descriptions_file.write(result['description'])
                            descriptions_file.write("\n\n" + "=" * 80 + "\n\n")
                    else:
                        safe_filename = str(result['track']['filepath']).encode('ascii', errors='replace').decode('ascii')
                        progress.console.print(f"[red]Error processing {safe_filename}: {result['error']}")
                    
                    # Update progress
                    progress.advance(task)
    
    print(f"\nDescriptions saved to: {descriptions_path}")


def main():
    parser = argparse.ArgumentParser(description='Generate audio embeddings CSV files')
    parser.add_argument('-t', '--test', action='store_true', 
                        help='Test mode - only process 3 songs')
    parser.add_argument('-p', '--playlist', default='3kHKc76hZqTDJVKk2ENK4V',
                        help='Spotify playlist ID (default: 3kHKc76hZqTDJVKk2ENK4V)')
    parser.add_argument('-m', '--method', choices=['clap', 'audio', 'both'], default='audio',
                        help='Which embedding method to use (default: audio/gemini)')
    parser.add_argument('-e', '--embedding-provider', choices=['gemini', 'openai'], default='gemini',
                        help='Which provider to use for audio embeddings (default: gemini)')
    
    args = parser.parse_args()
    
    print(f"Fetching tracks from playlist {args.playlist}...")
    tracks = get_playlist_tracks(args.playlist)
    print(f"Found {len(tracks)} tracks in playlist")
    
    previews_dir = Path("previews")
    previews_dir.mkdir(exist_ok=True)
    
    track_files = []
    downloaded = 0
    skipped = 0
    failed = 0
    
    for i, track in enumerate(tracks, 1):
        song_name = track['name']
        artist_names = track['artists']
        artist_str = ', '.join(artist_names)
        
        print(f"\n{i}/{len(tracks)} - {song_name} by {artist_str}")
        
        # Check if file already exists
        existing_file = find_existing_file(song_name, artist_str, previews_dir)
        
        if existing_file:
            print(f"✓ File already exists: {existing_file.name}")
            track_files.append({
                'name': song_name,
                'artists': artist_names,
                'external_url': track['external_url'],
                'filepath': str(existing_file)
            })
            skipped += 1
        else:
            print(f"Downloading {song_name} by {artist_str}...")
            if search_and_download(song_name, artist_str, str(previews_dir)):
                # Find the downloaded file
                downloaded_file = find_existing_file(song_name, artist_str, previews_dir)
                if downloaded_file:
                    track_files.append({
                        'name': song_name,
                        'artists': artist_names,
                        'external_url': track['external_url'],
                        'filepath': str(downloaded_file)
                    })
                    downloaded += 1
                else:
                    print(f"✗ Downloaded file not found for {song_name}")
                    failed += 1
            else:
                print(f"✗ Failed to download {song_name}")
                failed += 1
    
    print(f"\nDownload summary: {downloaded} downloaded, {skipped} skipped, {failed} failed")
    print(f"Total files for processing: {len(track_files)}")
    
    if not track_files:
        print("No audio files available for processing")
        return
    
    if args.test:
        print("Running in test mode - processing only 3 files")
    
    if args.method in ['clap', 'both']:
        generate_clap_csv(track_files, "clap_embeddings.csv", args.test)
        print("CLAP embeddings CSV saved to clap_embeddings.csv")
    
    if args.method in ['audio', 'both']:
        output_filename = f"{args.embedding_provider}_embeddings.csv"
        generate_audio_embeddings_csv(track_files, output_filename, args.embedding_provider, args.test)
        print(f"{args.embedding_provider.title()} embeddings CSV saved to {output_filename}")

if __name__ == "__main__":
    main()