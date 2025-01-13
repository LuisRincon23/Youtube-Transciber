from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    # Handle different URL formats (full URL, shared URL, etc.)
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
    raise ValueError("Invalid YouTube URL")

def get_transcript(url: str) -> list:
    """Get transcript from YouTube video URL."""
    try:
        video_id = extract_video_id(url)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        raise Exception(f"Failed to get transcript: {str(e)}")

# Example usage:
# transcript = get_transcript("https://www.youtube.com/watch?v=VIDEO_ID")
# Each transcript entry has: {'text': '...', 'start': 123.45, 'duration': 6.78} 