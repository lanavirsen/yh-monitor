# YH Monitor (late applications)

This small script was originally written in summer 2025 while I was applying to Swedish *yrkeshögskola* programs.

I wanted an easy way to track Data/IT programs as *sen anmälan* (late application) spots were opening and closing throughout the summer.

The script fetches listings from **yrkeshogskolan.se**, saves them as daily CSV files, and shows what changed since yesterday.

## Prerequisites
- Python 3.11+
- `pip install -r requirements.txt`

## Usage

By default the script runs in **offline mode**, parsing saved HTML fixtures (located in `fixtures/onsite.html` and `fixtures/remote.html`).

This makes the project fully testable and safe to run in CI/CD pipelines.

To run against the real yrkeshogskolan.se site, use the `--live` flag:

```bash
python yh-monitor.py --live
```

The script writes CSV files into `./data/<category>/<YYYYMMDD>.csv.` 

Categories are on-site and remote.

## Optional contact in User-Agent (live mode only)

If you run in **live mode**, you can optionally include a contact in the request headers by setting the environment variable `YH_CONTACT`.

This is a common courtesy: it allows site administrators to identify who is making automated requests if there are issues.

```powershell
$env:YH_CONTACT="name@example.com"
python yh-monitor.py --live
```

## Notes

- The script is for educational/demo purposes.
- In live mode, it makes only a single request per category. Be considerate and do not schedule frequent runs against the site.
- In offline mode (default), it uses saved fixtures and does not perform any network requests.
