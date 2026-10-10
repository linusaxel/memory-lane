from pipeline.scenes import copied, opening_fault, raw_at, reach


def test_opening_fault():
    seen = {"the old royal"}
    assert opening_fault("This was where the mill stood.", seen)
    assert opening_fault("In 1827 a rope-dancer came.", seen)
    assert opening_fault("The old Royal Theatre is gone.", seen)
    assert opening_fault("Here, on the quay, a bear cub sat.", seen)
    assert opening_fault("This drill ground was where Roat fell.", seen)
    assert opening_fault("The walker is on Østergade.", seen)
    assert opening_fault("A bear cub sat with its back to the bulwark.", seen) is None
    assert opening_fault("Heiberg laughed.", seen) is None
    assert opening_fault("Tivoli is where the night ended.", seen)
    assert opening_fault("Kongens Nytorv was where the theatre stood.", seen)
    assert opening_fault("Tivoli hired a pianist.", seen) is None


def test_reach_finds_where_the_list_stopped():
    chunk = "Første side, en scene. " + "Mere tekst. " * 50
    found = [{"end": "en scene."}]
    done = reach(found, chunk)
    assert chunk[raw_at(chunk, done) :].startswith(". Mere")
    assert reach([], chunk) == 0


def test_copied_across_a_page_break():
    passage = "paa det nye\n\nOtto Zinck: Erindringer 3\n\n34\n\nkongelige Teater, som da"
    assert copied("det nye kongelige Teater", passage)
    assert not copied("det gamle kongelige Teater", passage)
    assert not copied("det nye Teater", "det nye " + "x" * 200 + " Teater")


def test_an_unsupported_fact_is_written_again_never_cut(monkeypatch):
    from pipeline import scenes

    entry = {
        "today": "Kongens Nytorv",
        "address": None,
        "old_name": "",
        "what": "",
        "standing": "no",
    }
    flags = {
        "first": [{"claim": "two colleagues", "kind": "fact"}],
        "second": [{"claim": "sixteen", "kind": "fact"}],
        "flourish": [{"claim": "glittering", "kind": "colour"}],
        "bad": [{"claim": "a date", "kind": "fact"}],
    }
    draws, notes = [], []

    def write(*a):
        notes.append(a[-1])
        return {"summary": draws.pop(0), "quote": None}

    monkeypatch.setattr(scenes.extract, "unsupported", lambda *a: flags.get(a[-1], []))
    monkeypatch.setattr(scenes, "write", write)

    draws[:] = ["second", "clean"]
    assert scenes.faithful(None, None, 1, "", "", {}, entry, "first", "") == "clean"
    assert "two colleagues" in notes[-1] and "sixteen" in notes[-1]

    assert scenes.faithful(None, None, 1, "", "", {}, entry, "flourish", "") == "flourish"

    draws[:] = ["bad", "bad"]
    assert scenes.faithful(None, None, 1, "", "", {}, entry, "first", "") is None
