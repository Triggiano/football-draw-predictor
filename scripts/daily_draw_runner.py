"""Daily runner: load fixtures, score matches, and select top daily outputs.

Expects `fixtures_out.json` to be a JSON list of matches, each with at least:
  {"home": <id>, "away": <id>, "competition": <id>, "draw_odds": <opt>, "under25_odds": <opt>}

"""
import json
from pathlib import Path
from app.services.scoring import score_match, select_day_outputs


def load_fixtures(path: Path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def main():
    fixtures = load_fixtures(Path("fixtures_out.json"))
    scored = []
    for f in fixtures:
        home = f.get("home") or f.get("home_id")
        away = f.get("away") or f.get("away_id")
        comp = f.get("competition") or f.get("competition_id")
        if not home or not away or not comp:
            continue
        s = score_match(home, away, comp, draw_odds=f.get("draw_odds"), under25_odds=f.get("under25_odds"))
        entry = {"home": home, "away": away, "competition": comp, "score": s.get("score"), "passes": s.get("passes"), "reasons": s.get("reasons")}
        scored.append(entry)

    selection = select_day_outputs(scored)
    out = {"selected": selection["selected"], "low_confidence": selection["low_confidence"], "count": selection["count"]}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
