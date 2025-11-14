#!/usr/bin/env python3

import os
import requests
import base64
import webbrowser
import urllib.parse
import json
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv()

class SpotifyPlaylistCreator:
    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
        self.access_token = None
        self.user_id = None
        
        if not self.client_id or not self.client_secret:
            raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in environment variables")
    
    def get_user_access_token(self):
        """Get access token using authorization code flow with playlist creation permissions"""
        # Generate authorization URL with necessary scopes
        scope = 'playlist-modify-public playlist-modify-private'
        auth_params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': scope
        }
        
        auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(auth_params)}"
        
        print(f"\nOpening authorization URL in browser...")
        print(f"URL: {auth_url}")
        webbrowser.open(auth_url)
        
        # Get authorization code from user
        auth_code = input("\nPaste the authorization code from the redirect URL: ").strip()
        
        # Exchange authorization code for access token
        token_url = 'https://accounts.spotify.com/api/token'
        
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        return self.access_token
    
    def get_current_user(self):
        """Get current user information"""
        if not self.access_token:
            self.get_user_access_token()
        
        url = 'https://api.spotify.com/v1/me'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        user_data = response.json()
        self.user_id = user_data['id']
        return user_data
    
    def create_playlist(self, name: str, description: str = "", public: bool = True) -> dict:
        """Create a new playlist"""
        if not self.user_id:
            self.get_current_user()
        
        url = f'https://api.spotify.com/v1/users/{self.user_id}/playlists'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'name': name,
            'description': description,
            'public': public
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> dict:
        """Add tracks to a playlist using their URIs"""
        url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Spotify API allows max 100 tracks per request
        batch_size = 100
        results = []
        
        for i in range(0, len(track_uris), batch_size):
            batch = track_uris[i:i + batch_size]
            
            data = {
                'uris': batch
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            results.append(response.json())
        
        return results
    
    def create_playlist_with_tracks(self, name: str, track_uris: List[str], 
                                  description: str = "", public: bool = True) -> dict:
        """Create a playlist and add tracks to it in one operation"""
        # Create the playlist
        playlist = self.create_playlist(name, description, public)
        
        # Add tracks if provided
        if track_uris:
            self.add_tracks_to_playlist(playlist['id'], track_uris)
        
        return playlist
    
    def create_spotify_playlist(self, name: str, track_uris: List[str], 
                               description: str = "", public: bool = True) -> dict:
        """
        Create a Spotify playlist with the given tracks using this authenticated instance.
        
        Args:
            name: Name of the playlist
            track_uris: List of Spotify track URIs (format: spotify:track:XXXXXXXXXXXXXXXXXXXX)
            description: Optional description for the playlist
            public: Whether the playlist should be public (default: True)
        
        Returns:
            dict: Playlist information including ID and URL
        
        Raises:
            ValueError: If invalid track URIs are provided or authentication fails
            Exception: For other Spotify API errors
        """
        # Validate all URIs first
        invalid_uris = [uri for uri in track_uris if not validate_spotify_uri(uri)]
        if invalid_uris:
            raise ValueError(f"Invalid Spotify track URIs: {invalid_uris[:5]}{'...' if len(invalid_uris) > 5 else ''}")
        
        try:
            # Create playlist with tracks using this authenticated instance
            playlist = self.create_playlist_with_tracks(
                name=name,
                track_uris=track_uris,
                description=description,
                public=public
            )
            
            return {
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist['description'],
                'public': playlist['public'],
                'url': playlist['external_urls']['spotify'],
                'tracks_added': len(track_uris)
            }
            
        except Exception as e:
            raise Exception(f"Failed to create playlist: {str(e)}")
    
    def create_multiple_playlists(self, playlist_data: List[dict]) -> List[dict]:
        """
        Create multiple playlists in batch using a single authentication.
        
        Args:
            playlist_data: List of dictionaries with playlist info:
                [
                    {
                        'name': 'Playlist Name',
                        'track_uris': ['spotify:track:...', ...],
                        'description': 'Optional description',
                        'public': True/False
                    },
                    ...
                ]
        
        Returns:
            List[dict]: List of created playlist information
        """
        if not playlist_data:
            return []
        
        # Ensure authentication
        if not self.access_token:
            self.get_user_access_token()
        if not self.user_id:
            self.get_current_user()
        
        results = []
        for i, playlist_info in enumerate(playlist_data, 1):
            try:
                print(f"\nCreating playlist {i}/{len(playlist_data)}: {playlist_info['name']}")
                print(f"Songs in playlist: {len(playlist_info['track_uris'])}")
                
                result = self.create_spotify_playlist(
                    name=playlist_info['name'],
                    track_uris=playlist_info['track_uris'],
                    description=playlist_info.get('description', ''),
                    public=playlist_info.get('public', False)
                )
                
                results.append(result)
                print(f"✅ Created: {playlist_info['name']}")
                print(f"   URL: {result['url']}")
                print(f"   Tracks: {len(playlist_info['track_uris'])}")
                
            except Exception as e:
                print(f"❌ Failed to create playlist '{playlist_info['name']}': {e}")
                results.append({
                    'error': str(e),
                    'name': playlist_info['name'],
                    'failed': True
                })
        
        return results

def load_track_uris_from_file(file_path: str) -> List[str]:
    """Load track URIs from a text file (one URI per line)"""
    try:
        with open(file_path, 'r') as f:
            uris = [line.strip() for line in f if line.strip()]
        return uris
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")

def validate_spotify_uri(uri: str) -> bool:
    """Validate that a string is a proper Spotify track URI"""
    return uri.startswith('spotify:track:') and len(uri) == 36

def create_spotify_playlist(name: str, track_uris: List[str], 
                           description: str = "", public: bool = True) -> dict:
    """
    Create a Spotify playlist with the given tracks.
    
    Args:
        name: Name of the playlist
        track_uris: List of Spotify track URIs (format: spotify:track:XXXXXXXXXXXXXXXXXXXX)
        description: Optional description for the playlist
        public: Whether the playlist should be public (default: True)
    
    Returns:
        dict: Playlist information including ID and URL
    
    Raises:
        ValueError: If invalid track URIs are provided or authentication fails
        Exception: For other Spotify API errors
    """
    # Validate all URIs first
    invalid_uris = [uri for uri in track_uris if not validate_spotify_uri(uri)]
    if invalid_uris:
        raise ValueError(f"Invalid Spotify track URIs: {invalid_uris[:5]}{'...' if len(invalid_uris) > 5 else ''}")
    
    try:
        creator = SpotifyPlaylistCreator()
        
        # Create playlist with tracks
        playlist = creator.create_playlist_with_tracks(
            name=name,
            track_uris=track_uris,
            description=description,
            public=public
        )
        
        return {
            'id': playlist['id'],
            'name': playlist['name'],
            'description': playlist['description'],
            'public': playlist['public'],
            'url': playlist['external_urls']['spotify'],
            'tracks_added': len(track_uris)
        }
        
    except Exception as e:
        raise Exception(f"Failed to create playlist: {str(e)}")

def main():
    try:
        print("Spotify Playlist Creator")
        print("========================")
        
        # Get playlist details from user
        playlist_name = input("Enter playlist name: ").strip()
        if not playlist_name:
            print("Error: Playlist name is required")
            return
        
        playlist_description = input("Enter playlist description (optional): ").strip()
        
        public_choice = input("Make playlist public? (y/n, default: y): ").strip().lower()
        is_public = public_choice != 'n'
        
        print("\nTrack URI input options:")
        print("1. Enter URIs manually (one at a time)")
        print("2. Load URIs from a text file")
        
        input_choice = input("Choose option (1 or 2): ").strip()
        
        track_uris = []
        
        if input_choice == '1':
            print("\nEnter Spotify track URIs (format: spotify:track:XXXXXXXXXXXXXXXXXXXX)")
            print("Press Enter with empty line when done:")
            
            while True:
                uri = input("Track URI: ").strip()
                if not uri:
                    break
                
                if validate_spotify_uri(uri):
                    track_uris.append(uri)
                    print(f"✓ Added URI {len(track_uris)}")
                else:
                    print("✗ Invalid URI format. Should be: spotify:track:XXXXXXXXXXXXXXXXXXXX")
        
        elif input_choice == '2':
            file_path = input("Enter path to text file with URIs: ").strip()
            try:
                file_uris = load_track_uris_from_file(file_path)
                
                # Validate all URIs
                valid_uris = []
                invalid_count = 0
                
                for uri in file_uris:
                    if validate_spotify_uri(uri):
                        valid_uris.append(uri)
                    else:
                        invalid_count += 1
                
                track_uris = valid_uris
                
                print(f"✓ Loaded {len(track_uris)} valid URIs from file")
                if invalid_count > 0:
                    print(f"⚠ Skipped {invalid_count} invalid URIs")
                
            except FileNotFoundError as e:
                print(f"Error: {e}")
                return
        
        else:
            print("Invalid choice")
            return
        
        if not track_uris:
            print("No valid track URIs provided. Creating empty playlist...")
        
        print(f"\nCreating playlist '{playlist_name}' with {len(track_uris)} tracks...")
        
        # Use the new function
        playlist_info = create_spotify_playlist(
            name=playlist_name,
            track_uris=track_uris,
            description=playlist_description,
            public=is_public
        )
        
        print(f"\n✅ Playlist created successfully!")
        print(f"Name: {playlist_info['name']}")
        print(f"ID: {playlist_info['id']}")
        print(f"URL: {playlist_info['url']}")
        print(f"Public: {playlist_info['public']}")
        print(f"Tracks added: {playlist_info['tracks_added']}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set in .env file")
        print("2. Ensure you have granted the necessary permissions during authentication")
        print("3. Check that all track URIs are valid Spotify track URIs")
        print("4. Make sure you have a Spotify account and are logged in")

if __name__ == "__main__":
    main()