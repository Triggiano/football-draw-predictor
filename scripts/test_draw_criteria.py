"""Simple script to test draw scoring engine.

Usage:
    python scripts/test_draw_criteria.py --home 66 --away 64 --competition 2021
"""
import argparse
import json
from app.services.scoring import score_match, select_day_outputs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--home", type=int, required=True)
    p.add_argument("--away", type=int, required=True)
    p.add_argument("--competition", type=int, required=True)
    args = p.parse_args()

    scored = score_match(args.home, args.away, args.competition)
    print(json.dumps(scored, indent=2))


if __name__ == "__main__":
    main()
