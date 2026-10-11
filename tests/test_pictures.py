from pipeline import pictures

FILE = {
    "title": "File:Nyhavn 1970.jpg",
    "url": "https://upload.wikimedia.org/a.jpg",
    "thumb": "https://upload.wikimedia.org/a_1024.jpg",
    "page": "https://commons.wikimedia.org/wiki/File:Nyhavn_1970.jpg",
    "caption": "Sailors dancing in Nyhavn",
    "date": "1970",
    "categories": "Nyhavn",
    "author": "A. Photographer",
    "license": "CC BY-SA 2.0",
    "lat": 55.6797,
    "lng": 12.5907,
}
SEEN = {
    "moment": True,
    "occasion": True,
    "striking": 4,
    "venue": "Nyhavn",
    "address": None,
    "happened_at": "1970",
    "happened_precision": "year",
    "summary": "Sailors danced on the quay.",
    "tags": [],
}


def test_a_moment_keeps_commons_point_and_its_picture(monkeypatch):
    monkeypatch.setattr(pictures.walk_score, "walk_score", lambda *a: 7)
    monkeypatch.setattr(pictures.commons, "files", lambda titles: [FILE])
    monkeypatch.setattr(pictures, "look", lambda *a: SEEN)
    mem, picture = pictures.card(None, None, 1, FILE["page"], "caption", set())
    assert (mem["lat"], mem["lng"]) == (FILE["lat"], FILE["lng"])
    assert picture["url"] == FILE["url"] and picture["license"] == "CC BY-SA 2.0"


def test_an_unfree_or_still_picture_is_dropped(monkeypatch):
    monkeypatch.setattr(pictures, "look", lambda *a: SEEN)
    monkeypatch.setattr(pictures.commons, "files", lambda t: [FILE | {"license": "CC BY-NC 2.0"}])
    assert pictures.card(None, None, 1, FILE["page"], "c", set()) is None
    monkeypatch.setattr(pictures.commons, "files", lambda t: [FILE])
    monkeypatch.setattr(pictures, "look", lambda *a: SEEN | {"moment": False})
    assert pictures.card(None, None, 1, FILE["page"], "c", set()) is None


def test_the_walk_score_sees_a_picture_memorys_picture(monkeypatch):
    from pipeline import walk_score

    asked = []
    monkeypatch.setattr(walk_score, "image_block", lambda url: {"type": "image", "url": url})
    monkeypatch.setattr(
        walk_score,
        "_request",
        lambda c, prompt, user, *a, **k: asked.append((prompt, user)) or '{"score": 7}',
    )
    assert walk_score.walk_score(None, "Nyhavn: sailors danced.", "https://x/a.jpg") == 7
    assert walk_score.walk_score(None, "Nyhavn: sailors danced.") == 7
    assert asked[0][0] == walk_score.PICTURE_PROMPT and asked[0][1][0]["url"] == "https://x/a.jpg"
    assert asked[1][0] == walk_score.PROMPT, "a story without a picture is scored as before"


def test_a_series_is_looked_at_once(monkeypatch):
    monkeypatch.setattr(pictures.walk_score, "walk_score", lambda *a: 7)
    monkeypatch.setattr(pictures, "look", lambda *a: SEEN)
    monkeypatch.setattr(
        pictures.commons, "files", lambda t: [FILE | {"caption": "Show at Vega 01"}]
    )
    looked = set()
    assert pictures.card(None, None, 1, FILE["page"], "c", looked)
    monkeypatch.setattr(
        pictures.commons, "files", lambda t: [FILE | {"caption": "Show at Vega 02"}]
    )
    assert pictures.card(None, None, 2, FILE["page"], "c", looked) is None


def test_a_picture_under_good_is_never_made(monkeypatch):
    monkeypatch.setattr(pictures, "look", lambda *a: SEEN)
    monkeypatch.setattr(pictures.commons, "files", lambda t: [FILE])
    monkeypatch.setattr(pictures.walk_score, "walk_score", lambda *a: pictures.GOOD - 1)
    assert pictures.card(None, None, 1, FILE["page"], "c", set()) is None


def test_an_old_homepages_gif_is_sent_as_a_gif(monkeypatch):
    from crawler import commons
    from pipeline.extract import image_block

    monkeypatch.setattr(commons, "download", lambda url, ua: b"GIF89a\x01\x00")
    assert image_block("https://x/a.jpg")["source"]["media_type"] == "image/gif"


def test_a_picture_gone_from_its_page_is_scored_as_the_story_alone(monkeypatch):
    from pipeline import walk_score

    def _gone(url):
        raise OSError("404")

    asked = []
    monkeypatch.setattr(walk_score, "image_block", _gone)
    monkeypatch.setattr(
        walk_score, "_request", lambda c, prompt, *a, **k: asked.append(prompt) or '{"score": 6}'
    )
    assert walk_score.walk_score(None, "Nyhavn: sailors danced.", "https://x/gone.jpg") == 6
    assert asked == [walk_score.PROMPT]
