from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from typing import Any

from .config import BASE_URL, LOGIN_URL, REGION_NAMES, institution, password, team_id


USER_AGENT = "Mozilla/5.0 (compatible; sc-game-tracker/1.0)"
SERIES_RE = re.compile(
    r"\{label:\s*'(?P<label>[^']*)',\s*name:\s*'(?P<name>[^']*)',\s*points:'(?P<points>[^']*)'\}"
)
MONEY_RE = re.compile(r"[-+]?\(?\$?[0-9,]+(?:\.[0-9]+)?\)?")


class GameClient:
    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )

    def _request(self, path: str, data: dict[str, str] | None = None) -> str:
        url = path if path.startswith("http") else f"{BASE_URL}/{path.lstrip('/')}"
        payload = None
        headers = {"User-Agent": USER_AGENT, "Referer": LOGIN_URL}
        if data is not None:
            payload = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=payload, headers=headers)
        with self._opener.open(req, timeout=45) as resp:
            return resp.read().decode("utf-8", "replace")

    def login(self) -> str:
        tid = team_id()
        pwd = password()
        if not tid or not pwd:
            raise RuntimeError("Missing SC_TEAM_ID or SC_PASSWORD in .env")
        return self._request(
            LOGIN_URL,
            {
                "id": tid,
                "password": pwd,
                "institution": institution(),
                "ismobile": "false",
            },
        )

    def get(self, path: str) -> str:
        return self._request(path)

    def post(self, path: str, data: dict[str, str] | None = None) -> str:
        return self._request(path, data or {})


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _parse_number(text: str) -> float | None:
    cleaned = _clean(text).replace(",", "").replace("$", "").replace(" ", "")
    cleaned = cleaned.replace("(", "-").replace(")", "").strip(".")
    if cleaned in {"", ".", "-"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_points(raw: str) -> list[tuple[float, float]]:
    if not raw.strip():
        return []
    nums = [float(tok) for tok in raw.split() if tok]
    pairs: list[tuple[float, float]] = []
    for i in range(0, len(nums) - 1, 2):
        pairs.append((nums[i], nums[i + 1]))
    return pairs


def parse_header(page: str) -> dict[str, Any]:
    name = re.search(r"Name:\s*<b>(.*?)</b>", page, re.I)
    cash = re.search(r"Cash:\s*<b>(.*?)</b>", page, re.I)
    day = re.search(r"Day:\s*<b>(.*?)</b>", page, re.I)
    factories = sorted(
        {int(x) for x in re.findall(r"SCFactory\?action=change&region=(\d+)", page)}
    )
    warehouses = sorted(
        {int(x) for x in re.findall(r"SCWarehouse\?submit=change&region=(\d+)", page)}
    )
    return {
        "team": _clean(name.group(1)) if name else team_id(),
        "cash": _parse_number(cash.group(1) if cash else ""),
        "day": int(float(_clean(day.group(1)))) if day else None,
        "factory_regions": factories or [1],
        "warehouse_regions": warehouses or [1],
    }


def parse_plot(page: str) -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    for match in SERIES_RE.finditer(page):
        label = match.group("label").strip() or match.group("name").strip() or "value"
        series[label] = _parse_points(match.group("points"))
    return series


def _plain_text(page: str) -> str:
    text = html.unescape(page).replace("\xa0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def parse_factory(page: str, region: int) -> dict[str, Any]:
    text = _plain_text(page)
    current = re.search(r"current capacity of\s+([0-9,]+(?:\.[0-9]+)?)", text, re.I)
    if not current:
        current = re.search(r"capacity of\s+([0-9,]+(?:\.[0-9]+)?)", text, re.I)
    scheduled = re.search(r"scheduled capacity is\s+([0-9,]+(?:\.[0-9]+)?)", text, re.I)
    ship = re.search(r"<option value=(\w+)\s+selected>", page)
    point = re.search(r'name=point\d+[^>]*value=([0-9,]+)', page)
    quant = re.search(r'name=quant\d+[^>]*value=([0-9,]+)', page)
    priority = re.search(r'name=priority\d+[^>]*value=([0-9,]+)', page)
    return {
        "region": region,
        "region_name": REGION_NAMES.get(region, str(region)),
        "current_capacity": _parse_number(current.group(1)) if current else None,
        "scheduled_capacity": _parse_number(scheduled.group(1)) if scheduled else None,
        "shipping": ship.group(1) if ship else None,
        "order_point": _parse_number(point.group(1)) if point else None,
        "order_quantity": _parse_number(quant.group(1)) if quant else None,
        "priority": _parse_number(priority.group(1)) if priority else None,
        "operational": "operational" in page.lower(),
    }


def parse_warehouse(page: str, region: int) -> dict[str, Any]:
    ship = re.search(r"<option value=(\w+)\s+selected>", page)
    point = re.search(r'name=point\d+[^>]*value=([0-9,]+)', page)
    quant = re.search(r'name=quant\d+[^>]*value=([0-9,]+)', page)
    priority = re.search(r'name=priority\d+[^>]*value=([0-9,]+)', page)
    return {
        "region": region,
        "region_name": REGION_NAMES.get(region, str(region)),
        "shipping": ship.group(1) if ship else None,
        "order_point": _parse_number(point.group(1)) if point else None,
        "order_quantity": _parse_number(quant.group(1)) if quant else None,
        "priority": _parse_number(priority.group(1)) if priority else None,
        "operational": "operational" in page.lower(),
    }


def parse_cash_status(page: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in re.finditer(r"<tr>(.*?)</tr>", page, re.I | re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", match.group(1), re.I | re.S)
        if len(cells) < 2:
            continue
        desc = _clean(re.sub(r"<[^>]+>", "", cells[0]))
        amount_raw = _clean(re.sub(r"<[^>]+>", "", cells[1]))
        if desc.lower() in {"description", ""}:
            continue
        amount = _parse_number(amount_raw)
        kind = "total"
        if "source" in desc.lower():
            kind = "section"
        elif "use" in desc.lower():
            kind = "section"
        elif desc.lower().startswith("starting"):
            kind = "start"
        elif "balance" in desc.lower():
            kind = "balance"
        elif amount is not None and amount < 0:
            kind = "use"
        elif amount is not None:
            kind = "source"
        rows.append({"description": desc, "amount": amount, "kind": kind})
    return rows


def parse_standing(page: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in re.finditer(r"<tr>(.*?)</tr>", page, re.I | re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", match.group(1), re.I | re.S)
        if len(cells) < 3:
            continue
        values = [_clean(re.sub(r"<[^>]+>", "", c)) for c in cells[:3]]
        rank = _parse_number(values[0])
        if rank is None:
            continue
        rows.append(
            {
                "rank": int(rank),
                "team": values[1],
                "cash": _parse_number(values[2]),
            }
        )
    return rows


def parse_history(page: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    body = re.search(r"<tbody>(.*?)</tbody>", page, re.I | re.S)
    chunk = body.group(1) if body else page
    for match in re.finditer(r"<tr>(.*?)</tr>", chunk, re.I | re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", match.group(1), re.I | re.S)
        if len(cells) < 6:
            continue
        values = [_clean(re.sub(r"<[^>]+>", "", c)) for c in cells[:6]]
        rows.append(
            {
                "day": _parse_number(values[0]),
                "parameter": values[1],
                "parameter_short": values[2],
                "factory": values[3],
                "warehouse": values[4],
                "new_value": _parse_number(values[5]) if _parse_number(values[5]) is not None else values[5],
            }
        )
    return rows


def fetch_all() -> dict[str, Any]:
    client = GameClient()
    home = client.login()
    if "Cash:" not in home or "Day:" not in home:
        raise RuntimeError("Login failed. Check team id / password.")

    header = parse_header(home)
    day = header["day"] or 0
    plots: dict[str, dict[str, list[tuple[float, float]]]] = {
        "demand": parse_plot(client.get("SCPlotk?submit=plot+demand&data=DEMAND1")),
        "lost_demand": parse_plot(client.get("SCPlotk?submit=plot+lost+demand&data=LOST1")),
        "cash_balance": parse_plot(client.get("SCPlotk?submit=plot+cash+balance&data=BALANCE")),
    }

    factories = []
    for region in header["factory_regions"]:
        factories.append(parse_factory(client.get(f"SCFactory?action=change&region={region}"), region))
        plots[f"wip_{region}"] = parse_plot(client.get(f"SCPlotk?submit=plot+wip&data=WIP{region}"))

    warehouses = []
    for region in header["warehouse_regions"]:
        warehouses.append(parse_warehouse(client.get(f"SCWarehouse?submit=change&region={region}"), region))
        plots[f"inventory_{region}"] = parse_plot(
            client.get(f"SCPlotk?submit=plot+inventory&data=WH{region}")
        )
        plots[f"shipments_{region}"] = parse_plot(
            client.get(f"SCPlotk?submit=plot+shipments&data=SHIP{region}SEG1")
        )

    return {
        "header": header,
        "day": day,
        "factories": factories,
        "warehouses": warehouses,
        "plots": plots,
        "cash_status": parse_cash_status(client.post("SCCashStatus")),
        "standing": parse_standing(client.post("SCStanding")),
        "history": parse_history(client.post("SCHistory")),
    }
