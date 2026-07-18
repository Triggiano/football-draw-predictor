import os
import sys
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the backend folder regardless of current working directory
script_dir = Path(__file__).resolve().parent
dotenv_path = script_dir.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Fallback: if python-dotenv didn't load variables (some environments/tools
# may not pick them up), parse the .env file manually and set missing vars.
import os
if not os.getenv("ODDS_API_URL") or not os.getenv("ODDS_API_KEY"):
    try:
        with open(dotenv_path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if not os.getenv(k):
                        os.environ[k] = v
    except FileNotFoundError:
        pass

API_URL = os.getenv("ODDS_API_URL")
API_KEY = os.getenv("ODDS_API_KEY")

if not API_URL:
    print("ODDS_API_URL not set in environment. Please set it in backend/.env")
    sys.exit(1)

if not API_KEY:
    print("ODDS_API_KEY not set in environment. Please set it in backend/.env")
    sys.exit(1)

# football-data.org expects the API key in the X-Auth-Token header
headers = {
    "X-Auth-Token": API_KEY
}

try:
    # If the provided URL is the API root, request the matches endpoint for today
    from datetime import date, timedelta

    # Allow optional command-line overrides for date range
    import argparse
    parser = argparse.ArgumentParser(description='Test football-data /matches')
    parser.add_argument('--dateFrom', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--dateTo', help='End date (YYYY-MM-DD)')
    args = parser.parse_args()

    today = date.today()
    default_from = today
    default_to = today + timedelta(days=7)

    date_from = args.dateFrom if args.dateFrom else default_from.isoformat()
    date_to = args.dateTo if args.dateTo else default_to.isoformat()

    target = API_URL.rstrip('/') + '/matches'
    params = {'dateFrom': date_from, 'dateTo': date_to}
    resp = requests.get(target, headers=headers, params=params, timeout=15)
except Exception as e:
    print("Request failed:", e)
    sys.exit(1)

print("Request:", resp.request.url)
print("Status:", resp.status_code)

try:
    data = resp.json()
except Exception:
    print("Response is not JSON:\n", resp.text)
    sys.exit(1)

# Attempt to find matches list in response
matches = None
if isinstance(data, list):
    matches = data
elif isinstance(data, dict):
    # common keys
    for key in ("matches", "data", "events", "games", "response"):
        if key in data and isinstance(data[key], list):
            matches = data[key]
            break

if matches is None:
    print("No matches list found in response JSON. Here's the full JSON:\n", data)
    sys.exit(0)

print("Matches returned:", len(matches))
for i, m in enumerate(matches[:10], 1):
    print(i, m)
