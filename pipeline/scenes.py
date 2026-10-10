"""Scene-first extraction of book windows (docs/04, *About the spot*).

    python -m pipeline.scenes <content_id>...       # bills: only the windows named
    python -m pipeline.scenes --source <id> --save  # bills: every pending window, saved

An index of the whole book, then a scene finder that writes no prose, then
the spot placed by the geocoder, then a short writer, then today's check and
rewrites. Every call is stored like a chunk, so a rerun is free. Prints the
cards; --save stores them through `extract.save_memories` (geocode, launch
area, retelling check), marks each window extracted, one commit a window, and
runs `tasks.after_save` (walk score, links, enrichment, the book's repeats).
Not yet in batch: full price, no worth-telling judge, no tags or dates.
"""

import argparse
import difflib
import json
import re

import anthropic
from sqlalchemy import text

from pipeline import extract, geocode, tasks
from pipeline.config import ANTHROPIC_API_KEY, LAUNCH_BBOX
from pipeline.db import get_session

INDEX_PROMPT = """You read a whole memoir about Copenhagen and write the index that a
later reader of any one passage of it will use: who each person is, and where
each place was, in today's terms.

- people: everyone the book names more than in passing. role: who they are, in
  at most 12 words, as the book makes clear ("the author's grandfather, a
  lime-burner", "Rahbek, critic and host of Bakkehuset").
- places: every place in Copenhagen the book tells something happening at.
  old_name: as the book writes it. today: where that was on today's map - a
  building, street or square a walker can find ("the yard of the royal
  porcelain factory, Købmagergade"), from the book, or from what you know for
  certain about Copenhagen's history; null if you are not sure. address:
  today's street (and number if known) or null. standing: "yes" if what the
  book describes can still be seen there, "no" if it is gone, "unknown".
  what: what the place was then, in plain words a stranger knows ("a water
  mill that ground quartz for the porcelain factory").

Plain English. Only places in or near Copenhagen."""

INDEX_SCHEMA = {
    "type": "object",
    "properties": {
        "people": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "role": {"type": "string"}},
                "required": ["name", "role"],
                "additionalProperties": False,
            },
        },
        "places": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "old_name": {"type": "string"},
                    "what": {"type": "string"},
                    "today": extract._NULLABLE_STRING,
                    "address": extract._NULLABLE_STRING,
                    "standing": {"type": "string", "enum": ["yes", "no", "unknown"]},
                },
                "required": ["old_name", "what", "today", "address", "standing"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["people", "places"],
    "additionalProperties": False,
}

FIND_PROMPT = """You find the scenes in one passage of a memoir about Copenhagen. A scene
is the stuff of a story a stranger would be glad to hear standing on the spot:
someone did something at one place, at one time, and it took a turn - a
surprise, a fall, a joke, a fright, a loss, a win.

One anecdote is one candidate. When one moment leads to the next - a fall in
the street that puts a brother on the stage - list it once, from where it
starts to its payoff, at the place where it starts. One event told across
several places - a king's death heard at the theatre, argued over at the
club, cheered on the square - is one candidate too, at the place of its
sharpest moment; the other places are its mentions.

The passage may open with <before>, the end of the passage before it. A scene
that begins there and ends in the passage is yours. A scene that runs past the
end of the passage is not: leave it out, the next passage tells it.

List every candidate in the order of the passage, to its end, also the ones
that fail, so each can be seen to fail:
- place_words: the words of the passage that name the place, copied exactly.
- index_place: that place's old_name in the index, or null.
- venue: where to stand today, as today's map of Copenhagen names it, in
  Danish, even when the text uses an old name ("Kongens Nytorv", "Rundetårn",
  "Assistens Kirkegård"). For a place that is gone, the street or square it
  stood on. Null if neither the passage nor the index says where it was.
- address: today's street and number, if known; else null.
- what_happens: one line, who did what.
- place_use: "scene" if the place is part of what happens - its purpose, its
  feature, the crowd it drew, what was seen from it; "setting" if it only
  happened there, in a home, shop or office where the same moment could have
  happened in any other ("a man entertained imaginary guests in his flat");
  "mention" if the place is only referred to (an event elsewhere, before or
  after, a home someone came from); "discourse" if it is a figure of speech or
  a comparison.
- shape: "scene" for one moment that unfolds; "list" for rooms, fittings,
  goods, owners; "lineage" for who begat whom, who married whom, who lived
  where; "chronicle" for years of a place's or a person's life told in turn;
  "description" for what a place looked like.
- turn: true if the moment takes a turn, false if nothing changes in it.
- theme: in at most 15 words, why a stranger standing there today would be
  glad to know it. Null if you cannot say it without "interesting" or
  "historic".
- start / end: the first and last 6-10 words of the scene, copied exactly.

The index and the brief are context for who and where; every scene comes from
the passage. An empty list is the right answer for a page of description."""

FIND_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "place_words": {"type": "string"},
                    "index_place": extract._NULLABLE_STRING,
                    "venue": extract._NULLABLE_STRING,
                    "address": extract._NULLABLE_STRING,
                    "what_happens": {"type": "string"},
                    "place_use": {
                        "type": "string",
                        "enum": ["scene", "setting", "mention", "discourse"],
                    },
                    "shape": {
                        "type": "string",
                        "enum": ["scene", "list", "lineage", "chronicle", "description"],
                    },
                    "turn": {"type": "boolean"},
                    "theme": extract._NULLABLE_STRING,
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                },
                "required": [
                    "place_words",
                    "index_place",
                    "venue",
                    "address",
                    "what_happens",
                    "place_use",
                    "shape",
                    "turn",
                    "theme",
                    "start",
                    "end",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["scenes"],
    "additionalProperties": False,
}

WRITE_PROMPT = """You write one story card for a walker standing on a spot in Copenhagen,
reading it on a phone. You get where they are standing, who the people are,
and the passage with the scene marked.

- The spot is the subject. Within the first two sentences the reader knows
  what of the story they are standing at - what they can see, or that it is
  gone and what is there now.
- Then the one scene, in order, with the details that make it: what was said
  or done, the object at the turn, the date. Not rooms, fittings or ancestors.
- The reader knows none of these people, the author included. Everyone named
  is introduced the first time, from the people given: who they were, and
  their age if it matters ("Otto Zinck, three years old, later an actor";
  "Thorvaldsen, the sculptor"). At most two people by name; anyone else by
  their role ("the boy's father", "a priest from the prison").
- Everyday words that a reader with school English knows: "harbour front",
  not "quay"; "nonsense", not "humbug". An old trade or thing is said in a few
  words of what it was.
- 60 to 150 words, past tense, English. Two short paragraphs past 90 words.
- Every fact comes from the passage or the spot and people given; add no
  name, date, image or adjective of your own.
- quote: the passage's best line about this moment in someone's own voice,
  copied exactly, at most 40 words, or null.

The examples show the range; do not copy their openings.

<examples>
<card>Ten years before his first play was staged inside these walls, Andersen,
fourteen and new to Copenhagen, circled the theatre as though it were home. A
man selling playbills held one out to him. Andersen took it as a gift and
thanked him warmly; the seller thought he was being mocked, and Andersen fled
in fright.</card>
<card>"I am the King," the masked man whispered at the door of Kasino, the
theatre that stood on this stretch of Amaliegade until the 1960s. It was a
carnival night, the crush at its worst, and he had no ticket. The old
doorkeeper, a Jutlander, was not impressed and made him wait until the Lord
Chamberlain arrived with it. It was the King. Afterwards he praised the
doorkeeper to the theatre's director.</card>
<card>Somewhere under these beeches, one spring morning, Andersen hugged a
tree. It was his first walk in open country in nearly three years. Sunlight,
the smell of leaves and birdsong overcame him; he shouted for joy, threw his
arms around a budding beech and kissed it. A palace servant watching asked,
"Is he mad?"</card>
<card>The square is quiet now, but a column of shame once stood here, raised
where the traitor Corfitz Ulfeldt's house was torn down, with butchers'
stalls all round. Oehlenschläger saw it as a boy and imagined the meat on the
hooks as offerings hung around an altar.</card>
</examples>"""

WRITE_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}, "quote": extract._NULLABLE_STRING},
    "required": ["summary", "quote"],
    "additionalProperties": False,
}

STOCK_OPENING = re.compile(
    r"(This\b|Here\b|On this spot|You are standing|The walker|Nothing (is )?(left|remains|of)"
    r"|(In|On|By|During) (the )?\d"
    r"|[\w' .-]{1,40}? (is|was) (where|the place)\b)",
    re.I,
)
SLACK = 80
REWRITES = 2
BEFORE_CHARS = 1500

PENDING_WINDOWS = """SELECT c.id FROM content c JOIN transcripts t ON t.content_id = c.id
WHERE c.source_id = :s AND NOT c.memories_extracted AND NOT c.extraction_failed ORDER BY c.id"""

PREVIOUS_WINDOW = """SELECT t.full_text FROM content c JOIN transcripts t ON t.content_id = c.id
WHERE c.source_id = :s AND c.id < :id ORDER BY c.id DESC LIMIT 1"""


def opening_fault(summary: str, seen: set[str]) -> str | None:
    """Why a card's first three words won't do, or None.

    A rule in the writer prompt becomes a template ("This was…" opened most
    cards), and the spot card invites "The old Royal Theatre…" six times over,
    so the opening is checked in code: no stock opening, no date first, and
    not the opening of a card already written.
    """
    words = " ".join(summary.split()[:3])
    if STOCK_OPENING.match(summary):
        return f'"{words}" is a stock opening'
    if words.lower() in seen:
        return f'"{words}" already opens another card'
    return None


def before(session, source_id: int, content_id: int) -> str:
    """The end of the window before, from a paragraph break: a scene cut by the
    window's edge (the elephant that eats the boy's cap) is told whole by the
    window it ends in."""
    prev = session.execute(text(PREVIOUS_WINDOW), {"s": source_id, "id": content_id}).scalar()
    if not prev:
        return ""
    tail = prev[-BEFORE_CHARS:]
    cut = tail.find("\n\n")
    return tail[cut + 2 :] if 0 <= cut < len(tail) // 2 else tail


def raw_at(chunk: str, n: int) -> int:
    """The index in chunk where its squashed form reaches n characters."""
    k = 0
    for i, ch in enumerate(chunk):
        if k >= n:
            return i
        k += len(extract._squash(ch))
    return len(chunk)


def reach(found: list[dict], chunk: str) -> int:
    """How far into the squashed chunk the candidates' ends reach."""
    whole, reached = extract._squash(chunk), 0
    for sc in found:
        end = extract._squash(sc["end"])
        if (at := whole.find(end)) >= 0:
            reached = max(reached, at + len(end))
    return reached


def copied(words: str, passage: str) -> bool:
    """The words are in the passage, in order, with room for what a scan puts
    between them: a running head and page number split "det nye kongelige
    Teater", and the theatre fall was dropped for it."""
    tokens = [re.escape(w) for w in map(extract._squash, words.split()) if w]
    return (
        bool(tokens)
        and re.search(f".{{0,{SLACK}}}?".join(tokens), extract._squash(passage)) is not None
    )


def kept(sc: dict, passage: str) -> bool:
    return bool(
        sc["place_use"] == "scene"
        and sc["shape"] == "scene"
        and sc["turn"]
        and sc["theme"]
        and copied(sc["place_words"], passage)
    )


def book_text(session, source_id: int) -> str:
    rows = session.execute(
        text("""SELECT t.full_text FROM content c JOIN transcripts t ON t.content_id = c.id
                WHERE c.source_id = :s ORDER BY c.id"""),
        {"s": source_id},
    ).fetchall()
    return "\n\n".join(r.full_text for r in rows)


def index_for(session, client, source_id: int, name: str) -> dict:
    first = session.execute(
        text("SELECT min(id) FROM content WHERE source_id = :s"), {"s": source_id}
    ).scalar()
    user = f"The book: {name}\n\n{book_text(session, source_id)}"
    raw = extract._stored_request(
        session, client, first, -10, INDEX_PROMPT, user, INDEX_SCHEMA, max_tokens=16000
    )
    return json.loads(raw)


def index_text(idx: dict) -> str:
    people = "\n".join(f"- {p['name']}: {p['role']}" for p in idx["people"])
    places = "\n".join(
        f"- {p['old_name']}: {p['what']}; today: {p['today']} ({p['standing']})"
        for p in idx["places"]
    )
    return f"<index>\nPeople:\n{people}\n\nPlaces:\n{places}\n</index>\n"


def find(session, client, cid: int, chunk: str, prior: str, ctx: str) -> list[dict]:
    """The candidates, asked again for the rest of the passage when the list
    stopped short: two windows came back with one candidate from their first
    page and nothing after it (docs/04, *Scene-first, before it ships*)."""

    def ask(passage, part):
        lead = f"<before>\n{prior}\n</before>\n\n" if prior and part == 0 else ""
        user = f"{lead}Passage:\n\n{passage}"
        raw = extract._stored_request(
            session, client, cid, part, FIND_PROMPT, user, FIND_SCHEMA, ctx, max_tokens=6000
        )
        return json.loads(raw)["scenes"] if raw else []

    found = ask(chunk, 0)
    done = reach(found, chunk)
    if found and done < len(extract._squash(chunk)) // 2:
        found += ask(chunk[raw_at(chunk, done) :], 1)
    return found


def resolve(sc: dict, idx: dict):
    """The spot from the finder's venue; the index only adds what it was then."""
    if not sc["venue"]:
        return None, None
    names = {p["old_name"].strip().lower(): p for p in idx["places"]}
    m = difflib.get_close_matches((sc["index_place"] or "").strip().lower(), names, 1, 0.8)
    then = names[m[0]] if m else None
    entry = {
        "today": sc["venue"],
        "address": sc["address"],
        "old_name": then["old_name"] if then else sc["place_words"],
        "what": then["what"] if then else "",
        "standing": then["standing"] if then else "unknown",
    }
    # The finder adds asides ("Holms Plads, ved Langebro"); the map knows the bare name.
    for venue in dict.fromkeys([sc["venue"], geocode.unbracket(sc["venue"]).split(",")[0]]):
        hit = geocode.place(sc["address"], venue, "Copenhagen", "DK", None, None)
        if hit:
            return entry, hit
    return entry, None


def spot_card(entry: dict) -> str:
    now = {"yes": "still there", "no": "gone", "unknown": "not known if still there"}
    address = f", {entry['address']}" if entry["address"] else ""
    what = f", {entry['what']}" if entry["what"] else ""
    return (
        f"<spot>\nThe walker stands at: {entry['today']}{address}.\n"
        f"Then: {entry['old_name']}{what}. Now: {now[entry['standing']]}.\n</spot>\n"
    )


def write(session, client, cid, passage, ctx, sc, entry, note=""):
    user = (
        f'{spot_card(entry)}\nThe scene runs from "{sc["start"]}" to "{sc["end"]}": '
        f"{sc['what_happens']}\n{note}\nPassage:\n\n{passage}"
    )
    raw = extract._stored_request(session, client, cid, 0, WRITE_PROMPT, user, WRITE_SCHEMA, ctx)
    return json.loads(raw) if raw else None


def cards(session, client, cid: int, idx_by_source: dict, seen: dict) -> list[dict]:
    r = session.execute(
        text("SELECT source_id, source_name, title FROM content WHERE id = :c"), {"c": cid}
    ).one()
    chunk = session.execute(
        text("SELECT full_text FROM transcripts WHERE content_id = :c"), {"c": cid}
    ).scalar()
    if r.source_id not in idx_by_source:
        idx_by_source[r.source_id] = index_for(session, client, r.source_id, r.source_name)
    idx = idx_by_source[r.source_id]
    seen = seen.setdefault(r.source_id, set())
    ctx = extract.source_context(r.source_name, r.title) + index_text(idx)
    prior = before(session, r.source_id, cid)
    passage = f"{prior}\n\n{chunk}" if prior else chunk

    out = []
    for sc in find(session, client, cid, chunk, prior, ctx):
        tag = f"[{sc['place_use']}/{sc['shape']}/turn={sc['turn']}] {sc['what_happens']}"
        entry, hit = resolve(sc, idx) if kept(sc, passage) else (None, None)
        if not entry:
            print(f"  drop  {tag}")
            continue
        if not hit:
            print(f"  drop, not on the map: {entry['today']}")
            continue
        if hit and LAUNCH_BBOX and not extract._in_box(hit[0], hit[1], LAUNCH_BBOX):
            print(f"  drop, outside the launch area: {entry['today']}")
            continue
        print(f"  keep  {tag} -> {entry['today']} ({hit[3]})")
        w = write(session, client, cid, passage, ctx, sc, entry)
        fault = w and opening_fault(w["summary"], seen)
        note = ""
        if fault:
            print(f"  reopen: {fault}")
            note = (
                f"Do not open as before: {fault}. Open with the person, the moment or a line said."
            )
            w = write(session, client, cid, passage, ctx, sc, entry, note) or w
        if not w:
            continue
        seen.add(" ".join(w["summary"].split()[:3]).lower())
        summary = faithful(session, client, cid, passage, ctx, sc, entry, w["summary"], note)
        if not summary:
            continue
        out.append(
            {
                "place": entry["today"],
                "summary": summary,
                "quote": w["quote"],
                "venue": entry["today"],
                "address": entry["address"],
                "locality": "Copenhagen",
                "region": "Capital Region of Denmark",
                "country": "DK",
                "lat": hit[0],
                "lng": hit[1],
                "location_precision": "street",
                "confidence": "high",
                "spot_test": "pass",
            }
        )
    return out


def faithful(session, client, cid, passage, ctx, sc, entry, summary: str, note: str) -> str | None:
    """The card with no fact the passage doesn't give, or None.

    The writer writes it again, told everything the check has named so far,
    up to REWRITES times; nothing is ever cut from it. The trim left fragments
    mid-sentence ("Retelling it later,", "he added a line."), which no guard
    sees, and one rewrite then a drop lost the theatre debut and the mother's
    grave to "sixteen" and "crying in secret" (docs/04, *Scene-first, before
    it ships*). A card with only colour left is kept as written.
    """
    context = ctx + spot_card(entry)
    named: list[str] = []
    for draw in range(REWRITES + 1):
        claims = extract.unsupported(session, client, cid, 0, passage, context, summary) or []
        if not any(c["kind"] == "fact" for c in claims):
            return summary
        named += [c["claim"] for c in claims if c["claim"] not in named]
        if draw == REWRITES:
            break
        print(f"  rewrite, unsupported: {'; '.join(c['claim'] for c in claims)}")
        leave_out = f"The passage does not say: {'; '.join(named)}. Leave these out; keep the rest."
        again = write(session, client, cid, passage, ctx, sc, entry, f"{note}\n{leave_out}".strip())
        if again and (fault := opening_fault(again["summary"], set())):
            reopen = (
                f"Do not open as before: {fault}. Open with the person, the moment or a line said."
            )
            note = f"{note}\n{reopen}".strip()
            again = write(session, client, cid, passage, ctx, sc, entry, f"{note}\n{leave_out}")
        if not again:
            return None
        summary = again["summary"]
    print(f"  dropped, still unsupported: {'; '.join(named)}")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("content_ids", type=int, nargs="*")
    parser.add_argument("--source", type=int, help="every window of this source not yet extracted")
    parser.add_argument("--save", action="store_true", help="save the cards as memories")
    args = parser.parse_args()
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    idx_by_source, seen = {}, {}
    with get_session() as s:
        ids = args.content_ids + [
            r.id
            for r in s.execute(text(PENDING_WINDOWS), {"s": args.source}).fetchall()
            if args.source
        ]
        for cid in ids:
            print(f"######## {cid}", flush=True)
            found = cards(s, client, cid, idx_by_source, seen)
            for c in found:
                print(f"--- {c['place']} ({len(c['summary'].split())}w)\n{c['summary']}\n")
            if args.save:
                extract.save_memories(s, cid, found, extract.layer_for("book"), client)
                s.execute(
                    text("UPDATE content SET memories_extracted = TRUE WHERE id = :id"), {"id": cid}
                )
                s.commit()
                tasks.after_save(client, cid)


if __name__ == "__main__":
    main()
