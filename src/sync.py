from __future__ import annotations

import argparse
import json
import traceback
from datetime import datetime, timezone

from .config import DATA_DIR, EXCEL_PATH, SNAPSHOT_DIR, STATE_PATH, git_push_enabled, period_days
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
        "advice": {
            "conclusion": (report.get("advice") or {}).get("conclusion"),
            "urgency": (report.get("advice") or {}).get("urgency"),
            "action": (report.get("advice") or {}).get("action"),
        },
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
        "advice": report.get("advice"),
    }


def _log(line: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with (DATA_DIR / "sync.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {line}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Supply Chain Game and write Excel")
    parser.add_argument("--no-push", action="store_true", help="Write Excel only, do not git push")
    args = parser.parse_args()
    try:
        result = run(push=False if args.no_push else None)
        _log(f"ok day={result['day']} cash={result['cash']} rank={result['rank']} git={result['git']}")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except Exception as exc:
        _log(f"ERROR {exc}\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
