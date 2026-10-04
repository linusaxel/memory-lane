"""Stand-ins for services the loop is forbidden from calling for real.

The loop may not spend Anthropic credits, so every test that touches the
extraction path uses FakeAnthropic. That proves chunking, prompt assembly,
response parsing and DB writes. It does NOT prove extraction quality -
that is parked as W1-09 for a human.
"""

import json


class _Content:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Usage:
    input_tokens = 0
    cache_read_input_tokens = 0
    cache_creation_input_tokens = 0
    output_tokens = 0


class _Response:
    model = "fake"
    stop_reason = "end_turn"
    usage = _Usage()

    def __init__(self, text):
        self.content = [_Content(text)]


class _Messages:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Response(json.dumps(self._payload))


class FakeAnthropic:
    """Drop-in for anthropic.Anthropic that never touches the network.

    fake = FakeAnthropic([{...memory...}])
    fake.messages.calls   -> every request that would have been sent
    """

    def __init__(self, payload=None):
        if payload is None:
            payload = [
                {
                    "place_words": "Katz's",
                    "happened_there": "Mark and Joe argued over the pastrami at the counter.",
                    "spot_test": "pass",
                    "venue": "Katz's Delicatessen",
                    "locality": "New York",
                    "region": "New York, USA",
                    "lat": 40.7223,
                    "lng": -73.9874,
                    "summary": "Mark and Joe argued about pastrami for twenty minutes.",
                    "tags": ["food", "personal"],
                    "confidence": "high",
                    "location_precision": "exact",
                    "timestamp_start": 12.5,
                }
            ]
        self.messages = _Messages(payload)
