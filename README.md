# YH Monitor (late applications)

This small script was originally written in summer 2025 while I was applying to Swedish *yrkeshögskola* programs.

I wanted an easy way to track Data/IT programs that still had *sen anmälan* (late application) spots open.

The script fetches listings from **yrkeshogskolan.se**, saves them as daily CSV files, and shows what changed since yesterday

## Prerequisites
- Python 3.11+
- `pip install -r requirements.txt`

## Usage
Run the script:
```bash
python yh-monitor.py
```

The script writes CSV files into `./data/<category>/<YYYYMMDD>.csv.` 

Categories are on-site and remote.

## Optional contact in User-Agent

You can set an environment variable if you want to include a contact in the requests:
```powershell
$env:YH_CONTACT="name@example.com"
python yh-monitor.py
```

## Notes

- The script is for educational/demo purposes.
- It makes only a single request per category and should not be run too frequently.
- Default mode uses live scraping.
