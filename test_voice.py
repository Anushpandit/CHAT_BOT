import os
from voice import transcribe_audio, text_to_speech
from dotenv import load_dotenv

load_dotenv()

print("Testing TTS...")
try:
    audio = text_to_speech("Hello world")
    print("TTS success, length:", len(audio))
except Exception as e:
    print("TTS failed:", repr(e))

print("Testing STT...")
try:
    with open("test.webm", "wb") as f:
        f.write(b"fake audio data")
    # This will fail to transcribe fake audio, but will tell us if API call shape is correct
    transcribe_audio(b"fake audio data")
except Exception as e:
    print("STT failed:", repr(e))
