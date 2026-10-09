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


def test_an_unsupported_claim_is_written_again_not_cut(monkeypatch):
    from pipeline import scenes

    entry = {
        "today": "Kongens Nytorv",
        "address": None,
        "old_name": "",
        "what": "",
        "standing": "no",
    }
    notes = []

    def claims(*a):
        return [{"claim": "two colleagues", "kind": "fact"}] if a[-1] == "first" else []

    def write(*a):
        notes.append(a[-1])
        return {"summary": "second", "quote": None}

    monkeypatch.setattr(scenes.extract, "unsupported", claims)
    monkeypatch.setattr(scenes.extract, "checked", lambda *a: a[-1])
    monkeypatch.setattr(scenes, "write", write)
    assert scenes.faithful(None, None, 1, "", "", {}, entry, "first", "") == "second"
    assert "two colleagues" in notes[0]
    assert scenes.faithful(None, None, 1, "", "", {}, entry, "clean", "") == "clean"
    assert len(notes) == 1
