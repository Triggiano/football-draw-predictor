"""Run the scheduler in the foreground (useful when not running FastAPI).

Usage: python run_scheduler.py
"""
from app.scheduler import start_scheduler
import time


if __name__ == '__main__':
    sched = start_scheduler()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        sched.shutdown()
