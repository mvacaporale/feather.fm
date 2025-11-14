#!/usr/bin/env python3

import os
import requests
import base64
import webbrowser
import urllib.parse
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

class SpotifyPlaylistDeleter:
    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
        self.access_token = None
        self.user_id = None
        
        if not self.client_id or not self.client_secret:
            raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in environment variables")
    
    def get_user_access_token(self):
        """Get access token using authorization code flow with playlist modification permissions"""
        scope = 'playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative'
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
        
        auth_code = input("\nPaste the authorization code from the redirect URL: ").strip()
        
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
    
    def get_user_playlists(self) -> List[Dict]:
        """Get all user's playlists"""
        if not self.user_id:
            self.get_current_user()
        
        url = 'https://api.spotify.com/v1/me/playlists'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        all_playlists = []
        
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            for playlist in data['items']:
                if playlist['owner']['id'] == self.user_id:
                    playlist_info = {
                        'id': playlist['id'],
                        'name': playlist['name'],
                        'description': playlist['description'],
                        'public': playlist['public'],
                        'tracks_count': playlist['tracks']['total'],
                        'url': playlist['external_urls']['spotify']
                    }
                    all_playlists.append(playlist_info)
            
            url = data.get('next')
        
        return all_playlists
    
    def unfollow_playlist(self, playlist_id: str) -> bool:
        """Delete/unfollow a playlist"""
        url = f'https://api.spotify.com/v1/playlists/{playlist_id}/followers'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        response = requests.delete(url, headers=headers)
        return response.status_code == 200
    
    def find_playlists_with_phrase(self, phrase: str, case_sensitive: bool = False) -> List[Dict]:
        """Find all user playlists that contain the specified phrase"""
        all_playlists = self.get_user_playlists()
        
        matching_playlists = []
        search_phrase = phrase if case_sensitive else phrase.lower()
        
        for playlist in all_playlists:
            playlist_name = playlist['name'] if case_sensitive else playlist['name'].lower()
            
            if search_phrase in playlist_name:
                matching_playlists.append(playlist)
        
        return matching_playlists
    
    def delete_playlists_with_phrase(self, phrase: str, case_sensitive: bool = False, 
                                   confirm_each: bool = True) -> Dict:
        """Delete all playlists containing the specified phrase"""
        matching_playlists = self.find_playlists_with_phrase(phrase, case_sensitive)
        
        if not matching_playlists:
            return {
                'found': 0,
                'deleted': 0,
                'skipped': 0,
                'errors': 0,
                'results': []
            }
        
        print(f"\nFound {len(matching_playlists)} playlist(s) containing '{phrase}':")
        for i, playlist in enumerate(matching_playlists, 1):
            print(f"{i}. {playlist['name']} ({playlist['tracks_count']} tracks)")
        
        if confirm_each:
            print(f"\nYou can confirm each deletion individually.")
        else:
            confirm = input(f"\nAre you sure you want to delete ALL {len(matching_playlists)} playlists? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("Operation cancelled.")
                return {
                    'found': len(matching_playlists),
                    'deleted': 0,
                    'skipped': len(matching_playlists),
                    'errors': 0,
                    'results': []
                }
        
        results = {
            'found': len(matching_playlists),
            'deleted': 0,
            'skipped': 0,
            'errors': 0,
            'results': []
        }
        
        for playlist in matching_playlists:
            if confirm_each:
                print(f"\nPlaylist: {playlist['name']}")
                print(f"Tracks: {playlist['tracks_count']}")
                print(f"URL: {playlist['url']}")
                confirm = input("Delete this playlist? (y/n/q to quit): ").strip().lower()
                
                if confirm == 'q':
                    print("Stopping deletion process.")
                    break
                elif confirm != 'y':
                    print("Skipped.")
                    results['skipped'] += 1
                    results['results'].append({
                        'name': playlist['name'],
                        'action': 'skipped',
                        'reason': 'user declined'
                    })
                    continue
            
            try:
                if self.unfollow_playlist(playlist['id']):
                    print(f"✅ Deleted: {playlist['name']}")
                    results['deleted'] += 1
                    results['results'].append({
                        'name': playlist['name'],
                        'action': 'deleted',
                        'id': playlist['id']
                    })
                else:
                    print(f"❌ Failed to delete: {playlist['name']}")
                    results['errors'] += 1
                    results['results'].append({
                        'name': playlist['name'],
                        'action': 'failed',
                        'reason': 'API error'
                    })
            except Exception as e:
                print(f"❌ Error deleting {playlist['name']}: {e}")
                results['errors'] += 1
                results['results'].append({
                    'name': playlist['name'],
                    'action': 'error',
                    'reason': str(e)
                })
        
        return results

def main():
    try:
        print("Spotify Playlist Deleter")
        print("========================")
        print("This tool will delete playlists that contain a specific phrase in their name.")
        print("⚠️  WARNING: This action cannot be undone!")
        
        deleter = SpotifyPlaylistDeleter()
        
        phrase = input("\nEnter the phrase to search for in playlist names: ").strip()
        if not phrase:
            print("Error: Phrase cannot be empty")
            return
        
        case_sensitive = input("Case sensitive search? (y/n, default: n): ").strip().lower() == 'y'
        
        print(f"\nSearching for playlists containing '{phrase}'...")
        
        matching_playlists = deleter.find_playlists_with_phrase(phrase, case_sensitive)
        
        if not matching_playlists:
            print(f"No playlists found containing '{phrase}'")
            return
        
        print(f"\n🎵 Found {len(matching_playlists)} matching playlist(s):")
        print("=" * 60)
        total_tracks = 0
        for i, playlist in enumerate(matching_playlists, 1):
            print(f"{i:2d}. {playlist['name']}")
            print(f"    📊 {playlist['tracks_count']} tracks | {'Public' if playlist['public'] else 'Private'}")
            print(f"    🔗 {playlist['url']}")
            if playlist['description']:
                print(f"    📝 {playlist['description'][:100]}{'...' if len(playlist['description']) > 100 else ''}")
            print()
            total_tracks += playlist['tracks_count']
        
        print("=" * 60)
        print(f"📈 Total: {len(matching_playlists)} playlists, {total_tracks} total tracks")
        print(f"⚠️  WARNING: Deleting these playlists cannot be undone!")
        
        # Confirmation step before showing deletion options
        proceed = input(f"\nDo you want to proceed with deleting these {len(matching_playlists)} playlists? (yes/no): ").strip().lower()
        if proceed != 'yes':
            print("Operation cancelled.")
            return
        
        print("\nDeletion options:")
        print("1. Confirm each deletion individually")
        print("2. Delete all matching playlists at once")
        print("3. Cancel")
        
        choice = input("Choose option (1-3): ").strip()
        
        if choice == '3':
            print("Operation cancelled.")
            return
        elif choice == '1':
            confirm_each = True
        elif choice == '2':
            confirm_each = False
            # Additional confirmation for bulk deletion
            final_confirm = input(f"\n⚠️  FINAL CONFIRMATION: Type 'DELETE ALL' to confirm bulk deletion of {len(matching_playlists)} playlists: ").strip()
            if final_confirm != 'DELETE ALL':
                print("Operation cancelled. Exact phrase 'DELETE ALL' required for bulk deletion.")
                return
        else:
            print("Invalid choice. Operation cancelled.")
            return
        
        results = deleter.delete_playlists_with_phrase(phrase, case_sensitive, confirm_each)
        
        print(f"\n📊 Results Summary:")
        print(f"Found: {results['found']}")
        print(f"Deleted: {results['deleted']}")
        print(f"Skipped: {results['skipped']}")
        print(f"Errors: {results['errors']}")
        
        if results['deleted'] > 0:
            print(f"\n✅ Successfully deleted {results['deleted']} playlist(s)")
        
        if results['errors'] > 0:
            print(f"\n❌ {results['errors']} error(s) occurred during deletion")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set in .env file")
        print("2. Ensure you have granted the necessary permissions during authentication")
        print("3. Make sure you have a Spotify account and are logged in")
        print("4. Check your internet connection")

if __name__ == "__main__":
    main()