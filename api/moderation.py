"""Is this fit to show a stranger? App Store 1.2 wants a filter on what people
post, before anybody else reads it.

One Haiku call per post, a yes or a no. Refused is 422 and says so; a call that
fails is 503 and nothing is published, since an unscreened post cannot be
unpublished from the screens it already reached. SCREEN_POSTS=0 turns it off,
which tests and e2e do. docs/10-decisions.md#posts-are-screened-reports-need-an-account.
"""

import json
import logging

import anthropic
from fastapi import HTTPException

from pipeline.config import ANTHROPIC_API_KEY, CLASSIFIER_MODEL, SCREEN_POSTS

logger = logging.getLogger(__name__)

PROMPT = """You screen what people post on a public map of place memories:
short stories about something that happened at a spot, notes under them, and
the names they sign with. A stranger standing there will read it.

Refuse only:
- hate or harassment aimed at a person or a group
- sexual content, or anything sexual involving a minor
- threats, or encouraging violence or self-harm
- a private person's home address, phone number or other contact details
- spam or advertising

Everything else passes, including drinking, crime and death in the past,
swearing, sadness, politics and criticism of a business."""

SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


def screen(*texts: str | None) -> None:
    """Return if it may be shown; raise if it may not, or if nobody could judge."""
    body = "\n\n".join(t.strip() for t in texts if t and t.strip())
    if not SCREEN_POSTS or not body:
        return
    try:
        reply = client.messages.create(
            model=CLASSIFIER_MODEL,
            max_tokens=50,
            system=PROMPT,
            messages=[{"role": "user", "content": body}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
        ok = json.loads(reply.content[0].text)["ok"]
    except Exception as e:
        logger.error(f"Screening failed, refusing the post: {e}")
        raise HTTPException(status_code=503, detail="Can't check that right now") from e
    if not ok:
        raise HTTPException(status_code=422, detail={"reason": "refused"})
