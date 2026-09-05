# Supply Chain Game 数据采集

把 NTU / Responsive 的 [Supply Chain Game](https://op.responsive.net/sc/nanyang/entry.html) 按 **3 个游戏日** 汇总成 Excel，并定时写回 GitHub。

官方节奏是 **1 个游戏日 ≈ 14 分钟**，3 日周期大约 42 分钟。脚本每 15 分钟重抓官方曲线，把完整历史重写成工作簿。

## 工作簿

`data/supply_chain_game.xlsx`

| 工作表 | 内容 |
| --- | --- |
| 概览 | 当前日、现金、排名、产能、ROP/Q、库存、当前周期 |
| 三日周期 | 需求 / 缺货 / 交付 / 服务水平 / 出货 / 现金 / 库存 |
| 每日数据 | 从第 1 天到当前日 |
| 资金构成 | 期初现金、收入、利息、生产、运费、持有成本、扩产 |
| 运营参数 | 工厂与仓库设置 |
| 决策历史 | 产能、订货点、批量变更 |
| 排行榜 | 全队现金排名 |

三日周期按游戏日 1–3、4–6 … 切片。Day 730 起标记为接管后。

## 本机运行

```powershell
cd $HOME\sc-game-tracker
.\.venv\Scripts\python -m src.sync --no-push
```

持续看守：

```powershell
.\.venv\Scripts\python -m src.watch
```

或安装 Windows 计划任务（每 15 分钟）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_task.ps1
```

## 推到 GitHub

本机还没有 Git（安装时需要管理员确认）。装好后：

1. 在 GitHub 新建**私有**仓库，不要提交 `.env`
2. `git init`、提交、`git remote add origin <仓库地址>`、`git push -u origin main`
3. 仓库 Secrets 添加 `SC_TEAM_ID` / `GAME_TEAM_ID` 和对应密码
4. 把 `.env` 里的 `GIT_PUSH=1` 打开

`.github/workflows/update-excel.yml` 大约每 40 分钟用 GitHub Actions 再抓一次并提交 Excel。
