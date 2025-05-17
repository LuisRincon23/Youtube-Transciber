from PyQt6.QtCore import QThread, pyqtSignal
from transcript_service import get_transcript
from gpt_service import GPTService
from playlist_service import PlaylistService
import os

class PlaylistTranscriptionWorker(QThread):
    """Worker thread for handling playlist transcription."""
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    video_progress = pyqtSignal(int, int, str)  # current video, total videos, video title
    chunk_progress = pyqtSignal(int, int, str)  # current chunk, total chunks, chunk text

    def __init__(self, playlist_url):
        super().__init__()
        self.playlist_url = playlist_url
        self.playlist_service = PlaylistService()
        self.gpt_service = GPTService()

    def run(self):
        try:
            # Get playlist videos
            self.progress.emit("Fetching playlist information...")
            videos = self.playlist_service.get_playlist_videos(self.playlist_url)
            
            if not videos:
                raise Exception("No videos found in playlist or invalid playlist URL")

            # Create output directory
            playlist_title = f"Playlist_{len(videos)}_videos"
            output_dir = self.playlist_service.create_output_directory(playlist_title)
            
            all_transcripts = []
            all_notes = []
            
            # Process each video
            for i, video in enumerate(videos, 1):
                self.video_progress.emit(i, len(videos), video['title'])
                self.progress.emit(f"Processing video {i}/{len(videos)}: {video['title']}")
                
                try:
                    # Get transcript
                    transcript = get_transcript(video['url'])
                    
                    # Format raw transcript
                    raw_transcript = self.format_raw_transcript(transcript)
                    
                    # Generate notes
                    notes = self.gpt_service.generate_notes(transcript)
                    
                    # Save to file
                    self.save_transcript_and_notes(
                        output_dir,
                        video['title'],
                        raw_transcript,
                        notes
                    )
                    
                    all_transcripts.append(raw_transcript)
                    all_notes.append(notes)
                    
                except Exception as e:
                    self.progress.emit(f"Error processing video {video['title']}: {str(e)}")
                    continue
            
            self.finished.emit((output_dir, all_transcripts, all_notes))
            
        except Exception as e:
            self.error.emit(str(e))

    def format_raw_transcript(self, transcript):
        """Format raw transcript with timestamps."""
        formatted_lines = []
        for entry in transcript:
            minutes = int(entry['start'] // 60)
            seconds = int(entry['start'] % 60)
            formatted_lines.append(f"[{minutes:02d}:{seconds:02d}] {entry['text']}")
        return "\n".join(formatted_lines)

    def save_transcript_and_notes(self, output_dir, video_title, transcript, notes):
        """Save transcript and notes to files."""
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
        
        # Save transcript
        transcript_path = os.path.join(output_dir, f"{safe_title}_transcript.txt")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        # Save notes
        notes_path = os.path.join(output_dir, f"{safe_title}_notes.txt")
        with open(notes_path, 'w', encoding='utf-8') as f:
            f.write(notes) 