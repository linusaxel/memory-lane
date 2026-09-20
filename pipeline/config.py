"""Every environment knob the pipeline reads, in one place.

extract.py and tasks.py each used to read the same five variables, and the chunk
defaults were hardcoded a third time in chunk_transcript's signature. Three
sources of truth for one value is how CLASSIFIER_MODEL drifted to an ID that
does not exist.
"""

import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "claude-sonnet-4-20250514")
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "claude-haiku-4-5")
CHUNK_MINUTES = int(os.getenv("CHUNK_MINUTES", "4"))
CHUNK_OVERLAP_SECONDS = int(os.getenv("CHUNK_OVERLAP_SECONDS", "30"))
