"""pipeline/repin.py: the model picks a map candidate, never a coordinate."""

import pytest

from pipeline.geocode import Hit
from pipeline.repin import choose
from tests.fakes import FakeAnthropic

HITS = [
    Hit(55.6910, 12.5666, "Plejecentret Sølund", "Læssøesgade", None, "poi", "photon"),
    Hit(55.6411, 12.1865, "Sølund Station", None, None, "poi", "wikidata"),
]


@pytest.mark.parametrize(("answer", "picked"), [(0, HITS[0]), (1, HITS[1]), (-1, None), (7, None)])
def test_a_pick_is_one_of_the_candidates_or_nothing(answer, picked):
    fake = FakeAnthropic({"reason": "r", "choice": answer})
    assert choose(fake, "Sølund", ["A story."], HITS) == picked
