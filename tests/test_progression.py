"""XP and level from finished walks (api/progression.py)."""

from api.progression import level, walk_xp


def test_levels_come_slower_as_they_climb():
    assert [level(x) for x in (0, 49, 50, 199, 200, 450)] == [1, 1, 2, 2, 3, 4]
    assert walk_xp(5, 5000) == 100
