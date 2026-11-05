
import hashlib
import json
import logging
import os
import random
import re
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus

    httpx = None


# ==========================================================================
# LOGGING (with secret redaction)
# ==========================================================================

SECRET_ENV_NAMES = (
    "BUFFER_API_KEY",
    "GEMINI_API_KEY",
    "AI_HORDE_API_KEY",
    "CLOUDINARY_API_KEY",
    "CLOUDINARY_API_SECRET",
)


def _secret_values():
    values = []
    for name in SECRET_ENV_NAMES:
        value = (os.getenv(name) or "").strip()
        if len(value) >= 6:
            values.append(value)
    return values


def redact(text):
    """Remove every known secret value from a string."""
    text = str(text)
    for secret in _secret_values():
        text = text.replace(secret, "***")
    return text


class SecretRedactingFilter(logging.Filter):
    def filter(self, record):
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001
            return True
        record.msg = redact(message)
        record.args = ()
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
for _handler in logging.getLogger().handlers:
    _handler.addFilter(SecretRedactingFilter())

log = logging.getLogger("unique_news")


def describe_error(exc):
    """Short, secret-free description of an exception for logs."""
    return redact(f"{type(exc).__name__}: {exc}")[:600]


def gha(level, message):
    """GitHub Actions annotation (warning / error). Harmless elsewhere."""
    if os.getenv("GITHUB_ACTIONS") == "true":
        clean = redact(message).replace("\r", " ").replace("\n", " ")[:800]
        print(f"::{level}::{clean}", flush=True)


# ==========================================================================
# ENVIRONMENT VARIABLES
# ==========================================================================

def env(name, default=""):
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def env_int(name, default, low, high):
    raw = env(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        log.warning("%s is not a number (%r). Using default %d.", name, raw, default)
        return default
    return max(low, min(high, value))


def env_bool(name, default=True):
    raw = env(name).lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


BUFFER_API_KEY = env("BUFFER_API_KEY")
BUFFER_CHANNEL_ID = env("BUFFER_CHANNEL_ID")
GEMINI_API_KEY = env("GEMINI_API_KEY")
AI_HORDE_API_KEY = env("AI_HORDE_API_KEY")
CLOUDINARY_CLOUD_NAME = env("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = env("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = env("CLOUDINARY_API_SECRET")

TEXT_MODEL = env("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
MAX_ARTICLES_PER_RUN = env_int("MAX_ARTICLES_PER_RUN", 1, 1, 5)

ENABLE_STORIES = env_bool("ENABLE_STORIES", True)
AI_HORDE_TIMEOUT = env_int("AI_HORDE_TIMEOUT", 300, 60, 600)
RUN_BUDGET_SECONDS = env_int("RUN_BUDGET_SECONDS", 20 * 60, 300, 40 * 60)

REQUIRED_ENV = (
    "BUFFER_API_KEY",
    "BUFFER_CHANNEL_ID",
    "GEMINI_API_KEY",
    "CLOUDINARY_CLOUD_NAME",
    "CLOUDINARY_API_KEY",
    "CLOUDINARY_API_SECRET",
)

SEEN_FILE = Path("seen.json")
MAX_HISTORY = 1000
STATE_VERSION = 2

GEMINI_MAX_ATTEMPTS = 4
GEMINI_RETRY_DELAYS = (4, 12, 30)  # waits after attempt 1, 2, 3
GEMINI_TIMEOUT_MS = 60_000

MAX_REVIEWS_PER_RUN = 12          # max Gemini reviews per run
MAX_CONSECUTIVE_GEMINI_FAILURES = 2
MAX_AGE_HOURS = 36                # ignore older news
MAX_ITEMS_PER_FEED = 15
STORY_MAX_ATTEMPTS = 3
STORY_RETRY_WINDOW_HOURS = 12
MAX_STORY_RETRIES_PER_RUN = 2

BUFFER_API_URL = "https://api.buffer.com"
AI_HORDE_BASE = "https://aihorde.net/api/v2"

START_TIME = time.monotonic()
WORK_DIR = None  # created in main()
gemini_client = None

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "UniqueNewsBot/2.0 (+https://github.com/; github-actions)",
    "Accept": "*/*",
})


def time_left():
    return RUN_BUDGET_SECONDS - (time.monotonic() - START_TIME)


# ==========================================================================
# EXCEPTIONS
# ==========================================================================

class FatalError(Exception):
    """Configuration/authentication problem: stop the whole run."""


class StateError(Exception):
    """seen.json is unreadable. Stop instead of risking duplicate posts."""


class GeminiUnavailable(Exception):
    """Gemini failed for this article. Article must NOT be marked as seen."""


        if stats["feeds_queued"] == 0 and failures > 0:
            exit_code = 1

    except StateError as exc:
        log.error("%s", describe_error(exc))
        gha("error", describe_error(exc))
        exit_code = 1
    except FatalError as exc:
        log.error("Fatal configuration/authentication error: %s", describe_error(exc))
        gha("error", describe_error(exc))
        exit_code = 1
    except Exception as exc:  # noqa: BLE001
        log.error("Unexpected error: %s", describe_error(exc))
        gha("error", f"Unexpected error: {describe_error(exc)}")
        exit_code = 1

    log.info(
        "Finished. Feed queued: %d | Story queued: %d | Story failures: %d | "
        "Unsuitable: %d | Gemini failures: %d | Other failures: %d",
        stats["feeds_queued"], stats["stories_queued"], stats["story_failures"],
        stats["unsuitable"], stats["gemini_failures"], stats["other_failures"],
    )
    write_step_summary(stats)
    return exit_code


# ==========================================================================
# START
# ==========================================================================

if __name__ == "__main__":
    sys.exit(main())
