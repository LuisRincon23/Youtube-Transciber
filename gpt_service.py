import os
from openai import OpenAI, APIError, APIConnectionError, AuthenticationError
from dotenv import load_dotenv
import math

# Load environment variables
load_dotenv()

class GPTServiceError(Exception):
    """Base exception class for GPT service errors"""
    pass

class GPTService:
    def __init__(self):
        """Initialize OpenAI client with API key from environment."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise GPTServiceError("OpenAI API key not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        
        # Chunk size in minutes (reduced for more granular processing)
        self.chunk_duration = 5  # Process 5 minutes at a time for more detail
        
    def _chunk_transcript(self, transcript: list) -> list:
        """Split transcript into chunks based on time."""
        chunks = []
        current_chunk = []
        chunk_start_time = transcript[0]['start'] if transcript else 0
        
        for entry in transcript:
            # If this entry is within our chunk duration, add it
            if (entry['start'] - chunk_start_time) <= (self.chunk_duration * 60):
                current_chunk.append(entry)
            else:
                # Save current chunk and start a new one
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = [entry]
                chunk_start_time = entry['start']
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def _format_chunk(self, chunk: list) -> str:
        """Format a chunk of transcript entries into a readable string."""
        return "\n".join([
            f"[{int(entry['start'] // 60):02d}:{int(entry['start'] % 60):02d}] {entry['text']}"
            for entry in chunk
        ])

    def _process_chunk(self, chunk: list) -> str:
        """Process a single chunk of the transcript."""
        try:
            chunk_text = self._format_chunk(chunk)
            prompt = f"""Analyze this transcript section and create detailed notes following these strict requirements:

1. Format:
   - Use proper markdown formatting
   - Each main point must start with a timestamp [MM:SS]
   - Use bold (**) for key concepts/topics
   - Use bullet points (-) for main points
   - Use sub-bullets (*) for supporting details or examples

2. Content Requirements:
   - Identify and explain every key concept mentioned
   - Include specific examples or scenarios discussed
   - Capture any definitions or explanations given
   - Note any important relationships between concepts
   - Include any warnings, cautions, or important notes

3. Output Structure:
   - [MM:SS] **Key Concept/Topic**: Detailed explanation
     * Supporting detail or example
     * Additional context
     * Related information
   - [MM:SS] **Next Key Concept**: ...

Transcript to analyze:
{chunk_text}"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise note-taking assistant. Create detailed, structured notes that capture every important concept with exact timestamps. Be thorough and maintain consistent formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content

        except Exception as e:
            raise GPTServiceError(f"Failed to process chunk: {str(e)}")

    def generate_notes(self, transcript: list, custom_prompt: str = None) -> str:
        """Generate notes from transcript using GPT."""
        try:
            if not transcript:
                raise GPTServiceError("Empty transcript provided")

            # Split transcript into manageable chunks
            chunks = self._chunk_transcript(transcript)
            chunk_notes = []
            
            # Process each chunk
            total_chunks = len(chunks)
            for i, chunk in enumerate(chunks, 1):
                print(f"Processing chunk {i}/{total_chunks}...")
                chunk_note = self._process_chunk(chunk)
                chunk_notes.append(chunk_note)
            
            # If we have multiple chunks, create a final summary
            if len(chunk_notes) > 1:
                all_notes = "\n\n".join(chunk_notes)
                final_prompt = f"""Combine these section notes into a comprehensive document following these requirements:

1. Structure:
   - Start with a brief overview of the content
   - Group related concepts together under clear section headers
   - Maintain ALL timestamps and detailed bullet points
   - Keep chronological order within each section
   - Preserve all specific examples and details

2. Formatting:
   - Use markdown headers (## for sections)
   - Keep the [MM:SS] timestamp format
   - Maintain bold (**) formatting for key concepts
   - Use consistent bullet points (-) and sub-bullets (*)
   - Add a horizontal line (---) between major sections

3. Content:
   - Ensure no important details are lost in consolidation
   - Keep all specific examples and context
   - Maintain the relationship between connected concepts
   - Preserve all technical details and definitions

Notes to combine:
{all_notes}"""

                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a precise documentation specialist. Create a well-structured, comprehensive document that maintains all important details and ensures consistent formatting."},
                        {"role": "user", "content": final_prompt}
                    ],
                    temperature=0.3
                )
                
                return response.choices[0].message.content
            
            return chunk_notes[0]

        except AuthenticationError as e:
            raise GPTServiceError(f"Authentication failed: {str(e)}")
        except APIConnectionError as e:
            raise GPTServiceError(f"Failed to connect to OpenAI API: {str(e)}")
        except APIError as e:
            raise GPTServiceError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise GPTServiceError(f"Unexpected error: {str(e)}")

# Example usage:
# gpt_service = GPTService()
# notes = gpt_service.generate_notes(transcript)
# Or with custom prompt:
# notes = gpt_service.generate_notes(transcript, "Summarize this video focusing on {transcript}") 