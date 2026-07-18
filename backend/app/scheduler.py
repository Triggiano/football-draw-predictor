from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, timedelta
import traceback

# Import job functions from scripts. These scripts expose callable functions.
try:
    from scripts.fetch_fixtures import fetch_and_store
except Exception:
    fetch_and_store = None

try:
    from scripts.fetch_odds import run_for_range as fetch_odds_run
except Exception:
    fetch_odds_run = None

try:
    from scripts.fetch_team_form import run as fetch_team_form_run
except Exception:
    fetch_team_form_run = None

try:
    from scripts.populate_synthetic_odds import run as populate_synthetic_run
except Exception:
    populate_synthetic_run = None


scheduler: BackgroundScheduler | None = None


def _job_fetch_fixtures():
    try:
        if not fetch_and_store:
            print('fetch_and_store not available')
            return
        today = date.today()
        df = (today - timedelta(days=3)).isoformat()
        dt = (today + timedelta(days=3)).isoformat()
        print('Scheduler: fetching fixtures', df, '->', dt)
        fetch_and_store(df, dt)
    except Exception:
        traceback.print_exc()


def _job_fetch_odds():
    try:
        print('Scheduler: fetching odds')
        if fetch_odds_run:
            fetch_odds_run()
        elif populate_synthetic_run:
            # fallback to synthetic odds for environments without provider
            populate_synthetic_run()
        else:
            print('No odds job available')
    except Exception:
        traceback.print_exc()


def _job_team_form():
    try:
        print('Scheduler: computing team form')
        if fetch_team_form_run:
            fetch_team_form_run()
        else:
            print('team form job not available')
    except Exception:
        traceback.print_exc()


def start_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        return scheduler
    scheduler = BackgroundScheduler()

    # Every morning (06:00) refresh 7-day window
    scheduler.add_job(_job_fetch_fixtures, 'cron', hour=6, minute=0, id='fetch_fixtures')

    # Every few hours refresh odds (every 4 hours)
    scheduler.add_job(_job_fetch_odds, 'interval', hours=4, id='fetch_odds')

    # Daily compute team form after fixtures (07:00)
    scheduler.add_job(_job_team_form, 'cron', hour=7, minute=0, id='team_form')

    scheduler.start()
    print('Scheduler started with jobs:', [j.id for j in scheduler.get_jobs()])
    return scheduler


def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        print('Scheduler shut down')
        scheduler = None
