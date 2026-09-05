# Supply Chain Game 数据采集

把 NTU / Responsive 的 [Supply Chain Game](https://op.responsive.net/sc/nanyang/entry.html) 按 **3 个游戏日** 汇总成 Excel，并定时写回 GitHub。

官方节奏是 **1 个游戏日 ≈ 14 分钟**，3 日周期大约 42 分钟。脚本每 15 分钟抓一次，**只追加新行**，不覆盖已有历史。

## 工作簿

`data/supply_chain_game.xlsx`

| 工作表 | 内容 |
| --- | --- |
| 概览 | 最新状态（这一页会刷新） |
| 快照历史 | 每次抓取追加一行：现金、排名、库存、产能 |
| 三日周期 | 只追加新周期；进行中的周期更新最后一行 |
| 每日数据 | 只追加新游戏日 |
| 资金构成 | 按抓取时间追加 |
| 运营参数 | 参数变化时追加 |
| 决策历史 | 只追加尚未记录的操作 |
| 排行榜 | 按抓取时间追加全队排名 |

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
