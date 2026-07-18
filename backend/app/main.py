from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.services.odds_api import fetch_odds
from app.services.football_data import (
    get_matches,
    get_team_info,
    get_team_matches,
    get_recent_history,
    get_head2head,
)
from app.services.evaluator import evaluate_match
from app import scheduler as app_scheduler
from app import logging_config

app = FastAPI()

# Allow the Next.js dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "StalemateProtocol API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get('/odds-proxy')
async def odds_proxy(request: Request, path: str = ''):
    """Proxy endpoint to forward requests to the secondary odds provider.

    Query parameters are forwarded; use `path` query param to specify
    the provider path (for example `v1/odds`).
    """
    # Build params dict excluding the control 'path' param
    params = {k: v for k, v in request.query_params.items() if k != 'path'}
    status, data = fetch_odds(path=path, params=params)
    return JSONResponse(status_code=status, content=data)


@app.get('/fixtures')
async def fixtures(request: Request):
    params = dict(request.query_params)
    # If no date range provided, default to the next 7 days to return useful results
    if 'dateFrom' not in params and 'dateTo' not in params:
        from datetime import date, timedelta
        today = date.today()
        params['dateFrom'] = today.isoformat()
        params['dateTo'] = (today + timedelta(days=7)).isoformat()
    status, data = get_matches(params=params)
    return JSONResponse(status_code=status, content=data)


@app.get('/teams/{team_id}')
async def team_info(team_id: int):
    status, data = get_team_info(team_id)
    return JSONResponse(status_code=status, content=data)


@app.get('/teams/{team_id}/matches')
async def team_matches(team_id: int, request: Request):
    params = dict(request.query_params)
    status, data = get_team_matches(team_id, params=params)
    return JSONResponse(status_code=status, content=data)


@app.get('/teams/{team_id}/history')
async def team_history(team_id: int, limit: int = 5):
    status, data = get_recent_history(team_id, limit=limit)
    return JSONResponse(status_code=status, content=data)


@app.get('/head2head')
async def head2head(team1: int, team2: int, limit: int = 10):
    status, data = get_head2head(team1, team2, limit=limit)
    return JSONResponse(status_code=status, content=data)


@app.get('/evaluate-match')
async def evaluate_match_endpoint(team1: int, team2: int, competition_id: int, draw_odds: float | None = None, under25_odds: float | None = None):
    res = evaluate_match(team1, team2, competition_id, draw_odds=draw_odds, under25_odds=under25_odds)
    return JSONResponse(status_code=200, content=res)


@app.on_event('startup')
async def _startup_scheduler():
    # Start background scheduler
    try:
        app_scheduler.start_scheduler()
    except Exception as e:
        print('Failed to start scheduler:', e)


@app.on_event('shutdown')
async def _shutdown_scheduler():
    try:
        app_scheduler.stop_scheduler()
    except Exception as e:
        print('Failed to stop scheduler:', e)
