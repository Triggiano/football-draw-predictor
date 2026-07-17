import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Tuple, List, Dict, Any
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Ensure environment variables from backend/.env are loaded when the module is imported
# backend/.env is two levels up from this file (app/services/.. -> app -> backend)
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

BASE_URL = os.getenv("ODDS_API_URL")
API_KEY = os.getenv("ODDS_API_KEY")

HEADERS = {"X-Auth-Token": API_KEY} if API_KEY else {}


def _create_session(total_retries: int = 3, backoff_factor: float = 1.0) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(['GET', 'POST'])
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount('https://', adapter)
    s.mount('http://', adapter)
    return s


def _get(path: str, params: dict | None = None) -> Tuple[int, Any]:
    if not BASE_URL:
        logger.error('football-data URL not configured')
        return 500, {"error": "football-data URL not configured"}
    url = BASE_URL.rstrip("/") + "/" + path.lstrip("/")
    session = _create_session()
    try:
        logger.debug('Requesting football-data: %s params=%s', url, params)
        r = session.get(url, headers=HEADERS, params=params, timeout=15)
        logger.info('football-data request %s -> %s', r.request.url, r.status_code)
    except Exception as e:
        logger.exception('football-data request failed: %s %s', url, e)
        return 502, {"error": "request_failed", "details": str(e)}
    try:
        return r.status_code, r.json()
    except Exception:
        logger.warning('football-data response not JSON: status=%s text=%s', r.status_code, r.text[:500])
        return r.status_code, {"text": r.text}


def get_matches(params: dict | None = None) -> Tuple[int, Any]:
    return _get("matches", params=params)


def get_team_info(team_id: int) -> Tuple[int, Any]:
    return _get(f"teams/{team_id}")


def get_team_matches(team_id: int, params: dict | None = None) -> Tuple[int, Any]:
    return _get(f"teams/{team_id}/matches", params=params)


def get_recent_history(team_id: int, limit: int = 5) -> Tuple[int, List[Dict[str, Any]]]:
    # Fetch recent matches for team and return the most recent `limit` matches
    status, data = get_team_matches(team_id, params={"limit": limit, "status": "FINISHED"})
    if status != 200:
        return status, data
    matches = data.get("matches") if isinstance(data, dict) else []
    return 200, matches[:limit]


def get_head2head(team1: int, team2: int, limit: int = 10) -> Tuple[int, List[Dict[str, Any]]]:
    # Fetch matches for team1 and filter those where opponent == team2
    status, data = get_team_matches(team1, params={"limit": 100})
    if status != 200:
        return status, data
    matches = data.get("matches", []) if isinstance(data, dict) else []
    h2h = []
    for m in matches:
        # match contains 'homeTeam' and 'awayTeam' with 'id'
        home = m.get("homeTeam", {}).get("id")
        away = m.get("awayTeam", {}).get("id")
        if home == team2 or away == team2:
            h2h.append(m)
        if len(h2h) >= limit:
            break
    return 200, h2h


def get_competition_standings(competition_id: int) -> Tuple[int, Any]:
    return _get(f"competitions/{competition_id}/standings")
