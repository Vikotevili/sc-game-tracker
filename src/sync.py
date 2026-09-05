from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from .config import EXCEL_PATH, SNAPSHOT_DIR, STATE_PATH, git_push_enabled, period_days
from .excel_report import write_excel
from .gitutil import commit_and_push
from .scrape import fetch_all
from .transform import build_report


def _save_json(report: dict) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slim = {
        "fetched_at": report["fetched_at"],
        "day": report["day"],
        "header": report["header"],
        "rank": report["rank"],
        "factory": report["factory"],
        "warehouse": report["warehouse"],
        "stock": report["stock"],
        "current_period": report["current_period"],
        "last_complete_period": report["last_complete_period"],
    }
    (SNAPSHOT_DIR / f"snapshot_{stamp}.json").write_text(
        json.dumps(slim, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    STATE_PATH.write_text(
        json.dumps(
            {
                "fetched_at": report["fetched_at"],
                "day": report["day"],
                "period": (report["current_period"] or {}).get("period"),
                "cash": report["header"].get("cash"),
                "rank": report["rank"].get("rank"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def run(push: bool | None = None) -> dict:
    raw = fetch_all()
    report = build_report(raw)
    excel_path = write_excel(report)
    _save_json(report)
    git_result = commit_and_push(
        [excel_path, STATE_PATH],
        (
            f"Update game data: day {report['day']}, "
            f"cash {report['header'].get('cash')}, "
            f"{period_days()}-day period {(report['current_period'] or {}).get('period')}"
        ),
        git_push_enabled() if push is None else push,
    )
    return {
        "day": report["day"],
        "cash": report["header"].get("cash"),
        "rank": report["rank"].get("rank"),
        "excel": str(excel_path),
        "git": git_result,
        "period": report["current_period"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Supply Chain Game and write Excel")
    parser.add_argument("--no-push", action="store_true", help="Write Excel only, do not git push")
    args = parser.parse_args()
    result = run(push=False if args.no_push else None)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
