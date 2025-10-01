"""
Monitor YH "sen anmälan" (Data/IT). Writes daily CSV snapshots and prints diff vs yesterday.

Ethics: single GET per source, 30s timeout, no schedule by default; optional contact via YH_CONTACT.
"""

import os
import sys
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple

import requests
from bs4 import BeautifulSoup


def load_csv(path: str) -> List[Dict[str, str]]:
    """Read a CSV (utf-8) into a list of dicts."""
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# Hard-coded search URLs (Data/IT; Gothenburg on-site and remote).
SOURCES: Dict[str, str] = {
    "on-site": "https://www.yrkeshogskolan.se/hitta-utbildning/sok/?area=data&latest-filter=clearing&place=12&start=638869248000000000&clearing=1&query=&sort=name",
    "remote":  "https://www.yrkeshogskolan.se/hitta-utbildning/sok/?area=data&latest-filter=form&start=638869248000000000&clearing=1&form=2&query=&sort=name",
}

# CSV columns; outputs under ./data (portable).
FIELDS = ["title", "provider", "start", "scope", "pace", "location", "link"]
BASE_DIR = str(Path(__file__).parent / "data")


def main() -> None:
    today_str = datetime.now().strftime("%Y%m%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Script started.")

    # Neutral User-Agent; optional contact via YH_CONTACT (no PII in repo).
    contact = os.getenv("YH_CONTACT", "").strip()
    ua = "yh-monitor (+https://github.com/your-username/your-repo)" + (f"; contact: {contact}" if contact else "")
    headers = {"User-Agent": ua}

    for category, url in SOURCES.items():
        try:
            # HTTP GET with 30s timeout; raise on non-2xx.
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()

            # Parse with lxml.
            soup = BeautifulSoup(resp.text, "lxml")
            articles = soup.select("#search-list article")

            programs: List[Dict[str, str]] = []
            for article in articles:
                # Skip card if title or link is missing.
                title_el = article.select_one("h1.h-byline")
                a_el = article.find("a", href=True)
                if not title_el or not a_el:
                    continue

                title = title_el.get_text(strip=True)
                href = a_el.get("href", "")
                link = ("https://www.yrkeshogskolan.se" + href) if href.startswith("/") else href

                # Map <dt>/<dd> label–value pairs.
                details: Dict[str, str] = {}
                for dl in article.find_all("dl"):
                    for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
                        details[dt.get_text(strip=True)] = dd.get_text(strip=True)

                programs.append({
                    "title": title,
                    "provider": details.get("Utbildningsanordnare", ""),
                    "start": details.get("Nästa utbildningsstart", ""),
                    "scope": details.get("Omfattning", ""),
                    "pace": details.get("Studietakt", ""),
                    "location": details.get("Studieort", ""),
                    "link": link,
                })

            # Write today’s snapshot to CSV.
            folder = os.path.join(BASE_DIR, category)
            os.makedirs(folder, exist_ok=True)
            today_path = os.path.join(folder, f"{today_str}.csv")
            with open(today_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(programs)

            # Diff vs yesterday if snapshot exists.
            yesterday_path = os.path.join(folder, f"{yesterday_str}.csv")
            if not os.path.exists(yesterday_path):
                print(f"[{category}] First run or no data for yesterday – skipping comparison.")
                continue

            # Use in-memory programs for today (avoid re-read).
            today_set: set[Tuple[str, str, str]] = {(p["title"], p["provider"], p["link"]) for p in programs}
            yesterday_set: set[Tuple[str, str, str]] = {
                (p["title"], p["provider"], p["link"]) for p in load_csv(yesterday_path)
            }

            added = sorted(today_set - yesterday_set)
            removed = sorted(yesterday_set - today_set)

            if not added and not removed:
                print(f"[{category}] No changes.")
            else:
                if added:
                    print(f"[{category}] New program(s) added:")
                    for title, provider, link in added:
                        print(f"  + {title} by {provider} ({link})")
                if removed:
                    print(f"[{category}] Program(s) removed:")
                    for title, provider, link in removed:
                        print(f"  - {title} by {provider} ({link})")

        except Exception as e:
            # Continue other categories on error.
            print(f"[{category}] ERROR: {e}", file=sys.stderr)

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Script finished.")


if __name__ == "__main__":
    main()
