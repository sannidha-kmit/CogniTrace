import os
import tempfile
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Callable
from bson import ObjectId

import yt_dlp
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None  # type: ignore  # faster-whisper not installed; transcript generation unavailable

from app.core.config import settings

logger = logging.getLogger("cognitrace.transcript")


def format_seconds(seconds: float) -> str:
    """Format floating point seconds into MM:SS or HH:MM:SS string."""
    if seconds is None or seconds < 0:
        return "00:00"
    total_sec = int(round(seconds))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class TranscriptService:
    _model_instance = None  # WhisperModel instance or None

    @classmethod
    def get_model(cls):
        """Lazy-load and cache the Faster-Whisper model instance."""
        if WhisperModel is None:
            raise RuntimeError("faster-whisper is not installed. Transcript generation is unavailable.")
        if cls._model_instance is None:
            logger.info("Loading Faster-Whisper model size='%s', device='%s', compute_type='%s'...",
                        settings.WHISPER_MODEL_SIZE, settings.WHISPER_DEVICE, settings.WHISPER_COMPUTE_TYPE)
            try:
                cls._model_instance = WhisperModel(
                    settings.WHISPER_MODEL_SIZE,
                    device=settings.WHISPER_DEVICE,
                    compute_type=settings.WHISPER_COMPUTE_TYPE
                )
                logger.info("Faster-Whisper model loaded successfully.")
            except Exception as err:
                logger.error("Failed to load Faster-Whisper model: %s", err)
                raise RuntimeError(f"Whisper Model loading error: {err}")
        return cls._model_instance

    @staticmethod
    def extract_audio(
        youtube_url: str,
        progress_callback: Optional[Callable[[int, str, str], None]] = None
    ) -> Tuple[str, float, float]:
        """
        Extract audio from YouTube video using yt-dlp with mweb/android player clients.
        Returns tuple of (audio_file_path, duration_seconds, file_size_mb).
        """
        temp_dir = tempfile.gettempdir()
        temp_filename = f"cognitrace_yt_{ObjectId()}"
        out_template = os.path.join(temp_dir, f"{temp_filename}.%(ext)s")

        if progress_callback:
            progress_callback(5, "DOWNLOADING", "Downloading YouTube video audio stream...")

        ydl_opts = {
            'format': 'ba[ext=m4a]/ba/b',
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['mweb', 'android', 'web']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            duration = info.get('duration', 0.0)

        if progress_callback:
            progress_callback(12, "EXTRACTING_AUDIO", "Audio extraction complete. Preparing Faster-Whisper model...")

        # Locate downloaded audio file
        possible_files = [
            os.path.join(temp_dir, f)
            for f in os.listdir(temp_dir)
            if f.startswith(temp_filename)
        ]

        if not possible_files:
            raise RuntimeError("Audio extraction failed. No audio file downloaded.")

        audio_path = possible_files[0]
        size_bytes = os.path.getsize(audio_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)

        return audio_path, float(duration), float(size_mb)

    @classmethod
    def transcribe_audio_file(
        cls,
        audio_path: str,
        total_duration: float = 0.0,
        progress_callback: Optional[Callable[[float, float, str], None]] = None
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Transcribe an audio file using Faster-Whisper and report real-time percentage progress.
        Returns (segments_list, detected_language).
        """
        model = cls.get_model()
        segments_gen, info = model.transcribe(audio_path, beam_size=5)

        segments = []
        last_logged_pct = -10

        for seg in segments_gen:
            text = seg.text.strip()
            if text:
                start_fmt = format_seconds(seg.start)
                end_fmt = format_seconds(seg.end)
                
                seg_obj = {
                    "start": round(float(seg.start), 2),
                    "end": round(float(seg.end), 2),
                    "text": text,
                    "TranscriptStart": start_fmt,
                    "TranscriptEnd": end_fmt
                }
                segments.append(seg_obj)

                # Report real progress to worker callback
                if progress_callback and total_duration > 0:
                    progress_callback(float(seg.end), float(total_duration), f"Transcribing audio: {end_fmt} / {format_seconds(total_duration)}")

                # Log percentage progress in console
                if total_duration > 0:
                    pct = min(100, int((seg.end / total_duration) * 100))
                    if pct >= last_logged_pct + 10 or pct == 100:
                        print(f"  [Transcribing] {pct}% completed ({start_fmt} - {end_fmt})")
                        logger.info("Transcribing progress: %d%% (%s - %s)", pct, start_fmt, end_fmt)
                        last_logged_pct = pct

        return segments, info.language
