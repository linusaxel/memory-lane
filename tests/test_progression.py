"""XP, level and loot from finished walks (api/progression.py)."""

from types import SimpleNamespace

from api.progression import level, progress, walk_xp


def test_levels_come_slower_as_they_climb():
    assert [level(x) for x in (0, 49, 50, 199, 200, 450)] == [1, 1, 2, 2, 3, 4]
    assert walk_xp(5, 5000) == 100


def test_loot_is_the_same_on_every_read_and_every_level_up_drops():
    walks = [SimpleNamespace(id=i, stops=3, budget_meters=3000) for i in range(1, 9)]
    xp, items = progress(walks)
    assert xp == 480 and level(xp) == 4
    assert progress(walks) == (xp, items)
    assert sum(i.count for i in items) >= 3
