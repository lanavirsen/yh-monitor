import os
import csv
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# URLs for YH search results, filtered to "Data/IT" and "sen anmälan".
SOURCES = {
    "on-site": "https://www.yrkeshogskolan.se/hitta-utbildning/sok/?area=data&latest-filter=clearing&place=12&start=638869248000000000&clearing=1&query=&sort=name",
    "remote": "https://www.yrkeshogskolan.se/hitta-utbildning/sok/?area=data&latest-filter=form&start=638869248000000000&clearing=1&form=2&query=&sort=name",
}

# Consistent schema for CSV output.
FIELDS = ["title", "provider", "start", "scope", "pace", "location", "link"]

# ---------------------------------------------------------------------------
# HTTP utilities
# ---------------------------------------------------------------------------


def build_headers() -> dict:
    """
    Construct a User-Agent header.
    - Always includes a GitHub repo link (identifies project clearly).
    - Optionally appends a contact address from the YH_CONTACT env var.
      This avoids hardcoding personal data into the public repo.
    """
    contact = os.getenv("YH_CONTACT", "").strip()
    ua = "yh-monitor (+https://github.com/lanavirsen/yh-monitor)"
    if contact:
        ua += f"; contact: {contact}"
    return {"User-Agent": ua}


def fetch_live(url: str) -> str:
    """
    Fetch the HTML of a YH search page.
    Timeout + error propagation are used to avoid silent hangs.
    """
    resp = requests.get(url, headers=build_headers(), timeout=30)
    resp.raise_for_status()
    return resp.text


# ---------------------------------------------------------------------------
# Parsing logic
# ---------------------------------------------------------------------------


def parse(html: str) -> list[dict]:
    """
    Parse a YH search results page into a list of structured dicts.
    Each dict represents one program and matches FIELDS.

    - Parsing is isolated into a pure function so it can be unit tested
      against offline HTML fixtures (see /fixtures).
    - If the website structure changes, only this function needs updating.
    """
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select("#search-list article")

    programs: list[dict] = []
    for article in articles:
        title_el = article.select_one("h1.h-byline")
        a_el = article.find("a", href=True)
        if not title_el or not a_el:
            # Defensive: skip malformed blocks rather than crashing.
            continue

        title = title_el.get_text(strip=True)
        link = "https://www.yrkeshogskolan.se" + a_el["href"]

        # Extract definition list pairs (dt -> dd).
        details = {}
        for dl in article.find_all("dl"):
            for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
                details[dt.get_text(strip=True)] = dd.get_text(strip=True)

        programs.append(
            {
                "title": title,
                "provider": details.get("Utbildningsanordnare", ""),
                "start": details.get("Nästa utbildningsstart", ""),
                "scope": details.get("Omfattning", ""),
                "pace": details.get("Studietakt", ""),
                "location": details.get("Studieort", ""),
                "link": link,
            }
        )
    return programs


# ---------------------------------------------------------------------------
# CSV utilities
# ---------------------------------------------------------------------------


def write_csv(path: Path, rows: list[dict]) -> None:
    """
    Write parsed program rows to a CSV file.
    Ensures consistent headers and creates parent dirs if needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def load_csv(path: Path) -> list[dict]:
    """
    Load rows from an existing CSV file, or return empty if none.
    Useful for comparing today's vs yesterday's scraped results.
    """
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------


def diff(today_rows: list[dict], y_rows: list[dict]) -> tuple[set, set]:
    """
    Compare two sets of rows by (title, provider, link).
    Returns (added, removed) as sets of tuples.

    Why tuple keys?
    - Guarantees uniqueness per program.
    - Ignores superficial changes in start date/scope/pace/location.
    """

    def key(row: dict) -> tuple[str, str, str]:
        return (row["title"], row["provider"], row["link"])

    tset = {key(r) for r in today_rows}
    yset = {key(r) for r in y_rows}
    return tset - yset, yset - tset


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """
    Command-line interface.
    - Default: parse offline fixtures (reliable for CI/CD and testing).
    - --live: fetch from real website (manual runs only).
    """
    ap = argparse.ArgumentParser(description="Monitor YH ‘sen anmälan’ programs.")
    ap.add_argument(
        "--live",
        action="store_true",
        help="Fetch from the website instead of fixtures.",
    )
    ap.add_argument(
        "--fixtures",
        default="fixtures",
        help="Directory with onsite.html / remote.html",
    )
    ap.add_argument("--out", default="data", help="Output directory (default: data)")
    args = ap.parse_args()

    today = datetime.now().strftime("%Y%m%d")
    yday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    fixtures = Path(args.fixtures)
    out = Path(args.out)

    for key, url in SOURCES.items():
        try:
            # Offline mode reads local HTML snapshots; Live mode fetches.
            if args.live:
                html = fetch_live(url)
            else:
                fname = "onsite.html" if key == "on-site" else "remote.html"
                html = (fixtures / fname).read_text(encoding="utf-8")

            rows = parse(html)

            folder = out / key
            today_csv = folder / f"{today}.csv"
            write_csv(today_csv, rows)

            y_csv = folder / f"{yday}.csv"
            added, removed = diff(load_csv(today_csv), load_csv(y_csv))

            if not added and not removed:
                print(f"[{key}] No changes.")
            else:
                for title, provider, link in sorted(added):
                    print(f"[{key}] + {title} by {provider} ({link})")
                for title, provider, link in sorted(removed):
                    print(f"[{key}] - {title} by {provider} ({link})")
        except Exception as e:
            # Print errors to stderr so CI/CD logs clearly show failures.
            print(f"[{key}] ERROR: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
