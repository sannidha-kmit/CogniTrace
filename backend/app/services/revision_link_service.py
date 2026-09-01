import re
import logging
from typing import Optional, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger("cognitrace.quiz.revision_link")


class RevisionLinkService:
    """
    Utility service for validating video URLs, converting timestamps,
    and generating precise video revision links without inventing fake timestamps.
    """

    @staticmethod
    def parse_timestamp_to_seconds(ts: Any) -> Optional[int]:
        """
        Convert MM:SS, HH:MM:SS, or numeric values into canonical integer seconds.
        Returns None if timestamp is invalid or missing. Never invents values.
        """
        if ts is None:
            return None
        if isinstance(ts, (int, float)):
            return max(0, int(ts))
        if not isinstance(ts, str):
            return None

        clean_ts = ts.strip()
        if not clean_ts or clean_ts.lower() in ["none", "null", "n/a", ""]:
            return None

        try:
            parts = list(map(float, clean_ts.split(":")))
            if len(parts) == 1:
                return max(0, int(parts[0]))
            elif len(parts) == 2:
                return max(0, int(parts[0] * 60 + parts[1]))
            elif len(parts) == 3:
                return max(0, int(parts[0] * 3600 + parts[1] * 60 + parts[2]))
        except Exception as err:
            logger.warning("Failed to parse timestamp '%s': %s", clean_ts, err)
        return None

    @staticmethod
    def format_seconds_to_timestamp(seconds: Optional[int]) -> Optional[str]:
        """
        Format canonical seconds into human-readable display string (MM:SS or HH:MM:SS).
        E.g. 272 -> '04:32', 3725 -> '01:02:05'
        """
        if seconds is None or seconds < 0:
            return None

        hrs = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60

        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    @staticmethod
    def extract_youtube_video_id(url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats.
        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        """
        if not url:
            return None
        url = url.strip()

        # youtu.be/VIDEO_ID
        short_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
        if short_match:
            return short_match.group(1)

        # youtube.com/watch?v=VIDEO_ID
        watch_match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
        if watch_match:
            return watch_match.group(1)

        # youtube.com/embed/VIDEO_ID
        embed_match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})', url)
        if embed_match:
            return embed_match.group(1)

        return None

    @classmethod
    def create_revision_url(
        cls,
        video_url: str,
        timestamp_seconds: Optional[int] = None
    ) -> str:
        """
        Generate safe, trusted video revision URL pointing directly to the concept timestamp.
        If timestamp is None, returns the clean base video URL.
        Never appends fake or hallucinated timestamps.
        """
        if not video_url or not video_url.strip():
            return ""

        clean_url = video_url.strip()

        # If no timestamp is provided or 0, return base URL
        if timestamp_seconds is None or timestamp_seconds < 0:
            return clean_url

        video_id = cls.extract_youtube_video_id(clean_url)
        if video_id:
            # Canonical standard YouTube format with timestamp
            return f"https://www.youtube.com/watch?v={video_id}&t={timestamp_seconds}s"

        # General URL fallback with t parameter
        parsed = urlparse(clean_url)
        query_params = parse_qs(parsed.query)
        query_params["t"] = [f"{timestamp_seconds}s"]
        new_query = urlencode(query_params, doseq=True)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
