#!/usr/bin/env python3

"""
Test script to verify Spotify environment variable authentication.
"""

from create_playlist import SpotifyPlaylistCreator
import os

def test_env_authentication():
    """Test that environment variable authentication works"""
    print("Testing Spotify Environment Variable Authentication")
    print("=" * 50)
    
    # Check required environment variables
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    access_token = os.getenv('SPOTIFY_ACCESS_TOKEN')
    refresh_token = os.getenv('SPOTIFY_REFRESH_TOKEN')
    
    print("Environment Variables Status:")
    print(f"  SPOTIFY_CLIENT_ID: {'✅ Set' if client_id else '❌ Missing'}")
    print(f"  SPOTIFY_CLIENT_SECRET: {'✅ Set' if client_secret else '❌ Missing'}")
    print(f"  SPOTIFY_ACCESS_TOKEN: {'✅ Set' if access_token else '❌ Missing'}")
    print(f"  SPOTIFY_REFRESH_TOKEN: {'✅ Set' if refresh_token else '❌ Missing'}")
    
    if not client_id or not client_secret:
        print("\n❌ Missing required credentials!")
        print("Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
        return
    
    # Create instance and test authentication
    try:
        creator = SpotifyPlaylistCreator()
        
        if access_token:
            print("\n🔄 Testing existing tokens...")
            try:
                user_info = creator.get_current_user()
                print(f"✅ Successfully authenticated as: {user_info['display_name']} (ID: {user_info['id']})")
                print("🎉 Environment variable authentication is working!")
                return
            except Exception as e:
                print(f"❌ Existing tokens failed: {e}")
                print("Will attempt fresh authentication...")
        
        print("\n🔄 Running fresh authentication...")
        creator.get_user_access_token()
        user_info = creator.get_current_user()
        print(f"\n✅ Successfully authenticated as: {user_info['display_name']} (ID: {user_info['id']})")
        print("\n🎉 Authentication successful! Copy the export commands above to your shell profile.")
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
        print("2. Make sure your Spotify app has the correct redirect URI")
        print("3. Check that you've granted the necessary permissions")

if __name__ == "__main__":
    test_env_authentication()