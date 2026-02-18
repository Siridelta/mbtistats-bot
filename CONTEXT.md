# MBTI 统计机器人 - 项目开发文档

> 这份文档是为开发者和 IDE AI 助手准备的。它清晰地定义了项目的上下文、技术栈以及部署流程。

## 1. 项目背景与功能
本项目旨在开发一个 QQ 机器人，用于自动化统计群成员的 MBTI 人格分布
（基于群成员的呢称里自己声明/标注的MBTI类型，支持 MBTI 16型，扩展型（一般包含 4 字母代码，故可用相同逻辑检测），模糊型（用字母X代替其中的若干字母），OPS 类型（不包含通用 MBTI 4 字母代码，需要单独检测））

*   **核心痛点**：替代人工手动统计；避免 Matplotlib 等面向科研的库出图审美枯燥的问题。
*   **主要功能**：
    1.  **指令触发**：接收群指令
        * `/类型统计`：统计当前群的 MBTI 16 类型分布。
        * `/特质统计`：统计当前群的 MBTI 4 特质维度（E/I, S/N, T/F, J/P）分布。
        * `/mbti` (合一指令)：同时统计类型和特质，并生成包含历史趋势的综合图表。
        * `/帮助` 或 `/help`：显示帮助信息。
    2.  **自动统计**：定时自动统计群成员 MBTI 分布，无需用户手动触发指令。
        * **统计频率**：默认每小时执行一次（可配置）。
        * **结果发送**：统计完成后自动将图表发送到群里。
        * **黑名单模式**：默认对所有群启用，可在 `data/v1/auto_stats_disabled.txt` 中禁用特定群（每行一个群 ID）。
        * **数据去重**：如果数据与上次完全一致，不会重复记录和发送。
        * **调试模式**：设置环境变量 `AUTO_STATS_DEBUG=1` 可在本地调试时不发送图片，只保存到 `data/v1/cache-charts/{group_id}/` 目录。
        * **启动时执行**：设置 `AUTO_STATS_RUN_ON_STARTUP=1` 可在 Bot 启动时立即执行一次统计（调试用）。
        * **仅支持 OneBot V11**：QQ 官方 API 暂不支持主动获取群成员列表。
    3.  **数据抓取**：获取群成员列表，解析群名片中的 MBTI 关键词。
    4.  **高颜值绘图**：生成带有较精美风格的图表。
        > 其中饼状图部分带有文字标签（如："INTP 73人\n13%"），同时对主要类型附加对应漫画形象图（覆盖在饼状图上）；需要自动排布图表的文字标签和漫画形象，防止重叠。
    5.  **消息回复**：将生成的图片发送回 QQ 群。
    6.  **数据持久化**：
        *   **缓存**：缓存生成的图片，减少重复渲染。
        *   **历史记录**：以 JSON 文件形式存储群内的 MBTI 统计历史数据（时间序列），用于生成趋势图。
        > 这种基于文件系统的方式只适用于标准服务器/本地机器环境，不适用于云函数环境，同时也只适用于少量数据；后续需要优化。

### 部署场景 (双轨制)

本项目目前支持并维护两种部署/运行场景，且**短期内以场景 B 为主**：

*   **场景 A：腾讯云云函数 (SCF) + QQ 官方开放平台**
    *   **架构**：WebHook 模式，通过 Docker 镜像部署到腾讯云 SCF。
    *   **现状**：由于官方 API 功能受限（暂时无法获取群成员列表，仅支持获取频道成员列表），目前作为兼容目标维护，功能可能受限。
*   **场景 B：本地/服务器部署 + OneBot v11 (主力开发)**
    *   **架构**：WebSocket 模式，连接到兼容 OneBot v11 协议的实现端（如 **LLOneBot**, NapCat 等）。
    *   **现状**：这是目前的主力开发和测试场景。得益于 OneBot 生态的开放性，可以无障碍获取群成员列表、发送大图等，开发体验更佳。

## 2. 技术架构

*   **编程语言**：Python 3.13 (通过 Docker 镜像或 `uv` 环境管理)。
*   **Bot 框架**：`NoneBot2`。
    *   适配器：同时安装并支持 `nonebot-adapter-qq` (官方) 和 `nonebot-adapter-onebot` (OneBot v11)。
*   **绘图方案**：使用无头浏览器和 web 前端工程渲染图表。
    *   **前端**：HTML + ECharts (负责布局、逻辑计算、防重叠)。
    *   **渲染**：Playwright (Python) 调用 Headless Chromium 进行截图；使用 Jinja2 模板引擎渲染 HTML 模板。
    *   **资源加载**：为了兼容 Playwright 本地渲染，HTML 模板中的 CSS/JS 资源通过 Jinja2 `{% include %}` 语法内联。
*   **依赖管理**：`uv` (接替 pip/poetry)。

### 场景 A (官方 API + 腾讯云云函数)

**架构图:**

![QQ 机器人官方开放平台（QQ Open Platform）QQ 机器人 Webhook API 架构图](./docs/QQ_Open_Platform_QQ_Bot_Webhook_API_Architecture.png)

QQ 机器人官方开放平台（QQ Open Platform）使用 Webhook API 方式运行 Bot 应用，需要提供一个 Web 服务来接收 QQ 的回调请求，架构如图（其中 Websocket 部分已不再被支持）。

**部署环境:**

腾讯云云函数 (SCF) - Web 函数模式 + **自定义镜像模式 (Custom Image)**。
> 由于腾讯云 SCF 基础环境限制（CentOS 7/glibc 版本过低），本项目采用 **Docker 容器化部署** 方案。将 Docker 镜像推送到腾讯云镜像仓库（TCR），然后腾讯云函数（SCF）使用该镜像部署。
> 腾讯云 SCF 对自定义镜像模式的限制为解压前大小不超过 1 GB。粗略计算，官方 Python Slim 基础镜像 (~120MB) + Chromium (~300MB) + 依赖库 + 字体，通常总大小在 600MB-800MB 左右，是可以塞进去的

### 场景 B (OneBot v11 + 本地机器/服务器部署)

**架构图（以反向 WebSocket 为例）:**

```mermaid
graph LR
    User[用户] --> QQ[QQ 客户端/NTQQ]
    QQ <-->|注入/协议实现| LLOneBot[LLOneBot / NapCat]
    LLOneBot(ws客户端) <-->|反向 WebSocket (OneBot v11)| Bot(ws服务端)[NoneBot2 本项目 + OneBot v11 适配器]
    Bot -->|Playwright| Chrome[Headless Chromium]
```

## 3. 开发环境配置 (基于 uv)
本项目使用 `uv` 进行包管理，确保依赖版本锁定。

```bash
# 1. 初始化/同步依赖 (根据 pyproject.toml 和 uv.lock)
uv sync

# 2. 安装 Playwright 浏览器内核 (本地开发必做)
uv run playwright install chromium

# 3. 本地运行 Bot
# 需在 .env 文件中配置好适配器相关信息：
# - 官方场景：QQ_APP_ID, QQ_TOKEN
# - OneBot场景：ONEBOT_WS_URL (或由 nb-cli 默认配置)
uv run bot.py

# 本地开发时也可使用 nb cli 启动 Bot；
# 安装 nb cli:
uv tool install nb-cli
# 启动 Bot:
nb run
```

## 4. 前端开发与调试

本项目包含一套完整的前端调试工作流，支持在不运行 Bot 的情况下独立开发图表模板，预览图表效果。
“模式”对应不同的图表界面和不同的 Bot 指令，模式名即为 template 下的子目录名，但是不一定与 Bot 指令名完全对应。

```bash
# 启动前端调试模式
# <mode> 为模板目录名，例如：mbti-stats
uv run debug_frontend.py mbti-stats
```

*   **功能**：
    *   自动扫描 `template/` 目录下的模板。
    *   自动加载对应目录下的 `mock.json` 测试数据。
    *   **热更新**：同时监听 `index.html` 和 `mock.json` 的变化，自动重新渲染 `preview.html`。
    *   **内联支持**：和 Bot 运行时的 Jinja2 环境一样，同样支持 CSS/JS 内联渲染。

脚本将持续监听变化，并自动使用 mock 数据渲染至 `template/<mode>/preview.html` 文件。然后需要使用 IDE 的 Live Server 插件打开 `template/<mode>/preview.html` 文件，实时预览渲染效果。

## 5. 部署工作流

### 5.1 Docker 部署 (主要针对场景 A / 云服务器)
*   **Dockerfile**：已配置为基于 `python:3.13-slim`，集成 `uv` 和 `chromium`。
*   **腾讯云仓库 (TCR)**：你需要替换下方的 `<namespace>` 和 `<repo_name>`。
    *   示例地址：`ccr.ccs.tencentyun.com/<namespace>/<repo_name>`
    *   目前暂时使用：`ccr.ccs.tencentyun.com/sirilit/mbtistats-bot`
    *   不使用像 `.env.prod` 这样的面向生产环境的配置文件。直接使用腾讯云 SCF 配置界面参考 `.env.example` 来手动配置所有环境变量。`.env` 文件仅用于本地开发环境使用。
*   **发布到腾讯云 SCF**：
    1.  构建 Docker 镜像。
    2.  推送到腾讯云镜像仓库 (TCR)。
    3.  在 SCF 控制台更新镜像。


#### 常用指令片段

**场景 A：本地模拟运行 (测试 Docker 环境)**
```bash
# 1. 构建镜像 (本地标签)
docker build -t mbtistats-bot-local .

# 2. 运行容器 (映射端口 9000)
# 访问 http://localhost:9000 验证服务是否启动
docker run -p 9000:9000 --env-file .env mbtistats-bot-local
```

**场景 B：发布到腾讯云 SCF**
```bash
# 变量定义 (请替换为实际值)
export TCR_URL="ccr.ccs.tencentyun.com/<你的命名空间>/<你的仓库名>"
export VERSION="v1.0.0"  # 建议每次递增版本号

# 1. 登录腾讯云镜像仓库 (仅需执行一次)
# 密码在腾讯云控制台 -> 容器镜像服务 -> 访问凭证 中设置
docker login ccr.ccs.tencentyun.com --username=<你的腾讯云账号ID>

# 2. 构建并打标签 (针对云端)
# 注意命令最后有一个点 "."
docker build -t $TCR_URL:$VERSION .

# 3. 推送镜像到腾讯云
docker push $TCR_URL:$VERSION

# 4. 部署后续
# 推送成功后，前往腾讯云 SCF 控制台 -> 函数服务 -> 镜像配置 -> 点击“更新镜像”并选择刚才推送的版本。
```

### 5.2 本地/裸机部署 (针对场景 B)
1.  确保本地安装有 Python 3.13+ 和 `uv`。
2.  运行 `uv sync` 安装依赖。
3.  运行 `uv run playwright install chromium`。
4.  配置 `.env` 连接到本地的 LLOneBot 或其他 OneBot 实现。注意，需要同时配置环境变量根文件 `.env` 和具体场景的环境变量文件（如`.env.onebotv11-wsRev.example`）。
5.  启动 OneBot 实现端，例如 LLOneBot。
6.  运行 `uv run bot.py`。
> 可使用 `pm2` 或 `systemd` 守护进程。但是其实在裸机场景里大概率不必要，sirilit 的运行环境里（旧电脑 win11 系统）只需保持终端打开即可保持 Bot 运行。

## 6. 目录结构说明
```text
.
├── Dockerfile          # 构建脚本 (Python 3.13 + uv + Playwright + Chromium + 字体依赖 Fonts)
├── pyproject.toml      # 依赖定义
├── uv.lock             # 依赖锁定
├── .env                # 环境变量根文件 (不要提交)
├── .env.example        # 环境变量根文件示例
├── .env.qqbot.example  # QQ 官方开放平台环境变量文件示例
├── .env.onebotv11.example  # OneBot v11 环境变量文件示例
├── .env.onebotv11-wsRev.example  # OneBot v11 反向 WebSocket 环境变量文件示例
├── bot.py              # Bot 入口
├── debug_frontend.py   # 前端调试工具
├── plugins/            # Bot 插件源码
│   └── mbtistats/
│           ├── __init__.py      # 插件入口 (指令处理、历史数据管理)
│           ├── analyze.py       # 数据分析逻辑
│           ├── render.py        # Playwright 渲染逻辑
│           ├── proactive.py     # 主动模式工具函数 (非事件响应场景)
│           ├── auto_stats.py    # 自动统计功能 (定时任务)
│           └── ...其他脚本
├── template/           # 前端模板 (HTML/CSS/JS)
│   ├── mbti-stats/     # 合一指令模板
│   │   ├── index.html  # 主模板 (含 Jinja2 变量)
│   │   ├── mock.json   # 调试用测试数据，debug_frontend.py 使用
│   │   ├── styles.css  # 样式 (被 index.html 内联引用)
│   │   └── scripts.js  # 脚本 (被 index.html 内联引用)
│   └── ...
└── data/               # 运行时数据
    └── v1/
        ├── auto_stats_disabled.txt  # 自动统计禁用列表（黑名单）
        └── cache-charts/            # 图片缓存 & 数据缓存
            └── {{ group_id }}/      # 按群组 ID 缓存
                ├── mbti-stats.png   # 图片缓存
                └── mbti-stats.json  # 数据缓存
```
