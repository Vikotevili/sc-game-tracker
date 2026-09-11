from __future__ import annotations

import statistics
from datetime import datetime, timedelta
from typing import Any

from .config import GAME_END_DAY, SECONDS_PER_GAME_DAY


MINUTES_PER_GAME_DAY = SECONDS_PER_GAME_DAY / 60
WIND_DOWN_DAY = 1375
MID_CUT_DAY = 1390
ENDGAME_Q_DAY = 1420
STOP_DAY = 1429


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _remaining_forecast(daily: list[dict[str, Any]], day: int) -> dict[str, Any]:
    demand = {row["day"]: float(row["demand"] or 0) for row in daily}
    points: list[float] = []
    for future in range(day + 1, GAME_END_DAY + 1):
        sample = [demand[prev] for prev in (future - 365, future - 730) if prev in demand]
        if sample:
            points.append(statistics.mean(sample))
    return {
        "days": len(points),
        "total": sum(points) if points else None,
        "avg": _mean(points),
        "source": "前两年同一日历日均值（预测，不是实测）",
    }


def _recent(daily: list[dict[str, Any]], n: int = 7) -> dict[str, Any]:
    chunk = daily[-n:] if daily else []
    demands = [float(row["demand"] or 0) for row in chunk]
    lost = [float(row["lost_demand"] or 0) for row in chunk]
    return {
        "days": len(chunk),
        "demand_avg": _mean(demands),
        "lost_sum": sum(lost) if lost else 0.0,
        "demand_max": max(demands) if demands else None,
    }


def _eta(days_ahead: float) -> str:
    when = datetime.now().astimezone() + timedelta(minutes=days_ahead * MINUTES_PER_GAME_DAY)
    return when.strftime("%Y-%m-%d %H:%M")


def build_advice(report: dict[str, Any]) -> dict[str, Any]:
    day = int(report.get("day") or 0)
    factory = report.get("factory") or {}
    stock = report.get("stock") or {}
    daily = report.get("daily") or []
    last = daily[-1] if daily else {}

    ship = factory.get("shipping")
    rop = factory.get("order_point")
    qty = factory.get("order_quantity")
    cap = factory.get("current_capacity")
    scheduled = factory.get("scheduled_capacity")
    warehouse = float(stock.get("inventory") or 0)
    pipeline = float(stock.get("pipeline") or 0)
    wip = float(stock.get("wip") or 0)
    position = warehouse + pipeline + wip
    days_left = max(0, GAME_END_DAY - day)
    today_demand = float(last.get("demand") or 0)
    today_lost = float(last.get("lost_demand") or 0)

    recent = _recent(daily, 7)
    forecast = _remaining_forecast(daily, day)
    remaining = forecast["total"]
    recent_avg = recent["demand_avg"] or 0.0
    tight = warehouse < max(80.0, 2.0 * recent_avg) and recent_avg >= 35
    if today_lost > 0 or warehouse <= 0:
        tight = True

    target_ship = "truck"
    target_qty = 200.0
    target_cap = cap
    if day >= ENDGAME_Q_DAY and remaining is not None and remaining < 350:
        target_qty = 100.0
        target_ship = "mail"

    if day >= STOP_DAY:
        target_rop = 0.0
    elif remaining is not None and remaining <= position + 50 and not tight:
        target_rop = 0.0
    elif day >= 1410:
        target_rop = 400.0 if not tight else 800.0
    elif day >= MID_CUT_DAY:
        target_rop = 400.0 if not tight else 800.0
    elif day >= WIND_DOWN_DAY:
        target_rop = 800.0 if not tight else 1400.0
    else:
        target_rop = 1400.0
        if remaining is not None and remaining + 100 < position and not tight:
            target_rop = 800.0

    if days_left < 90:
        cap_note = "剩余不足90天，不要再加产能"
    else:
        cap_note = "不要再加产能"
    if scheduled is not None and cap is not None and float(scheduled) > float(cap):
        cap_note += f"；已有计划产能 {scheduled}，不要再加"

    changes: list[str] = []
    if ship and target_ship and ship != target_ship:
        changes.append(f"运输 {ship} → {target_ship}")
    if rop is not None and abs(float(rop) - target_rop) >= 50:
        changes.append(f"订货点 {int(float(rop))} → {int(target_rop)}")
    if qty is not None and abs(float(qty) - target_qty) >= 50:
        changes.append(f"批量 {int(float(qty))} → {int(target_qty)}")

    need_change = bool(changes)
    if day >= STOP_DAY and (rop is None or float(rop) > 0):
        urgency = "立即"
    elif day >= WIND_DOWN_DAY and need_change and not tight:
        urgency = "立即"
    elif need_change:
        urgency = "本小时内"
    else:
        urgency = "暂不改"

    if need_change:
        action = "请改：" + "；".join(changes) + "。改完点 ok。未列出的项不要动。"
        conclusion = "需要改参数"
    else:
        action = (
            f"现在不用改。保持 运输 {ship or '—'} / 订货点 "
            f"{int(float(rop)) if rop is not None else '—'} / 批量 "
            f"{int(float(qty)) if qty is not None else '—'} / 产能 "
            f"{int(float(cap)) if cap is not None else '—'}。"
        )
        conclusion = "暂不改"

    if day < WIND_DOWN_DAY:
        next_day, next_note = WIND_DOWN_DAY, "开始评估下调订货点（先看仓库是否仍紧）"
    elif day < MID_CUT_DAY:
        next_day, next_note = MID_CUT_DAY, "再降一档订货点"
    elif day < ENDGAME_Q_DAY:
        next_day, next_note = ENDGAME_Q_DAY, "收尾：评估批量是否改100"
    elif day < STOP_DAY:
        next_day, next_note = STOP_DAY, "订货点改0停产"
    else:
        next_day, next_note = GAME_END_DAY, "游戏结束"

    measured = (
        f"实测：第{day}天 仓库{warehouse:.0f} 在途{pipeline:.0f} 在制{wip:.0f} "
        f"位置{position:.0f}；今天需求{today_demand:.0f} 缺货{today_lost:.0f}；"
        f"近{recent['days']}日均需求"
        f"{recent_avg:.1f} 缺货合计{recent['lost_sum']:.0f}。"
    )
    forecast_text = (
        f"预测：剩余需求约{remaining:.0f}桶（{forecast['source']}）。"
        if remaining is not None
        else "预测：剩余需求样本不足。"
    )
    next_text = (
        f"第{next_day}天（约{_eta(max(0, next_day - day))}）{next_note}。"
        f"按1游戏日≈{MINUTES_PER_GAME_DAY:.0f}分钟换算，误差约±30分钟。"
    )

    return {
        "conclusion": conclusion,
        "need_change": need_change,
        "urgency": urgency,
        "current_shipping": ship,
        "target_shipping": target_ship,
        "current_rop": rop,
        "target_rop": target_rop,
        "current_quantity": qty,
        "target_quantity": target_qty,
        "current_capacity": cap,
        "target_capacity": target_cap,
        "capacity_note": cap_note,
        "changes": changes,
        "action": action,
        "measured": measured,
        "forecast": forecast_text,
        "next_check": next_text,
        "tight": tight,
        "position": position,
        "remaining_forecast": remaining,
    }
