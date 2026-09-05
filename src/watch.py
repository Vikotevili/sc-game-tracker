from __future__ import annotations

import time
from datetime import datetime

from .config import poll_seconds
from .sync import run


def main() -> None:
    interval = poll_seconds()
    print(f"Watching Supply Chain Game every {interval} seconds. Ctrl+C to stop.")
    while True:
        started = datetime.now().isoformat(timespec="seconds")
        try:
            result = run()
            print(f"[{started}] day={result['day']} cash={result['cash']} rank={result['rank']} git={result['git']}")
        except Exception as exc:
            print(f"[{started}] ERROR: {exc}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
