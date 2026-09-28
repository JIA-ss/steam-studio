# steam-studio

个人维护、面向开源的 Steam 工作流仓库。以 **skills 为入口**，每个 skill 的采集和执行工具放在自己的 `tools/` 子目录。

第一项能力是 **`steam-research`**：在题材尚未确定时，从市场数据出发发现游戏方向，并支持竞品筛选和有证据的分析。当前版本提供可运行的数据采集器与研究流程，尚未提供一键市场排名、销量预测、商店配置或游戏发布功能。

```text
skills/
  steam-research/
    SKILL.md
    agents/openai.yaml
    references/
    tools/steam-games-scraper/
      SteamGamesScraper.py
      UPSTREAM.md
      LICENSE.md
tests/
docs/
```

## 开始使用

需要 Python 3.10+ 和 [uv](https://docs.astral.sh/uv/)。

```sh
git clone https://github.com/JIA-ss/steam-studio.git
cd steam-studio
uv sync --locked
uv run python skills/steam-research/tools/steam-games-scraper/SteamGamesScraper.py \
  --appids 413150 1145360 --steamspy --data-dir data/smoke
```

以上小样本不需要 API key，也不需要 Gamalytic 订阅。首次扫描官方游戏目录需要环境变量 `STEAM_API_KEY`，见 `.env.example`；程序不会自动读取 `.env`。所有采集均为只读。

将 `skills/steam-research` 安装或链接到支持 `SKILL.md` 的客户端，即可通过 `$steam-research` 使用。例如在仓库根目录执行：

```sh
mkdir -p ~/.codex/skills
ln -s "$(pwd)/skills/steam-research" ~/.codex/skills/steam-research
```

如果目标已存在，先检查，不覆盖已有 skill。新安装的 skill 可能需要新开会话才能发现。仅调用脚本不需要安装 skill。

- [Skill 入口](skills/steam-research/SKILL.md)
- [采集命令、数据结构与恢复](skills/steam-research/references/collector.md)
- [选题分析方法与证据边界](skills/steam-research/references/methodology.md)
- [验证记录](docs/validation.md)

## 数据原则

缺失数据不能当成 0；SteamSpy 拥有量不能当成销量；当前价格乘拥有量不能当成收入。每次采集保存原始响应、来源、时间和失败状态。默认最多选择 20 个游戏，显式 `--all` 才处理完整目录；退出成功也不等于覆盖全市场。

`data/`、本地环境和凭据不提交。免费数据不代表没有网络、存储与维护成本。公开数据也不自动获得再分发许可；本仓库发布的是代码与流程，不发布抓取数据库。

## 维护

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
```

采集器基于 [FronkonGames/Steam-Games-Scraper](https://github.com/FronkonGames/Steam-Games-Scraper) 的 MIT 代码适配，具体版本和变更见 [UPSTREAM.md](skills/steam-research/tools/steam-games-scraper/UPSTREAM.md)。不要把历史 upstream README 当作当前 CLI 文档。

新工具随对应 skill 放置；有实际需求时再增加其他 skills。修复数据逻辑需带行为测试。CI 只运行离线测试，真实接口验证由维护者运行小样本并记录范围，不在每次提交抓取 Steam。

MIT 许可证见 [LICENSE](LICENSE)，上游版权见其独立许可证。本项目与 Valve、Steam 或 Gamalytic 无隶属关系。
