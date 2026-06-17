import speech_recognition as sr
import os
from typing import Optional

class SpeechHandler:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        """Transcribes an audio file to text."""
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data)
                return text
        except Exception as e:
            print(f"Speech recognition error: {e}")
            return None

    def transcribe_from_mic(self) -> Optional[str]:
        """
        Note: This usually works locally. 
        In a Streamlit cloud environment, you'd use streamlit-mic-recorder.
        """
        try:
            with sr.Microphone() as source:
                print("Listening...")
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio)
                return text
        except Exception as e:
            print(f"Mic error: {e}")
            return None
