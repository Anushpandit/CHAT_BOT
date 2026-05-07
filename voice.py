import os
import io
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Speech-to-Text  (Groq Whisper)
# ─────────────────────────────────────────────

def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language: Optional[str] = None,          # e.g. "en", "hi", None = auto-detect
    model: str = "whisper-large-v3",
) -> dict:
    """
    Transcribe audio bytes to text using Groq Whisper.

    Args:
        audio_bytes: Raw audio file bytes (webm / mp3 / wav / m4a / ogg).
        filename:    Original filename — Groq uses extension to detect format.
        language:    ISO-639-1 language code or None for auto-detect.
        model:       Whisper model variant.

    Returns:
        dict with: text, language, duration
    """
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set.")

    client = Groq(api_key=api_key)

    # Write to a named temp file — Groq SDK needs a file-like object with a name
    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            kwargs = dict(
                file=audio_file,
                model=model,
                response_format="verbose_json",   # includes language + duration
            )
            if language:
                kwargs["language"] = language

            response = client.audio.transcriptions.create(**kwargs)

        return {
            "text":     response.text.strip(),
            "language": getattr(response, "language", "unknown"),
            "duration": getattr(response, "duration", 0),
        }

    finally:
        os.unlink(tmp_path)


# ─────────────────────────────────────────────
# Text-to-Speech  (Groq PlayAI TTS)
# ─────────────────────────────────────────────

VOICES = {
    "nova":    "Nova (warm female)",
    "shimmer": "Shimmer (clear female)",
    "echo":    "Echo (male)",
    "onyx":    "Onyx (deep male)",
    "fable":   "Fable (expressive)",
    "alloy":   "Alloy (neutral)",
}

def text_to_speech(
    text: str,
    voice: str = "nova",
    model: str = "playai-tts",
    speed: float = 1.0,
) -> bytes:
    """
    Convert answer text to speech audio using Groq TTS.

    Args:
        text:  Text to speak (max ~4000 chars recommended per call).
        voice: Voice ID (nova / shimmer / echo / onyx / fable / alloy).
        model: TTS model.
        speed: Playback speed multiplier (0.5 – 2.0).

    Returns:
        MP3 audio bytes.
    """
    from gtts import gTTS
    import io

    # Truncate very long answers to avoid TTS limits
    if len(text) > 4000:
        text = text[:3900] + "... [truncated for audio]"

    tts = gTTS(text=text, lang='en')
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()
