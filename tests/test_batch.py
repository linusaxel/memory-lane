"""A batch pass collects one stage per content and saves nothing; the batch's
replies are stored where the next pass reads them (pipeline/batch.py)."""

from types import SimpleNamespace as NS

import anthropic
import pytest
from sqlalchemy import text

from pipeline import enrich, extract
from pipeline.batch import dollars, dropped, send
from pipeline.extract import Collect, _stored_request
from tests.fakes import _Response


@pytest.fixture
def collecting():
    extract.COLLECT = Collect()
    yield extract.COLLECT
    extract.COLLECT = None


def _rows(db_session):
    return db_session.execute(text("SELECT count(*) FROM extraction_chunks")).scalar()


@pytest.mark.db
def test_a_pass_collects_only_the_first_stage_to_miss(db_session, collecting):
    assert _stored_request(db_session, None, 7, 0, "extract", "chunk one") is None
    assert _stored_request(db_session, None, 7, 1, "extract", "chunk two") is None
    # The judge would read the chunks' answers: not paid for until they exist.
    assert _stored_request(db_session, None, 7, -2, "judge", "candidates") is None
    assert collecting.stage == {7: "extract"}
    assert [r["chunk_index"] for r in collecting.requests.values()] == [0, 1]
    assert _rows(db_session) == 0


class _Batches:
    def __init__(self, replies):
        self.replies = replies

    def create(self, requests):
        self.keys = [r["custom_id"] for r in requests]
        return NS(id="b1", processing_status="ended")

    def results(self, batch_id):
        for key, reply in zip(self.keys, self.replies, strict=True):
            if reply is None:
                yield NS(custom_id=key, result=NS(type="errored"))
                continue
            message = _Response(reply[0])
            message.stop_reason = reply[1]
            yield NS(custom_id=key, result=NS(type="succeeded", message=message))


@pytest.mark.db
def test_a_batch_reply_is_stored_where_the_next_pass_reads_it(db_session, collecting, caplog):
    cid = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=bbbbbbbbbbb', 'youtube', 'bbbbbbbbbbb') "
            "RETURNING id"
        )
    ).scalar()
    for i in range(3):
        _stored_request(db_session, None, cid, i, "extract", f"chunk {i}")
    requests, extract.COLLECT = collecting.requests, None
    batches = _Batches([('{"memories": []}', "end_turn"), ('{"memo', "max_tokens"), None])
    client = NS(messages=NS(batches=batches))
    assert send(client, requests, db_session) == 1
    assert _stored_request(db_session, None, cid, 0, "extract", "chunk 0") == '{"memories": []}'
    assert _rows(db_session) == 1
    assert f"[content:{cid}] extract cut" in caplog.text, "a cut reply names its stage"


def test_a_reply_is_priced_from_its_usage_at_half_price():
    usage = NS(
        input_tokens=1_000_000,
        cache_creation_input_tokens=1_000_000,
        cache_read_input_tokens=1_000_000,
        output_tokens=1_000_000,
        server_tool_use=NS(web_search_requests=3),
    )
    # Sonnet 5.5 halved: $1 in, $2 for the 1-hour write, $0.10 read, $5 out, 3 searches.
    assert dollars(NS(model="claude-sonnet-5-5", usage=usage)) == pytest.approx(8.13)
    assert dollars(NS(model="fake", usage=usage)) is None


class _Blip(_Batches):
    """A batch still running, whose first poll hits a network blip."""

    def create(self, requests):
        super().create(requests)
        self.polls = 0
        return NS(id="b1", processing_status="in_progress")

    def retrieve(self, batch_id):
        self.polls += 1
        if self.polls == 1:
            raise anthropic.APIConnectionError(request=None)
        return NS(id=batch_id, processing_status="ended", request_counts=None)


@pytest.mark.db
def test_a_network_blip_while_polling_does_not_drop_the_batch(db_session, collecting, monkeypatch):
    monkeypatch.setattr("pipeline.batch.time.sleep", lambda s: None)
    cid = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=ccccccccccc', 'youtube', 'ccccccccccc') "
            "RETURNING id"
        )
    ).scalar()
    _stored_request(db_session, None, cid, 0, "extract", "chunk 0")
    requests, extract.COLLECT = collecting.requests, None
    batches = _Blip([('{"memories": []}', "end_turn")])
    assert send(NS(messages=NS(batches=batches)), requests, db_session) == 1
    assert batches.polls == 2


@pytest.mark.db
def test_a_run_that_stops_early_still_scores_what_it_saved(db_session, monkeypatch):
    from contextlib import contextmanager

    from pipeline import batch, tasks

    @contextmanager
    def _session():
        yield db_session

    monkeypatch.setattr(batch, "get_session", _session)
    saved = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, memories_extracted) "
            "VALUES ('https://www.youtube.com/watch?v=ddddddddddd', 'youtube', 'ddddddddddd', true) "
            "RETURNING id"
        )
    ).scalar()

    def _one_call_left(ids):
        extract.COLLECT.requests["k"] = {}

    monkeypatch.setattr(extract, "extract_all_pending", _one_call_left)
    monkeypatch.setattr(batch, "send", lambda client, requests, session: 0)
    scored = []
    monkeypatch.setattr(tasks, "after_save", lambda client, cid: scored.append(cid))
    with pytest.raises(SystemExit):
        batch.run(None, [saved])
    assert scored == [saved]


@pytest.mark.db
def test_a_chosen_id_that_is_not_pending_says_why(db_session):
    source = db_session.execute(
        text(
            "INSERT INTO sources (kind, locator, name, status) "
            "VALUES ('text', 'adl:x', 'S', 'candidate') RETURNING id"
        )
    ).scalar()
    cid = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_id) "
            "VALUES ('https://example.org/x', 'web', 'x', :s) RETURNING id"
        ),
        {"s": source},
    ).scalar()
    assert dropped(db_session, [cid, -1], []) == [
        "-1: no such content",
        f"{cid}: its source is candidate",
    ]


@pytest.mark.db
def test_a_run_prints_one_funnel_per_content_from_its_last_pass(db_session, monkeypatch, capsys):
    from contextlib import contextmanager

    from pipeline import batch, tasks

    @contextmanager
    def _session():
        yield db_session

    monkeypatch.setattr(batch, "get_session", _session)
    passes = iter([(4, {"k": {}}), (6, {})])

    def _pass(ids):
        raw, extract.COLLECT.requests = next(passes)
        extract.COLLECT.funnel[7] = {"raw": raw, "judge": 1}

    monkeypatch.setattr(extract, "extract_all_pending", _pass)
    monkeypatch.setattr(batch, "send", lambda client, requests, session: 1)
    monkeypatch.setattr(tasks, "after_save", lambda client, cid: None)
    batch.run(None, [7])
    assert capsys.readouterr().out == "content 7: 6 raw, 1 judge, 0 saved\n"


def _content(db_session, platform_id):
    return db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) VALUES (:url, 'web', :p) RETURNING id"
        ),
        {"url": f"https://example.org/{platform_id}", "p": platform_id},
    ).scalar()


@pytest.mark.db
def test_research_is_collected_and_read_back_after_its_batch(db_session, collecting):
    cid = _content(db_session, "vega")
    assert enrich.research(db_session, None, cid, "Vega", "the amp caught fire") is None
    [request] = collecting.requests.values()
    assert request["stage"] == "research" and request["params"]["tools"]
    requests, extract.COLLECT = collecting.requests, None
    batches = _Batches([("Notes from the web.", "end_turn")])
    assert send(NS(messages=NS(batches=batches)), requests, db_session) == 1
    assert enrich.research(db_session, None, cid, "Vega", "the amp caught fire") == (
        "Notes from the web."
    )


@pytest.mark.db
def test_a_thin_record_waiting_on_its_research_is_not_marked_done(db_session, collecting):
    from pipeline.tasks import seeded

    cid = _content(db_session, "plaque")
    assert seeded(db_session, None, cid, "A plaque", [{"text": "HER FALDT EJLER"}]) is None
    assert cid in collecting.stage
    done = db_session.execute(
        text("SELECT memories_extracted FROM content WHERE id = :id"), {"id": cid}
    ).scalar()
    assert not done


@pytest.mark.db
def test_an_enrichment_waiting_on_its_pictures_is_not_saved_without_them(
    db_session, collecting, monkeypatch
):
    monkeypatch.setattr(enrich, "research", lambda *a: pytest.fail("research is paused"))
    picture = {"caption": "Vega, 1996", "year": None, "source": True}
    monkeypatch.setattr(enrich, "source_pictures", lambda *a: [picture])
    args = ("Vega", "the amp caught fire", None, None, None, None, "https://example.org/v")
    assert enrich.enrich(db_session, None, 7, *args) is None
    assert len(collecting.requests) == 1
