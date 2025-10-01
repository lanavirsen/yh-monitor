from yh_monitor import diff


def test_diff_added_and_removed():
    yesterday = [
        {"title": "A", "provider": "X", "link": "u1"},
        {"title": "B", "provider": "Y", "link": "u2"},
    ]
    today = [
        {"title": "B", "provider": "Y", "link": "u2"},  # unchanged
        {"title": "C", "provider": "Z", "link": "u3"},  # new
    ]
    added, removed = diff(today, yesterday)
    assert added == {("C", "Z", "u3")}
    assert removed == {("A", "X", "u1")}
