from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .config import EXCEL_PATH, GAME_END_DAY, MANAGEMENT_START_DAY


HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True, name="Calibri", size=11)
TITLE_FONT = Font(bold=True, name="Calibri", size=16, color="1F4E79")
LABEL_FONT = Font(bold=True, name="Calibri", size=11)
GOOD_FILL = PatternFill("solid", fgColor="C6EFCE")
WARN_FILL = PatternFill("solid", fgColor="FFEB9C")
BAD_FILL = PatternFill("solid", fgColor="FFC7CE")
ALT_FILL = PatternFill("solid", fgColor="D6EAF8")
THIN = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)


def _style_header(ws: Worksheet, row: int, cols: int) -> None:
    for col in range(1, cols + 1):
        cell = ws.cell(row, col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN


def _autosize(ws: Worksheet, min_width: int = 10, max_width: int = 36) -> None:
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        width = min_width
        for cell in col:
            value = "" if cell.value is None else str(cell.value)
            width = max(width, min(max_width, len(value) + 2))
        ws.column_dimensions[letter].width = width


def _write_kv(ws: Worksheet, row: int, label: str, value: Any, num_format: str | None = None) -> int:
    ws.cell(row, 1, label).font = LABEL_FONT
    cell = ws.cell(row, 2, value)
    if num_format and isinstance(value, (int, float)):
        cell.number_format = num_format
    return row + 1


def _service_fill(value: float | None) -> PatternFill | None:
    if value is None:
        return None
    if value >= 0.95:
        return GOOD_FILL
    if value >= 0.80:
        return WARN_FILL
    return BAD_FILL


def _write_table(ws: Worksheet, start_row: int, headers: list[str], rows: list[list[Any]], formats: list[str | None]) -> None:
    for idx, header in enumerate(headers, start=1):
        ws.cell(start_row, idx, header)
    _style_header(ws, start_row, len(headers))
    for r_idx, row in enumerate(rows, start=start_row + 1):
        for c_idx, value in enumerate(row, start=1):
            cell = ws.cell(r_idx, c_idx, value)
            cell.border = THIN
            cell.alignment = Alignment(vertical="center")
            fmt = formats[c_idx - 1] if c_idx - 1 < len(formats) else None
            if fmt and isinstance(value, (int, float)):
                cell.number_format = fmt
            if headers[c_idx - 1].endswith("服务水平") and isinstance(value, float):
                fill = _service_fill(value)
                if fill:
                    cell.fill = fill
            elif r_idx % 2 == 0:
                cell.fill = ALT_FILL
    ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(headers))}{start_row + len(rows)}"
    ws.freeze_panes = f"A{start_row + 1}"
    ws.row_dimensions[start_row].height = 22


def write_excel(report: dict[str, Any], path: Path = EXCEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    ws = wb.active
    ws.title = "概览"
    header = report["header"]
    rank = report["rank"]
    factory = report["factory"]
    warehouse = report["warehouse"]
    stock = report["stock"]
    current = report["current_period"] or {}
    last_complete = report["last_complete_period"] or {}

    ws["A1"] = "Supply Chain Game 运营看板"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:D1")
    ws["A2"] = "按游戏日每 3 天一个周期汇总；图表数据来自游戏官方 plot / standing / cash / history 页面。"
    ws.merge_cells("A2:D2")

    row = 4
    row = _write_kv(ws, row, "抓取时间", report["fetched_at"])
    row = _write_kv(ws, row, "团队", header.get("team"))
    row = _write_kv(ws, row, "当前游戏日", report["day"], "#,##0")
    row = _write_kv(ws, row, "剩余游戏日", report["days_left"], "#,##0")
    row = _write_kv(ws, row, "游戏结束日", GAME_END_DAY, "#,##0")
    row = _write_kv(ws, row, "接管起始日", MANAGEMENT_START_DAY, "#,##0")
    row = _write_kv(ws, row, "当前现金", header.get("cash"), '"$"#,##0.00')
    row = _write_kv(ws, row, "当前排名", rank.get("rank"), "0")
    row = _write_kv(ws, row, "参赛队伍数", rank.get("teams"), "0")
    row = _write_kv(ws, row, "领先队伍", rank.get("leader_team"))
    row = _write_kv(ws, row, "距第一名差额", rank.get("gap_to_leader"), '"$"#,##0.00')

    row += 1
    ws.cell(row, 1, "工厂 / 仓库参数").font = TITLE_FONT
    row += 1
    row = _write_kv(ws, row, "工厂地区", factory.get("region_name"))
    row = _write_kv(ws, row, "当前产能 (鼓/日)", factory.get("current_capacity"), "0.00")
    row = _write_kv(ws, row, "计划产能 (鼓/日)", factory.get("scheduled_capacity"), "0.00")
    row = _write_kv(ws, row, "工厂运输方式", factory.get("shipping"))
    row = _write_kv(ws, row, "订货点 ROP", factory.get("order_point"), "#,##0")
    row = _write_kv(ws, row, "订货批量 Q", factory.get("order_quantity"), "#,##0")
    row = _write_kv(ws, row, "仓库运输方式", warehouse.get("shipping"))
    row = _write_kv(ws, row, "期末仓库库存", stock.get("inventory"), "#,##0.00")
    row = _write_kv(ws, row, "期末在途库存", stock.get("pipeline"), "#,##0.00")
    row = _write_kv(ws, row, "期末在制品 WIP", stock.get("wip"), "#,##0.00")

    row += 1
    ws.cell(row, 1, "当前 3 日周期").font = TITLE_FONT
    row += 1
    row = _write_kv(ws, row, "周期编号", current.get("period"))
    row = _write_kv(ws, row, "覆盖游戏日", f"{current.get('start_day')}–{current.get('end_day')}" if current else None)
    row = _write_kv(ws, row, "是否完整周期", "是" if current.get("complete") else "否（进行中）")
    row = _write_kv(ws, row, "周期需求", current.get("demand"), "#,##0.00")
    row = _write_kv(ws, row, "周期缺货", current.get("lost_demand"), "#,##0.00")
    row = _write_kv(ws, row, "周期交付", current.get("filled"), "#,##0.00")
    row = _write_kv(ws, row, "周期服务水平", current.get("service_level"), "0.0%")
    row = _write_kv(ws, row, "周期出货", current.get("shipments"), "#,##0.00")
    row = _write_kv(ws, row, "周期现金变动", current.get("cash_change"), '"$"#,##0.00')

    row += 1
    ws.cell(row, 1, "上一完整 3 日周期").font = TITLE_FONT
    row += 1
    row = _write_kv(ws, row, "周期编号", last_complete.get("period"))
    row = _write_kv(ws, row, "覆盖游戏日", f"{last_complete.get('start_day')}–{last_complete.get('end_day')}" if last_complete else None)
    row = _write_kv(ws, row, "需求 / 缺货 / 交付", last_complete and f"{last_complete.get('demand')} / {last_complete.get('lost_demand')} / {last_complete.get('filled')}")
    row = _write_kv(ws, row, "服务水平", last_complete.get("service_level"), "0.0%")
    row = _write_kv(ws, row, "现金变动", last_complete.get("cash_change"), '"$"#,##0.00')

    row += 2
    ws.cell(row, 1, "说明").font = LABEL_FONT
    ws.cell(row + 1, 1, "游戏速度约 1 游戏日 / 14 分钟，3 个游戏日约 42 分钟。脚本每 15 分钟刷新一次，并把完整历史重写成 Excel。")
    ws.merge_cells(start_row=row + 1, start_column=1, end_row=row + 1, end_column=4)
    ws.cell(row + 2, 1, "「三日周期」按游戏日 1–3、4–6 … 切片。Day 730 起为你们接管后的区间。现金序列已按当前现金校准。")
    ws.merge_cells(start_row=row + 2, start_column=1, end_row=row + 2, end_column=4)
    _autosize(ws, 16, 42)
    ws.column_dimensions["B"].width = 28

    ws_p = wb.create_sheet("三日周期")
    period_headers = [
        "周期", "起始日", "结束日", "天数", "是否完整", "接管后",
        "需求", "缺货", "交付", "服务水平", "出货",
        "期初现金", "期末现金", "现金变动",
        "期末仓库库存", "平均仓库库存", "期末在途", "期末WIP", "估算收入",
    ]
    period_rows = []
    for item in report["periods"]:
        period_rows.append([
            item["period"],
            item["start_day"],
            item["end_day"],
            item["days_in_period"],
            "是" if item["complete"] else "否",
            "是" if item["after_takeover"] else "否",
            item["demand"],
            item["lost_demand"],
            item["filled"],
            item["service_level"],
            item["shipments"],
            item["cash_start"],
            item["cash_end"],
            item["cash_change"],
            item["inventory_end"],
            item["inventory_avg"],
            item["pipeline_end"],
            item["wip_end"],
            item["est_revenue"],
        ])
    _write_table(
        ws_p,
        1,
        period_headers,
        period_rows,
        [
            "0", "0", "0", "0", None, None,
            "#,##0.00", "#,##0.00", "#,##0.00", "0.0%", "#,##0.00",
            '"$"#,##0.00', '"$"#,##0.00', '"$"#,##0.00',
            "#,##0.00", "#,##0.00", "#,##0.00", "#,##0.00", '"$"#,##0.00',
        ],
    )
    _autosize(ws_p, 10, 16)

    ws_d = wb.create_sheet("每日数据")
    daily_headers = [
        "游戏日", "接管后", "需求", "缺货", "交付", "服务水平", "出货",
        "现金", "仓库库存", "在途邮件", "在途卡车", "在途合计", "WIP", "估算收入",
    ]
    daily_rows = []
    for item in report["daily"]:
        daily_rows.append([
            item["day"],
            "是" if item["after_takeover"] else "否",
            item["demand"],
            item["lost_demand"],
            item["filled"],
            item["service_level"],
            item["shipments"],
            item["cash"],
            item["inventory"],
            item["pipeline_mail"],
            item["pipeline_truck"],
            item["pipeline"],
            item["wip"],
            item["est_revenue"],
        ])
    _write_table(
        ws_d,
        1,
        daily_headers,
        daily_rows,
        [
            "0", None, "#,##0.00", "#,##0.00", "#,##0.00", "0.0%", "#,##0.00",
            '"$"#,##0.00', "#,##0.00", "#,##0.00", "#,##0.00", "#,##0.00", "#,##0.00", '"$"#,##0.00',
        ],
    )
    _autosize(ws_d, 10, 14)

    ws_c = wb.create_sheet("资金构成")
    cash_rows = [[item["description"], item["amount"], item["kind"]] for item in report["cash_status"]]
    _write_table(ws_c, 1, ["项目", "金额", "类型"], cash_rows, [None, '"$"#,##0.00', None])
    _autosize(ws_c, 18, 40)

    ws_s = wb.create_sheet("运营参数")
    ws_s["A1"] = "工厂"
    ws_s["A1"].font = TITLE_FONT
    factory_headers = ["地区", "当前产能", "计划产能", "运输方式", "订货点", "批量", "优先级", "是否运营"]
    factory_rows = [[
        item.get("region_name"),
        item.get("current_capacity"),
        item.get("scheduled_capacity"),
        item.get("shipping"),
        item.get("order_point"),
        item.get("order_quantity"),
        item.get("priority"),
        "是" if item.get("operational") else "否",
    ] for item in [report["factory"]] if item]
    _write_table(ws_s, 3, factory_headers, factory_rows, [None, "0.00", "0.00", None, "#,##0", "#,##0", "0", None])
    ws_s["A7"] = "仓库"
    ws_s["A7"].font = TITLE_FONT
    warehouse_headers = ["地区", "运输方式", "订货点", "批量", "优先级", "是否运营"]
    warehouse_rows = [[
        item.get("region_name"),
        item.get("shipping"),
        item.get("order_point"),
        item.get("order_quantity"),
        item.get("priority"),
        "是" if item.get("operational") else "否",
    ] for item in [report["warehouse"]] if item]
    _write_table(ws_s, 9, warehouse_headers, warehouse_rows, [None, None, "#,##0", "#,##0", "0", None])
    _autosize(ws_s, 12, 18)

    ws_h = wb.create_sheet("决策历史")
    history_rows = [[
        item.get("day"),
        item.get("parameter"),
        item.get("parameter_short"),
        item.get("factory"),
        item.get("warehouse"),
        item.get("new_value"),
    ] for item in report["history"]]
    _write_table(
        ws_h,
        1,
        ["游戏日", "参数", "参数(短)", "工厂", "仓库", "新值"],
        history_rows,
        ["0.00", None, None, None, None, "#,##0.00"],
    )
    _autosize(ws_h, 12, 48)

    ws_r = wb.create_sheet("排行榜")
    standing_rows = [[item["rank"], item["team"], item["cash"]] for item in report["standing"]]
    _write_table(ws_r, 1, ["排名", "队伍", "现金"], standing_rows, ["0", None, '"$"#,##0.00'])
    my_team = header.get("team")
    for excel_row, item in enumerate(report["standing"], start=2):
        if item["team"] == my_team:
            for col in range(1, 4):
                ws_r.cell(excel_row, col).fill = WARN_FILL
    _autosize(ws_r, 12, 28)

    wb.save(path)
    return path
