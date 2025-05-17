import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLineEdit, QPushButton, QTextEdit, QLabel, QMessageBox,
                             QProgressBar, QHBoxLayout, QTabWidget, QSplitter, QScrollArea,
                             QRadioButton, QGroupBox, QComboBox, QInputDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from transcript_service import get_transcript
from gpt_service import GPTService, GPTServiceError
from playlist_worker import PlaylistTranscriptionWorker
from openrouter_service import OpenRouterService, OpenRouterServiceError
import csv


class TranscriptionWorker(QThread):
    """Worker thread for handling transcription and note generation."""
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    # Added string parameter for detailed status
    chunk_progress = pyqtSignal(int, int, str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.progress.emit("Fetching transcript from YouTube...")
            transcript = get_transcript(self.url)

            # Format raw transcript
            self.progress.emit("Formatting transcript with timestamps...")
            raw_transcript = self.format_raw_transcript(transcript)

            self.progress.emit(
                f"Transcript fetched! Processing {len(transcript)} entries in chunks...")

            gpt_service = GPTService()

            # Monkey patch the print function in GPTService to emit progress
            def progress_callback(current, total, chunk_text):
                self.chunk_progress.emit(current, total, chunk_text)
                self.progress.emit(f"Processing chunk {current}/{total}...")

            original_print = print

            def custom_print(message):
                if "Processing chunk" in message:
                    try:
                        parts = message.split()
                        if len(parts) >= 3:
                            chunk_info = parts[2].split('/')
                            if len(chunk_info) == 2:
                                current = int(chunk_info[0])
                                total = int(chunk_info[1])
                                # Extract timestamp from current chunk being processed
                                chunk_start = (current - 1) * \
                                    5  # 5 minutes per chunk
                                chunk_end = current * 5
                                chunk_text = f"Processing {chunk_start:02d}:00 - {chunk_end:02d}:00"
                                progress_callback(current, total, chunk_text)
                    except (ValueError, IndexError):
                        original_print(message)
                else:
                    original_print(message)

            import builtins
            builtins.print = custom_print

            try:
                self.progress.emit("Initializing GPT for note generation...")
                notes = gpt_service.generate_notes(transcript)
            finally:
                builtins.print = original_print

            self.progress.emit("Finalizing notes...")
            self.finished.emit((raw_transcript, notes))
        except Exception as e:
            self.error.emit(str(e))

    def format_raw_transcript(self, transcript):
        """Format raw transcript with timestamps."""
        formatted_lines = []
        for entry in transcript:
            minutes = int(entry['start'] // 60)
            seconds = int(entry['start'] % 60)
            formatted_lines.append(
                f"[{minutes:02d}:{seconds:02d}] {entry['text']}")
        return "\n".join(formatted_lines)


class ChatWorker(QThread):
    """Worker thread for handling chat interactions."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, prompt, transcript_context):
        super().__init__()
        self.prompt = prompt
        self.transcript_context = transcript_context
        self.gpt_service = GPTService()

    def run(self):
        try:
            # Create a chat prompt that includes context and the user's question
            chat_prompt = f"""Based on the following transcript, please answer this question: {self.prompt}

Transcript context:
{self.transcript_context}

Please provide a detailed, accurate response based solely on the information in the transcript."""

            response = self.gpt_service.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant analyzing a transcript. Provide accurate, relevant information based solely on the transcript content."},
                    {"role": "user", "content": chat_prompt}
                ],
                temperature=0.3
            )

            self.finished.emit(response.choices[0].message.content)
        except Exception as e:
            self.error.emit(str(e))


class PostGenerationWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, prompt, transcript_context):
        super().__init__()
        self.prompt = prompt
        self.transcript_context = transcript_context

    def run(self):
        try:
            self.progress.emit("Generating post using OpenRouter...")
            service = OpenRouterService()
            result = service.generate_post(
                self.prompt, self.transcript_context)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    PROMPT_CSV = "saved_prompts.csv"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Transcriber")
        self.setMinimumSize(800, 600)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # URL input section
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "Enter YouTube URL (video or playlist)")
        url_layout.addWidget(self.url_input)

        # Mode selection
        mode_group = QGroupBox("Transcription Mode")
        mode_layout = QHBoxLayout()
        self.single_video_radio = QRadioButton("Single Video")
        self.playlist_radio = QRadioButton("Playlist")
        self.single_video_radio.setChecked(True)
        mode_layout.addWidget(self.single_video_radio)
        mode_layout.addWidget(self.playlist_radio)
        mode_group.setLayout(mode_layout)
        url_layout.addWidget(mode_group)

        layout.addLayout(url_layout)

        # Progress bars
        self.video_progress = QProgressBar()
        self.video_progress.setVisible(False)
        layout.addWidget(self.video_progress)

        self.chunk_progress = QProgressBar()
        self.chunk_progress.setVisible(False)
        layout.addWidget(self.chunk_progress)

        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Tab widget for transcript and notes
        self.tab_widget = QTabWidget()
        self.transcript_text = QTextEdit()
        self.notes_text = QTextEdit()
        self.generated_post_text = QTextEdit()  # New tab for generated post
        self.tab_widget.addTab(self.transcript_text, "Transcript")
        self.tab_widget.addTab(self.notes_text, "Notes")
        self.tab_widget.addTab(self.generated_post_text,
                               "Generated Post")  # Add new tab
        layout.addWidget(self.tab_widget)

        # Buttons
        button_layout = QHBoxLayout()
        self.transcribe_button = QPushButton("Transcribe")
        self.transcribe_button.clicked.connect(self.start_transcription)
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.generate_post_button = QPushButton("Generate Post")  # New button
        self.generate_post_button.clicked.connect(self.generate_post)
        self.copy_post_button = QPushButton("Copy Post")  # New button
        self.copy_post_button.clicked.connect(self.copy_post_to_clipboard)
        button_layout.addWidget(self.transcribe_button)
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.generate_post_button)
        button_layout.addWidget(self.copy_post_button)
        layout.addLayout(button_layout)

        # Prompt management UI
        prompt_mgmt_layout = QHBoxLayout()
        self.prompt_combo = QComboBox()
        self.load_prompts_from_csv()
        prompt_mgmt_layout.addWidget(QLabel("Saved Prompts:"))
        prompt_mgmt_layout.addWidget(self.prompt_combo)
        self.save_prompt_button = QPushButton("Save Current Prompt")
        self.save_prompt_button.clicked.connect(self.save_current_prompt)
        self.load_prompt_button = QPushButton("Load Selected Prompt")
        self.load_prompt_button.clicked.connect(self.load_selected_prompt)
        self.delete_prompt_button = QPushButton("Delete Selected Prompt")
        self.delete_prompt_button.clicked.connect(self.delete_selected_prompt)
        prompt_mgmt_layout.addWidget(self.save_prompt_button)
        prompt_mgmt_layout.addWidget(self.load_prompt_button)
        prompt_mgmt_layout.addWidget(self.delete_prompt_button)

        # Custom prompt input for post generation
        post_prompt_layout = QVBoxLayout()
        post_prompt_layout.addLayout(prompt_mgmt_layout)
        self.post_prompt_input = QTextEdit()
        self.post_prompt_input.setPlaceholderText(
            "Type your custom prompt for the post here. Example: 'Write a LinkedIn post summarizing the key insights from this transcript.'")
        post_prompt_layout.addWidget(QLabel("Custom Post Prompt:"))
        post_prompt_layout.addWidget(self.post_prompt_input)
        layout.addLayout(post_prompt_layout)

        # Chat section
        chat_layout = QVBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(
            "Ask a question about the transcript...")
        self.chat_button = QPushButton("Send")
        self.chat_button.clicked.connect(self.send_chat_message)
        chat_layout.addWidget(self.chat_input)
        chat_layout.addWidget(self.chat_button)
        layout.addLayout(chat_layout)

        self.chat_response = QTextEdit()
        self.chat_response.setReadOnly(True)
        layout.addWidget(self.chat_response)

        # Initialize workers
        self.transcription_worker = None
        self.playlist_worker = None
        self.chat_worker = None
        self.post_worker = None

    def start_transcription(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube URL")
            return

        # Clear previous results
        self.transcript_text.clear()
        self.notes_text.clear()
        self.chat_response.clear()

        # Show progress bars
        self.video_progress.setVisible(self.playlist_radio.isChecked())
        self.chunk_progress.setVisible(True)

        if self.playlist_radio.isChecked():
            self.start_playlist_transcription(url)
        else:
            self.start_single_transcription(url)

    def start_playlist_transcription(self, url):
        self.playlist_worker = PlaylistTranscriptionWorker(url)
        self.playlist_worker.progress.connect(self.update_status)
        self.playlist_worker.video_progress.connect(self.update_video_progress)
        self.playlist_worker.chunk_progress.connect(self.update_chunk_progress)
        self.playlist_worker.finished.connect(self.handle_playlist_success)
        self.playlist_worker.error.connect(self.handle_error)
        self.playlist_worker.start()

        self.transcribe_button.setEnabled(False)
        self.url_input.setEnabled(False)

    def start_single_transcription(self, url):
        """Start transcription for a single video."""
        self.transcription_worker = TranscriptionWorker(url)
        self.transcription_worker.progress.connect(self.update_status)
        self.transcription_worker.chunk_progress.connect(
            self.update_chunk_progress)
        self.transcription_worker.finished.connect(self.handle_single_success)
        self.transcription_worker.error.connect(self.handle_error)
        self.transcription_worker.start()

        self.transcribe_button.setEnabled(False)
        self.url_input.setEnabled(False)

    def update_video_progress(self, current, total, title):
        self.video_progress.setMaximum(total)
        self.video_progress.setValue(current)
        self.status_label.setText(
            f"Processing video {current}/{total}: {title}")

    def handle_playlist_success(self, result):
        output_dir, transcripts, notes = result
        self.transcribe_button.setEnabled(True)
        self.url_input.setEnabled(True)

        # Display the first video's transcript and notes
        if transcripts and notes:
            self.transcript_text.setText(transcripts[0])
            self.notes_text.setText(notes[0])

        QMessageBox.information(
            self,
            "Success",
            f"Playlist transcription completed!\n\n"
            f"Transcripts and notes have been saved to:\n{output_dir}"
        )

    def update_status(self, message):
        """Update status message."""
        self.status_label.setText(message)

    def update_chunk_progress(self, current, total, chunk_text):
        """Update progress bar and chunk status."""
        progress = int((current / total) * 100)
        self.chunk_progress.setValue(progress)
        self.status_label.setText(chunk_text)

    def handle_error(self, error_msg):
        """Handle transcription error."""
        QMessageBox.critical(
            self, "Error", f"Failed to transcribe: {error_msg}")
        self.transcribe_button.setEnabled(True)
        self.url_input.setEnabled(True)
        self.status_label.setText("Error occurred during processing")
        self.chunk_progress.hide()

    def copy_to_clipboard(self):
        """Copy current tab content to clipboard."""
        clipboard = QApplication.clipboard()
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            clipboard.setText(current_tab.toPlainText())
            self.status_label.setText(
                f"Content from {self.tab_widget.tabText(self.tab_widget.currentIndex())} copied to clipboard!")

    def send_chat_message(self):
        """Handle sending a chat message."""
        if not self.transcript_text.toPlainText():
            QMessageBox.warning(
                self, "Error", "Please transcribe a video first")
            return

        message = self.chat_input.text().strip()
        if not message:
            return

        # Disable input while processing
        self.chat_input.setEnabled(False)
        self.chat_button.setEnabled(False)

        # Add user message to chat history
        self.chat_response.append(f"<b>You:</b> {message}")
        self.chat_input.clear()

        # Create and start chat worker
        self.chat_worker = ChatWorker(
            message, self.transcript_text.toPlainText())
        self.chat_worker.finished.connect(self.handle_chat_response)
        self.chat_worker.error.connect(self.handle_chat_error)
        self.chat_worker.start()

    def handle_chat_response(self, response):
        """Handle successful chat response."""
        self.chat_response.append(f"<b>AI:</b> {response}\n")
        self.chat_input.setEnabled(True)
        self.chat_button.setEnabled(True)
        self.chat_input.setFocus()

    def handle_chat_error(self, error_msg):
        """Handle chat error."""
        QMessageBox.critical(
            self, "Error", f"Failed to get response: {error_msg}")
        self.chat_input.setEnabled(True)
        self.chat_button.setEnabled(True)

    def handle_single_success(self, result):
        """Handle successful single video transcription."""
        transcript, notes = result
        self.transcribe_button.setEnabled(True)
        self.url_input.setEnabled(True)

        self.transcript_text.setText(transcript)
        self.notes_text.setText(notes)

        self.status_label.setText("Transcription completed successfully!")
        self.chunk_progress.setVisible(False)

    def generate_post(self):
        """Generate a post using OpenRouter and the transcript context."""
        transcript = self.transcript_text.toPlainText()
        prompt = self.post_prompt_input.toPlainText().strip()
        if not transcript:
            QMessageBox.warning(
                self, "Error", "Please transcribe a video first.")
            return
        if not prompt:
            QMessageBox.warning(
                self, "Error", "Please enter a custom prompt for the post.")
            return
        self.generated_post_text.clear()
        self.status_label.setText("Generating post...")
        self.generate_post_button.setEnabled(False)
        self.post_prompt_input.setEnabled(False)
        self.post_worker = PostGenerationWorker(prompt, transcript)
        self.post_worker.progress.connect(self.update_status)
        self.post_worker.finished.connect(self.handle_post_success)
        self.post_worker.error.connect(self.handle_post_error)
        self.post_worker.start()

    def handle_post_success(self, result):
        self.generated_post_text.setText(result)
        self.status_label.setText("Post generated successfully!")
        self.generate_post_button.setEnabled(True)
        self.post_prompt_input.setEnabled(True)
        self.tab_widget.setCurrentWidget(self.generated_post_text)

    def handle_post_error(self, error_msg):
        QMessageBox.critical(
            self, "Error", f"Failed to generate post: {error_msg}")
        self.status_label.setText("Error occurred during post generation")
        self.generate_post_button.setEnabled(True)
        self.post_prompt_input.setEnabled(True)

    def copy_post_to_clipboard(self):
        """Copy generated post to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.generated_post_text.toPlainText())
        self.status_label.setText("Generated post copied to clipboard!")

    def load_prompts_from_csv(self):
        self.prompt_combo.clear()
        try:
            with open(self.PROMPT_CSV, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    self.prompt_combo.addItem(row['name'], row['prompt'])
        except FileNotFoundError:
            pass
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load prompts: {e}")

    def save_current_prompt(self):
        name, ok = QInputDialog.getText(
            self, "Save Prompt", "Enter a name for this prompt:")
        if not ok or not name.strip():
            return
        prompt = self.post_prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Error", "Prompt text is empty.")
            return
        # Read all prompts
        prompts = []
        found = False
        try:
            with open(self.PROMPT_CSV, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['name'] == name:
                        row['prompt'] = prompt
                        found = True
                    prompts.append(row)
        except FileNotFoundError:
            pass
        # Add new if not found
        if not found:
            prompts.append({'name': name, 'prompt': prompt})
        # Write all prompts
        with open(self.PROMPT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['name', 'prompt'])
            writer.writeheader()
            writer.writerows(prompts)
        self.load_prompts_from_csv()
        self.status_label.setText(f"Prompt '{name}' saved.")

    def load_selected_prompt(self):
        idx = self.prompt_combo.currentIndex()
        if idx < 0:
            return
        prompt = self.prompt_combo.itemData(idx)
        if prompt:
            self.post_prompt_input.setPlainText(prompt)
            self.status_label.setText(
                f"Loaded prompt '{self.prompt_combo.currentText()}'.")

    def delete_selected_prompt(self):
        idx = self.prompt_combo.currentIndex()
        if idx < 0:
            return
        name = self.prompt_combo.currentText()
        # Read all prompts
        prompts = []
        try:
            with open(self.PROMPT_CSV, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['name'] != name:
                        prompts.append(row)
        except FileNotFoundError:
            return
        # Write back
        with open(self.PROMPT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['name', 'prompt'])
            writer.writeheader()
            writer.writerows(prompts)
        self.load_prompts_from_csv()
        self.status_label.setText(f"Prompt '{name}' deleted.")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
