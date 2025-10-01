from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yh_monitor import parse

def test_parse_onsite_fixture():
    html = (Path("fixtures") / "onsite.html").read_text(encoding="utf-8")
    rows = parse(html)
    assert isinstance(rows, list)
    if rows:
        r = rows[0]
        for k in ["title","provider","start","scope","pace","location","link"]:
            assert k in r
