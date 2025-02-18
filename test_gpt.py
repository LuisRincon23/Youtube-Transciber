from transcript_service import get_transcript
from gpt_service import GPTService, GPTServiceError
from urllib.error import URLError
import time

def generate_video_notes(url: str, custom_prompt: str = None) -> str:
    """
    Generate notes from a YouTube video transcript.
    
    Args:
        url: YouTube video URL
        custom_prompt: Optional custom prompt for note generation
    
    Returns:
        str: Generated notes in markdown format
    
    Raises:
        ValueError: If URL is invalid
        GPTServiceError: If note generation fails
        URLError: If video or transcript cannot be accessed
    """
    try:
        print("\n1. Fetching transcript...")
        start_time = time.time()
        transcript = get_transcript(url)
        print(f"✓ Transcript fetched! ({len(transcript)} entries)")
        
        print("\n2. Generating detailed notes...")
        print("This may take a few minutes for longer videos.")
        print("Progress will be shown as chunks are processed...")
        
        gpt_service = GPTService()
        notes = gpt_service.generate_notes(transcript, custom_prompt)
        
        total_time = time.time() - start_time
        print(f"\n✓ Notes generated successfully! (Total time: {total_time:.1f}s)")
        return notes
        
    except ValueError as e:
        raise ValueError(f"Invalid YouTube URL: {str(e)}")
    except URLError as e:
        raise URLError(f"Failed to access video: {str(e)}")
    except GPTServiceError as e:
        raise GPTServiceError(f"Note generation failed: {str(e)}")

if __name__ == "__main__":
    try:
        # Test URL
        url = "https://www.youtube.com/watch?v=GKeLVR3dPuI"
        print(f"Testing note generation for: {url}\n")
        
        notes = generate_video_notes(url)
        
        print("\nGenerated Notes:")
        print("=" * 80)
        print(notes)
        print("=" * 80)
        
    except (ValueError, URLError, GPTServiceError) as e:
        print(f"Error: {str(e)}") 