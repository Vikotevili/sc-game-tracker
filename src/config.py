from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
EXCEL_PATH = DATA_DIR / "supply_chain_game.xlsx"
STATE_PATH = DATA_DIR / "state.json"
ENV_PATH = ROOT / ".env"

REGION_NAMES = {
    1: "Calopeia",
    2: "Sorange",
    3: "Tyran",
    4: "Entworpe",
    5: "Fardo",
}

BASE_URL = "https://op.responsive.net/SupplyChain"
LOGIN_URL = f"{BASE_URL}/SCAccess"
GAME_END_DAY = 1460
MANAGEMENT_START_DAY = 730
REVENUE_PER_DRUM = 1450.0
SECONDS_PER_GAME_DAY = 14 * 60


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or ENV_PATH
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env = load_dotenv


def getenv(*names: str, default: str = "") -> str:
    load_dotenv()
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip():
            return value.strip()
    return default


def team_id() -> str:
    return getenv("SC_TEAM_ID", "GAME_TEAM_ID")


def password() -> str:
    return getenv("SC_PASSWORD", "GAME_PASSWORD")


def institution() -> str:
    return getenv("SC_INSTITUTION", "GAME_INSTITUTION", default="nanyang")


def period_days() -> int:
    return max(1, int(getenv("SC_PERIOD_DAYS", "PERIOD_DAYS", default="3") or "3"))


def poll_seconds() -> int:
    return max(60, int(getenv("SC_POLL_SECONDS", default="900") or "900"))


def git_push_enabled() -> bool:
    return getenv("GIT_PUSH", default="0") not in {"0", "false", "False", "no", ""}


def git_remote() -> str:
    return getenv("GIT_REMOTE", default="origin")


def git_branch() -> str:
    return getenv("GIT_BRANCH", default="main")


def settings() -> dict[str, str | int | bool]:
    load_dotenv()
    return {
        "base_url": getenv("GAME_BASE_URL", default=BASE_URL),
        "institution": institution(),
        "team_id": team_id(),
        "password": password(),
        "period_days": period_days(),
        "git_push": git_push_enabled(),
        "git_remote": git_remote(),
        "git_branch": git_branch(),
    }
