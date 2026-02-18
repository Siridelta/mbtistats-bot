# NoneBot Plugin MBTI Stats - 开发文档

> 这份文档是为开发者和 IDE AI 助手准备的。它定义了插件的业务逻辑、API、数据格式和包结构。

## 0. 包结构

```
nonebot-plugin-mbtistats/
├── pyproject.toml              # 包配置和依赖声明
├── README.md                   # 用户文档
├── CONTEXT.md                  # ← 本文档（开发者文档）
└── src/
    └── nonebot_plugin_mbtistats/   # Python 模块名 (PEP 503 规范)
        ├── __init__.py           # 插件入口，命令注册
        ├── analyze.py            # MBTI 数据分析逻辑
        ├── auto_stats.py         # 定时自动统计任务
        ├── config.py             # 配置项定义（待实现）
        ├── get_group_data.py     # 群成员数据获取
        ├── playwright_context.py # Playwright 浏览器上下文管理
        ├── proactive.py          # 主动 API 调用（获取群列表等）
        ├── render.py             # HTML 模板渲染和图片生成
        ├── send_image.py         # 图片发送工具
        └── template/             # HTML 模板目录
            ├── mbti-stats/       # 主统计图表模板
            ├── trait-stats/      # 特质统计模板（备用）
            ├── type-stats/       # 类型统计模板（备用）
            └── images/           # MBTI 类型形象图
```

### 命名规范

- **PyPI 包名**: `nonebot-plugin-mbtistats` (带连字符)
- **Python 模块名**: `nonebot_plugin_mbtistats` (带下划线)
- **NoneBot 插件名**: `nonebot_plugin_mbtistats` (entry point 注册)

## 1. 功能概述

本插件用于自动化统计群成员的 MBTI 人格分布。

### 支持的类型格式

- **标准 16 型**: `INTP`, `enfp` 等
- **扩展型**: 包含 4 字母代码的子串（如 `INTP-T`, `INTP(5w4)`）
- **模糊型**: 用 X 代替不确定字母（如 `INXP`, `exxp`）
- **OPS 类型**: 如 `Te/Se`（需单独检测逻辑）

### 指令

| 指令 | 功能 |
|------|------|
| `/mbti` | 合一指令：同时统计类型和特质，生成综合图表 |
| `/类型统计` | 仅统计 MBTI 16 类型分布 |
| `/特质统计` | 仅统计 4 特质维度分布 |
| `/帮助` | 显示帮助信息 |

### 自动统计

- **频率**: 默认定时执行（可配置 cron）
- **黑名单**: `data/v1/auto_stats_disabled.txt`（每行一个群号）
- **去重**: 数据与上次完全一致时不重复发送
- **调试**: `AUTO_STATS_DEBUG=1` 仅保存图片不发送

**注意**: 自动统计仅支持 OneBot V11，QQ 官方 API 无法获取群成员列表。

## 2. 技术架构

- **框架**: NoneBot2 v2.4+
- **定时任务**: `nonebot-plugin-apscheduler`（通过 `require()` 自动加载）
- **图表渲染**: Playwright + Headless Chromium + ECharts
- **模板引擎**: Jinja2
- **模板位置**: `src/nonebot_plugin_mbtistats/template/`（包内）

### 模板系统

HTML 模板使用 **内联资源**（CSS/JS 通过 Jinja2 `{% include %}` 嵌入），以兼容 Playwright 本地文件渲染。

渲染流程：
1. Jinja2 渲染模板 → 临时 HTML 文件
2. 启动临时 HTTP 服务器（端口随机）
3. Playwright 访问 `http://localhost:{port}/mbti-stats/{temp_file}`
4. 等待 Canvas 渲染 → 截图
5. 清理临时文件和服务器

## 3. 数据存储

### 路径结构（默认）

```
data/v1/
├── cache-charts/{group_id}/
│   ├── mbti-stats.png        # 最新图表缓存
│   └── mbti-stats.json       # 历史数据（时间序列）
└── auto_stats_disabled.txt   # 自动统计黑名单
```

### 历史数据格式

```json
[
  {
    "timestamp": 1704067200000,
    "group_name": "群名称",
    "total_count": 100,
    "type_data": { "INTP": 15, "ENFP": 10, ... },
    "trait_data": { "E": 60, "I": 40, "S": 30, "N": 70, ... }
  }
]
```

### 待实现：配置项

计划添加 `nonebot-plugin-mbtistats` 配置类：

```python
class Config(BaseModel):
    mbtistats_data_dir: Path = Path("./data/mbtistats")
    mbtistats_auto_stats_hour: int = 0
    mbtistats_auto_stats_minute: int = 0
    mbtistats_debug: bool = False
```

## 4. 核心模块说明

### `analyze.py`

- `analyze_type_stats(members)` → `(type_chart_data, total_count)`
- `analyze_trait_stats(members)` → `(trait_chart_data, total_count)`
- 包含 MBTI 正则匹配逻辑

### `render.py`

- `TEMPLATE_ROOT`: `Path(__file__).parent / "template"`
- `render_chart(template_mode, data, width, height)` → `bytes`
- `TempHTTPServer`: 临时 HTTP 服务，处理 CORS 和 MIME 类型

### `auto_stats.py`

- 使用 `@scheduler.scheduled_job("cron", ...)` 注册定时任务
- `perform_auto_stats()`: 执行统计逻辑
- 通过 `on_bot_connect` 支持启动时执行

### `proactive.py`

主动 API 调用（非事件驱动）：
- `get_group_members_proactive(bot, group_id)`
- `get_all_groups_proactive(bot)`
- `send_image_to_group_proactive(bot, group_id, image_bytes)`

## 5. 开发环境

使用 `mbtistats-bot` 仓库作为开发环境：

```bash
git clone https://github.com/Siridelta/nonebot-plugin-mbtistats-devbot.git
cd mbtistats-bot
git submodule update --init
uv sync
uv run bot.py
```

编辑插件代码在 `dev-plugins/mbtistats/` 目录内，该目录是独立的 git 仓库（submodule）。

---

**相关仓库**:
- 插件源码: https://github.com/Siridelta/nonebot-plugin-mbtistats
- 开发环境: https://github.com/Siridelta/nonebot-plugin-mbtistats-devbot
