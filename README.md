# feather.fm

Music clustering and Spotify playlist creation tool.

## Features

- Cluster songs based on audio features using embeddings
- Automatically create Spotify playlists from clusters
- Persistent Spotify authentication (no need to re-authenticate every time)

## Spotify Authentication Setup

The Spotify integration uses environment variables for secure token storage, eliminating the need to re-authenticate every time.

### Required Environment Variables

Add these to your `~/.zshrc`, `~/.bashrc`, or `.env` file:

```bash
# Required for all operations
export SPOTIFY_CLIENT_ID="your_client_id_here"
export SPOTIFY_CLIENT_SECRET="your_client_secret_here"

# Optional: Generated after first authentication
export SPOTIFY_ACCESS_TOKEN="your_access_token_here"
export SPOTIFY_REFRESH_TOKEN="your_refresh_token_here"  
export SPOTIFY_TOKEN_EXPIRES_AT="timestamp_here"
```

### Setup Process

1. **Get Spotify App Credentials**:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new app
   - Add `http://localhost:8888/callback` as a redirect URI
   - Copy your Client ID and Client Secret

2. **Set Required Variables**:
   ```bash
   export SPOTIFY_CLIENT_ID="your_client_id"
   export SPOTIFY_CLIENT_SECRET="your_client_secret"
   ```

3. **First Run Authentication**:
   ```bash
   python group_playlist.py --create-playlists clustered_songs.csv
   ```
   
4. **Save Generated Tokens**: 
   After authentication, the script will print export commands for the token variables. Copy these to your shell profile.

5. **Subsequent Runs**:
   The script will automatically use the saved tokens without requiring re-authentication.

### How It Works

1. **First Run**: OAuth flow through browser, tokens printed for you to save
2. **Token Refresh**: Automatically refreshes expired tokens when needed
3. **Manual Refresh**: If refresh fails, will prompt for re-authentication

### Security Notes

- Store tokens as environment variables (not in files)
- Never commit tokens to version control
- Tokens are only sent to Spotify's servers
- Access tokens expire after 1 hour but are auto-refreshed

### Troubleshooting

If authentication fails:

1. **Check Environment Variables**: Make sure all required variables are set
2. **Reload Shell**: Run `source ~/.zshrc` after adding variables
3. **Clear Tokens**: Remove token variables to force fresh authentication
4. **Verify Scopes**: Ensure your app has `playlist-modify-public playlist-modify-private` permissions