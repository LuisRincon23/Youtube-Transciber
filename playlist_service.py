import yt_dlp
from typing import List, Dict
import os
from datetime import datetime

class PlaylistService:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }

    def get_playlist_videos(self, playlist_url: str) -> List[Dict]:
        """Get all videos from a playlist."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                if 'entries' in playlist_info:
                    return [
                        {
                            'url': f"https://www.youtube.com/watch?v={entry['id']}",
                            'title': entry.get('title', 'Untitled'),
                            'duration': entry.get('duration', 0)
                        }
                        for entry in playlist_info['entries']
                        if entry is not None
                    ]
                return []
        except Exception as e:
            raise Exception(f"Error fetching playlist: {str(e)}")

    def create_output_directory(self, playlist_title: str) -> str:
        """Create a directory for storing transcripts of a playlist."""
        # Clean the playlist title to make it filesystem-safe
        safe_title = "".join(c for c in playlist_title if c.isalnum() or c in (' ', '-', '_')).strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = f"transcripts_{safe_title}_{timestamp}"
        
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        return dir_name 