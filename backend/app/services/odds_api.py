import os
import logging
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASE_URL = os.getenv('ODDS2_API_URL')
API_KEY = os.getenv('ODDS2_API_KEY')


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


def fetch_odds(path: str = '', params: dict | None = None):
    """Generic proxy to the secondary odds provider with retries and logging.

    Returns: (status_code, json_or_text)
    """
    if not BASE_URL or not API_KEY:
        logger.error('Odds provider not configured: ODDS2_API_URL or ODDS2_API_KEY missing')
        return 500, {'error': 'Odds provider not configured'}

    base = BASE_URL.rstrip('/')
    url = base + '/' + path.lstrip('/') if path else base

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'x-api-key': API_KEY,
    }

    session = _create_session()
    try:
        logger.debug('Requesting odds: %s params=%s', url, params)
        resp = session.get(url, headers=headers, params=params, timeout=15)
        logger.info('Odds request %s -> %s', resp.request.url, resp.status_code)
    except Exception as e:
        logger.exception('Odds request failed: %s %s', url, e)
        return 502, {'error': 'request_failed', 'details': str(e)}

    try:
        data = resp.json()
    except Exception:
        logger.warning('Odds response not JSON: status=%s text=%s', resp.status_code, resp.text[:500])
        return resp.status_code, {'text': resp.text}

    if resp.status_code >= 400:
        logger.error('Odds API returned error %s: %s', resp.status_code, str(data)[:1000])

    return resp.status_code, data
