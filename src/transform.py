from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .config import (
    GAME_END_DAY,
    MANAGEMENT_START_DAY,
    REGION_NAMES,
    REVENUE_PER_DRUM,
    period_days,
)


def _end_of_day(pairs: list[tuple[float, float]], last_day: int) -> dict[int, float]:
    result: dict[int, float] = {}
    i = 0
    last_v: float | None = None
    ordered = sorted(pairs, key=lambda item: item[0])
    for day in range(1, last_day + 1):
        while i < len(ordered) and ordered[i][0] <= day + 1e-9:
            last_v = ordered[i][1]
            i += 1
        if last_v is not None:
            result[day] = last_v
    return result


def _first_series(plot: dict[str, list[tuple[float, float]]]) -> list[tuple[float, float]]:
    if not plot:
        return []
    for key in plot:
        if plot[key]:
            return plot[key]
    return next(iter(plot.values()), [])


def _cash_scale(cash_pairs: list[tuple[float, float]], header_cash: float | None) -> float:
    if not cash_pairs or not header_cash:
        return 1.0
    last_value = cash_pairs[-1][1]
    if last_value == 0:
        return 1.0
    scale = header_cash / last_value
    if 50 <= scale <= 2000:
        return scale
    return 1.0


def build_daily_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    day = int(raw["day"] or 0)
    plots = raw["plots"]
    demand = _end_of_day(_first_series(plots.get("demand", {})), day)
    lost = _end_of_day(_first_series(plots.get("lost_demand", {})), day)
    cash_pairs = _first_series(plots.get("cash_balance", {}))
    scale = _cash_scale(cash_pairs, raw["header"].get("cash"))
    cash = {d: v * scale for d, v in _end_of_day(cash_pairs, day).items()}

    inventory: dict[int, float] = defaultdict(float)
    mail: dict[int, float] = defaultdict(float)
    truck: dict[int, float] = defaultdict(float)
    wip: dict[int, float] = defaultdict(float)
    shipments: dict[int, float] = defaultdict(float)

    for region in raw["header"].get("warehouse_regions", [1]):
        inv_plot = plots.get(f"inventory_{region}", {})
        for key, series in inv_plot.items():
            sampled = _end_of_day(series, day)
            lowered = key.lower()
            if lowered == "mail":
                target = mail
            elif lowered == "truck":
                target = truck
            else:
                target = inventory
            for d, value in sampled.items():
                target[d] += value
        for d, value in _end_of_day(_first_series(plots.get(f"shipments_{region}", {})), day).items():
            shipments[d] += value

    for region in raw["header"].get("factory_regions", [1]):
        for d, value in _end_of_day(_first_series(plots.get(f"wip_{region}", {})), day).items():
            wip[d] += value

    rows = []
    for d in range(1, day + 1):
        demand_qty = demand.get(d, 0.0)
        lost_qty = lost.get(d, 0.0)
        filled = max(0.0, demand_qty - lost_qty)
        service = (filled / demand_qty) if demand_qty else None
        pipeline = mail.get(d, 0.0) + truck.get(d, 0.0)
        rows.append(
            {
                "day": d,
                "after_takeover": d >= MANAGEMENT_START_DAY,
                "demand": demand_qty,
                "lost_demand": lost_qty,
                "filled": filled,
                "service_level": service,
                "shipments": shipments.get(d, 0.0),
                "cash": cash.get(d),
                "inventory": inventory.get(d, 0.0),
                "pipeline_mail": mail.get(d, 0.0),
                "pipeline_truck": truck.get(d, 0.0),
                "pipeline": pipeline,
                "wip": wip.get(d, 0.0),
                "est_revenue": filled * REVENUE_PER_DRUM,
            }
        )
    return rows


def build_period_rows(daily: list[dict[str, Any]], size: int | None = None) -> list[dict[str, Any]]:
    size = size or period_days()
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in daily:
        period_id = (row["day"] - 1) // size + 1
        grouped[period_id].append(row)

    periods = []
    for period_id in sorted(grouped):
        chunk = grouped[period_id]
        start_day = (period_id - 1) * size + 1
        end_day = period_id * size
        demand_sum = sum(r["demand"] for r in chunk)
        lost_sum = sum(r["lost_demand"] for r in chunk)
        filled = sum(r["filled"] for r in chunk)
        shipments = sum(r["shipments"] for r in chunk)
        cash_values = [r["cash"] for r in chunk if r["cash"] is not None]
        inv_values = [r["inventory"] for r in chunk]
        wip_values = [r["wip"] for r in chunk]
        periods.append(
            {
                "period": period_id,
                "start_day": start_day,
                "end_day": end_day,
                "days_in_period": len(chunk),
                "complete": len(chunk) == size,
                "after_takeover": end_day >= MANAGEMENT_START_DAY,
                "demand": demand_sum,
                "lost_demand": lost_sum,
                "filled": filled,
                "service_level": (filled / demand_sum) if demand_sum else None,
                "shipments": shipments,
                "cash_start": cash_values[0] if cash_values else None,
                "cash_end": cash_values[-1] if cash_values else None,
                "cash_change": (
                    cash_values[-1] - cash_values[0] if len(cash_values) >= 2 else None
                ),
                "inventory_end": inv_values[-1] if inv_values else None,
                "inventory_avg": (sum(inv_values) / len(inv_values)) if inv_values else None,
                "pipeline_end": chunk[-1]["pipeline"] if chunk else None,
                "wip_end": wip_values[-1] if wip_values else None,
                "wip_avg": (sum(wip_values) / len(wip_values)) if wip_values else None,
                "est_revenue": filled * REVENUE_PER_DRUM,
            }
        )
    return periods


def team_rank(raw: dict[str, Any]) -> dict[str, Any]:
    team = raw["header"].get("team")
    standing = raw.get("standing") or []
    mine = next((row for row in standing if row["team"] == team), None)
    leader = standing[0] if standing else None
    gap = None
    if mine and leader and mine["cash"] is not None and leader["cash"] is not None:
        gap = leader["cash"] - mine["cash"]
    return {
        "rank": mine["rank"] if mine else None,
        "teams": len(standing),
        "leader_team": leader["team"] if leader else None,
        "leader_cash": leader["cash"] if leader else None,
        "gap_to_leader": gap,
    }


def latest_inventory(daily: list[dict[str, Any]]) -> dict[str, float]:
    if not daily:
        return {"inventory": 0.0, "pipeline": 0.0, "wip": 0.0}
    last = daily[-1]
    return {
        "inventory": last["inventory"],
        "pipeline": last["pipeline"],
        "wip": last["wip"],
    }


def build_report(raw: dict[str, Any]) -> dict[str, Any]:
    daily = build_daily_rows(raw)
    periods = build_period_rows(daily)
    complete_periods = [p for p in periods if p["complete"]]
    current_period = periods[-1] if periods else None
    last_complete = complete_periods[-1] if complete_periods else None
    rank = team_rank(raw)
    stock = latest_inventory(daily)
    factory = raw["factories"][0] if raw.get("factories") else {}
    warehouse = raw["warehouses"][0] if raw.get("warehouses") else {}
    now = datetime.now(timezone.utc).astimezone()
    day = int(raw["day"] or 0)
    return {
        "fetched_at": now.isoformat(timespec="seconds"),
        "header": raw["header"],
        "day": day,
        "days_left": max(0, GAME_END_DAY - day),
        "period_days": period_days(),
        "rank": rank,
        "factory": factory,
        "warehouse": warehouse,
        "stock": stock,
        "current_period": current_period,
        "last_complete_period": last_complete,
        "daily": daily,
        "periods": periods,
        "cash_status": raw.get("cash_status") or [],
        "standing": raw.get("standing") or [],
        "history": raw.get("history") or [],
        "regions": {
            "factories": [REGION_NAMES.get(r, str(r)) for r in raw["header"].get("factory_regions", [])],
            "warehouses": [REGION_NAMES.get(r, str(r)) for r in raw["header"].get("warehouse_regions", [])],
        },
    }
