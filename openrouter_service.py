import os
import requests
from dotenv import load_dotenv

load_dotenv()


class OpenRouterServiceError(Exception):
    pass


class OpenRouterService:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise OpenRouterServiceError(
                "OpenRouter API key not found in environment variables")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        # You can change this to another model if desired
        self.model = "openai/gpt-3.5-turbo"

    def generate_post(self, prompt: str, transcript_context: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Generate a high-quality post using the provided prompt and transcript context."},
                {"role": "user", "content": f"Prompt: {prompt}\n\nTranscript context:\n{transcript_context}"}
            ],
            "temperature": 0.7
        }
        try:
            response = requests.post(
                self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            raise OpenRouterServiceError(f"OpenRouter API error: {str(e)}")
