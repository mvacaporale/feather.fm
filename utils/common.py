"""
Common Utilities

Shared utility functions used across the feather.fm system.
"""

import os
import re
import sys
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Union
from urllib.parse import urlparse
from rich.console import Console

console = Console()


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a filename to be safe for filesystem use.
    
    Args:
        filename: Original filename
        max_length: Maximum length for the filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Replace multiple spaces/underscores with single underscore
    filename = re.sub(r'[_\s]+', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' ._')
    
    # Truncate if too long
    if len(filename) > max_length:
        # Keep file extension if present
        name_part, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name_part[:max_name_length] + ext
    
    # Ensure filename is not empty
    if not filename:
        filename = "untitled"
    
    return filename


def validate_spotify_uri(uri: str) -> bool:
    """
    Validate a Spotify URI format.
    
    Args:
        uri: Spotify URI to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Spotify URI patterns
    patterns = [
        r'^spotify:track:[a-zA-Z0-9]{22}$',  # Track URI
        r'^spotify:playlist:[a-zA-Z0-9]{22}$',  # Playlist URI
        r'^spotify:album:[a-zA-Z0-9]{22}$',  # Album URI
        r'^spotify:artist:[a-zA-Z0-9]{22}$',  # Artist URI
    ]
    
    return any(re.match(pattern, uri) for pattern in patterns)


def extract_spotify_id(url_or_id: str) -> Optional[str]:
    """
    Extract Spotify ID from URL or return ID if already provided.
    
    Args:
        url_or_id: Spotify URL or ID
        
    Returns:
        Spotify ID or None if invalid
    """
    # If it's already a valid Spotify ID (22 characters, alphanumeric)
    if re.match(r'^[a-zA-Z0-9]{22}$', url_or_id):
        return url_or_id
    
    # Try to extract from URL
    patterns = [
        r'spotify\.com/playlist/([a-zA-Z0-9]{22})',
        r'spotify\.com/track/([a-zA-Z0-9]{22})',
        r'spotify\.com/album/([a-zA-Z0-9]{22})',
        r'spotify\.com/artist/([a-zA-Z0-9]{22})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, create if it doesn't.
    
    Args:
        directory: Directory path
        
    Returns:
        Path object for the directory
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_file_write(filepath: Union[str, Path], content: str, encoding: str = 'utf-8') -> bool:
    """
    Safely write content to a file with error handling.
    
    Args:
        filepath: Path to write to
        content: Content to write
        encoding: File encoding
        
    Returns:
        True if successful, False otherwise
    """
    try:
        filepath = Path(filepath)
        
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first, then rename (atomic operation)
        temp_filepath = filepath.with_suffix(filepath.suffix + '.tmp')
        
        with open(temp_filepath, 'w', encoding=encoding) as f:
            f.write(content)
        
        # Atomic rename
        temp_filepath.rename(filepath)
        return True
        
    except Exception as e:
        console.print(f"❌ Error writing file {filepath}: {e}", style="red")
        # Clean up temporary file if it exists
        if 'temp_filepath' in locals() and temp_filepath.exists():
            temp_filepath.unlink()
        return False


def calculate_file_hash(filepath: Union[str, Path]) -> Optional[str]:
    """
    Calculate SHA-256 hash of a file.
    
    Args:
        filepath: Path to file
        
    Returns:
        Hex hash string or None if error
    """
    try:
        filepath = Path(filepath)
        if not filepath.exists():
            return None
        
        hash_sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
        
    except Exception as e:
        console.print(f"❌ Error calculating hash for {filepath}: {e}", style="red")
        return None


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"


def parse_boolean_string(value: Union[str, bool]) -> bool:
    """
    Parse various string representations of boolean values.
    
    Args:
        value: String or boolean value
        
    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        value = value.lower().strip()
        return value in ('true', '1', 'yes', 'on', 'y')
    
    return bool(value)


def validate_environment_variables(required_vars: List[str]) -> Dict[str, bool]:
    """
    Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        Dictionary mapping variable names to whether they're set
    """
    results = {}
    for var in required_vars:
        results[var] = var in os.environ and bool(os.environ[var].strip())
    
    return results


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable string.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_order = 0
    
    while size_bytes >= 1024 and size_order < len(size_names) - 1:
        size_order += 1
        size_bytes = size_bytes / 1024
    
    return f"{size_bytes:.1f} {size_names[size_order]}"


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dictionaries(*dicts: Dict) -> Dict:
    """
    Merge multiple dictionaries, with later dictionaries taking precedence.
    
    Args:
        dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


class ProgressTracker:
    """
    Simple progress tracker for long-running operations.
    """
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.console = Console()
    
    def update(self, increment: int = 1, message: str = None):
        """Update progress"""
        self.current += increment
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        
        status_msg = f"{self.description}: {self.current}/{self.total} ({percentage:.1f}%)"
        if message:
            status_msg += f" - {message}"
        
        self.console.print(f"\r{status_msg}", end="")
        
        if self.current >= self.total:
            self.console.print()  # New line when complete
    
    def finish(self, message: str = "Complete"):
        """Mark as finished"""
        self.current = self.total
        self.console.print(f"\r{self.description}: {message}          ")


def retry_with_backoff(func, max_retries: int = 3, backoff_factor: float = 1.5):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        backoff_factor: Backoff multiplier
        
    Returns:
        Function result or raises last exception
    """
    import time
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                sleep_time = backoff_factor ** attempt
                console.print(f"⚠️  Attempt {attempt + 1} failed, retrying in {sleep_time:.1f}s...", style="yellow")
                time.sleep(sleep_time)
            else:
                console.print(f"❌ All {max_retries + 1} attempts failed", style="red")
    
    raise last_exception