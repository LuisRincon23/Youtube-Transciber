from transcript_service import get_transcript

# Test with a public YouTube video
try:
    # Using a short YouTube video for testing
    transcript = get_transcript("https://www.youtube.com/watch?v=jNQXAC9IVRw")
    print("First few lines of transcript:")
    for entry in transcript[:3]:  # Print first 3 entries
        print(f"[{entry['start']}s]: {entry['text']}")
except Exception as e:
    print(f"Error: {e}") 