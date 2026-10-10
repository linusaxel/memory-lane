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
    monkeypatch.setattr(pictures.commons, "files", lambda titles: [FILE])
    monkeypatch.setattr(pictures, "look", lambda *a: SEEN)
    mem, picture = pictures.card(None, None, 1, FILE["page"], "caption")
    assert (mem["lat"], mem["lng"]) == (FILE["lat"], FILE["lng"])
    assert picture["url"] == FILE["url"] and picture["license"] == "CC BY-SA 2.0"


def test_an_unfree_or_still_picture_is_dropped(monkeypatch):
    monkeypatch.setattr(pictures, "look", lambda *a: SEEN)
    monkeypatch.setattr(pictures.commons, "files", lambda t: [FILE | {"license": "CC BY-NC 2.0"}])
    assert pictures.card(None, None, 1, FILE["page"], "c") is None
    monkeypatch.setattr(pictures.commons, "files", lambda t: [FILE])
    monkeypatch.setattr(pictures, "look", lambda *a: SEEN | {"moment": False})
    assert pictures.card(None, None, 1, FILE["page"], "c") is None


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
