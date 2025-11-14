#!/usr/bin/env python3

import os
import requests
import base64
import webbrowser
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

class SpotifyPlaylistReader:
    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
        self.access_token = None
        self.auth_flow = None
        
        if not self.client_id or not self.client_secret:
            raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in environment variables")
    
    def get_access_token(self, use_user_auth=False):
        """Get access token using client credentials flow for public data or user auth for private data"""
        if use_user_auth:
            return self._get_user_access_token()
        else:
            return self._get_client_credentials_token()
    
    def _get_client_credentials_token(self):
        """Get access token using client credentials flow for public data"""
        auth_url = 'https://accounts.spotify.com/api/token'
        
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(auth_url, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        self.auth_flow = 'client_credentials'
        return self.access_token
    
    def _get_user_access_token(self):
        """Get access token using authorization code flow for user data"""
        # Generate authorization URL
        scope = 'playlist-read-private playlist-read-collaborative'
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
        self.auth_flow = 'authorization_code'
        return self.access_token
    
    def get_playlist_tracks(self, playlist_id, use_user_auth=False):
        """Get tracks from a Spotify playlist"""
        if not self.access_token:
            self.get_access_token(use_user_auth)
        
        url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        tracks = []
        
        while url:
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                for item in data['items']:
                    if item['track'] and item['track']['type'] == 'track':
                        track = item['track']
                        track_info = {
                            'name': track['name'],
                            'artists': [artist['name'] for artist in track['artists']],
                            'album': track['album']['name'],
                            'duration_ms': track['duration_ms'],
                            'popularity': track['popularity'],
                            'external_urls': track['external_urls']['spotify'],
                            'preview_url': track['preview_url']
                        }
                        tracks.append(track_info)
                
                url = data.get('next')
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    raise Exception("Access forbidden. This playlist may be private or require user authentication. Try using user authentication mode.")
                elif e.response.status_code == 404:
                    raise Exception("Playlist not found. Check that the playlist ID is correct and the playlist exists.")
                else:
                    raise e
        
        return tracks
    
    def get_playlist_info(self, playlist_id, use_user_auth=False):
        """Get basic information about a playlist"""
        if not self.access_token:
            self.get_access_token(use_user_auth)
        
        url = f'https://api.spotify.com/v1/playlists/{playlist_id}'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return {
                'name': data['name'],
                'description': data['description'],
                'owner': data['owner']['display_name'],
                'total_tracks': data['tracks']['total'],
                'public': data['public'],
                'external_urls': data['external_urls']['spotify'],
                'auth_flow_used': self.auth_flow
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                raise Exception("Access forbidden. This playlist may be private or require user authentication. Try using user authentication mode.")
            elif e.response.status_code == 404:
                raise Exception("Playlist not found. Check that the playlist ID is correct and the playlist exists.")
            else:
                raise e

def extract_playlist_id(spotify_url):
    """Extract playlist ID from Spotify URL"""
    if 'playlist/' in spotify_url:
        return spotify_url.split('playlist/')[-1].split('?')[0]
    return spotify_url

def get_playlist_tracks(playlist_url_or_id, use_user_auth=False):
    """
    Get tracks from a Spotify playlist.
    
    Args:
        playlist_url_or_id (str): Spotify playlist URL or playlist ID
        use_user_auth (bool): Whether to use user authentication for private playlists
        
    Returns:
        list: List of track dictionaries with keys: name, artists, external_url
    """
    reader = SpotifyPlaylistReader()
    playlist_id = extract_playlist_id(playlist_url_or_id)
    
    raw_tracks = reader.get_playlist_tracks(playlist_id, use_user_auth)
    
    simplified_tracks = []
    for track in raw_tracks:
        simplified_track = {
            'name': track['name'],
            'artists': track['artists'],
            'external_url': track['external_urls']
        }
        simplified_tracks.append(simplified_track)
    
    return simplified_tracks

def main():
    try:
        reader = SpotifyPlaylistReader()
        
        print("Spotify Playlist Reader")
        print("======================")
        print("Choose authentication mode:")
        print("1. Public access (client credentials) - works with public playlists only")
        print("2. User authentication (authorization code) - works with public and private playlists")
        
        auth_choice = input("\nEnter choice (1 or 2): ").strip()
        use_user_auth = auth_choice == '2'
        
        playlist_url = input("Enter Spotify playlist URL or ID: ").strip()
        playlist_id = extract_playlist_id(playlist_url)
        
        print("Getting playlist information...")
        try:
            playlist_info = reader.get_playlist_info(playlist_id, use_user_auth)
            
            print(f"\nPlaylist: {playlist_info['name']}")
            print(f"Owner: {playlist_info['owner']}")
            print(f"Description: {playlist_info['description']}")
            print(f"Total tracks: {playlist_info['total_tracks']}")
            print(f"Public: {playlist_info['public']}")
            print(f"Auth method used: {playlist_info['auth_flow_used']}")
            print(f"URL: {playlist_info['external_urls']}")
            
        except Exception as e:
            if "Access forbidden" in str(e) and not use_user_auth:
                print(f"\n{e}")
                retry_choice = input("Would you like to try with user authentication? (y/n): ").strip().lower()
                if retry_choice == 'y':
                    use_user_auth = True
                    playlist_info = reader.get_playlist_info(playlist_id, use_user_auth)
                    
                    print(f"\nPlaylist: {playlist_info['name']}")
                    print(f"Owner: {playlist_info['owner']}")
                    print(f"Description: {playlist_info['description']}")
                    print(f"Total tracks: {playlist_info['total_tracks']}")
                    print(f"Public: {playlist_info['public']}")
                    print(f"Auth method used: {playlist_info['auth_flow_used']}")
                    print(f"URL: {playlist_info['external_urls']}")
                else:
                    raise e
            else:
                raise e
        
        print("\nFetching tracks...")
        tracks = reader.get_playlist_tracks(playlist_id, use_user_auth)
        
        print(f"\nFound {len(tracks)} tracks:\n")
        
        for i, track in enumerate(tracks, 1):
            artists_str = ", ".join(track['artists'])
            duration_min = track['duration_ms'] // 60000
            duration_sec = (track['duration_ms'] % 60000) // 1000
            
            print(f"{i:3d}. {track['name']}")
            print(f"     Artists: {artists_str}")
            print(f"     Album: {track['album']}")
            print(f"     Duration: {duration_min}:{duration_sec:02d}")
            print(f"     Popularity: {track['popularity']}/100")
            if track['preview_url']:
                print(f"     Preview: ✓ Available - {track['preview_url']}")
            else:
                print(f"     Preview: ✗ Not available")
            print(f"     Spotify: {track['external_urls']}")
            print()
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set in .env file")
        print("2. For Spotify-made or private playlists, use user authentication mode")
        print("3. Check that the playlist URL/ID is correct")
        print("4. Some playlists may require the owner's permission to access")

if __name__ == "__main__":
    main()