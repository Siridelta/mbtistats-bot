# NoneBot2 MBTI Stats Plugin

[![NoneBot2](https://img.shields.io/badge/NoneBot2-v2.4+-green.svg)](https://nonebot.dev/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)

自动统计群聊 MBTI 类型分布的 NoneBot2 插件。

## 功能

- **类型识别**: 自动识别群名片/昵称中的 MBTI 类型
  - 支持标准 16 型、扩展型、模糊型（如 `INXP`）、OPS 类型
- **统计图表**: 生成精美的类型分布饼图 + 特质维度柱状图
- **历史趋势**: 记录每日数据，生成折线图趋势
- **自动统计**: 定时自动推送统计结果到群里

## 安装

### 使用 pip

```bash
pip install nonebot-plugin-mbtistats
```

### 使用 nb-cli

```bash
nb plugin install nonebot-plugin-mbtistats
```

### 安装浏览器（必需）

```bash
playwright install chromium
```

## 配置

在 `.env` 文件中添加：

```env
# 数据目录（可选，默认 Bot目录/data/mbtistats/）
# mbtistats_data_dir=/path/to/custom/data

# 自动统计时间（默认每天 00:00）
mbtistats_auto_stats_hour=0
mbtistats_auto_stats_minute=0

# 调试选项
# mbtistats_auto_stats_debug=true          # 调试模式：保存图片但不发送
# mbtistats_auto_stats_run_on_startup=true # 启动时立即执行一次

# 渲染配置（可选）
# mbtistats_render_timeout=30
# mbtistats_viewport_width=1050
# mbtistats_viewport_height=2500
```

## 使用

群聊中发送：

| 指令 | 功能 |
|------|------|
| `/mbti` | 生成当前群的 MBTI 统计图（类型+特质） |
| `/帮助` | 显示帮助信息 |

## 数据存储

```
data/mbtistats/
├── auto_stats_disabled.txt                    # 自动统计黑名单（每行一个群号）
├── data/v1/{group_id}/stats-data.json         # 历史统计数据（JSON）
└── cache/v1/{group_id}/mbti-stats-pic-{timestamp}.png  # 图表缓存
```

## 依赖

- `nonebot2>=2.4.0`
- `nonebot-plugin-apscheduler>=0.5.0`
- `nonebot-adapter-onebot>=2.4.0`
- `playwright>=1.56.0`
- `jinja2>=3.1.6`
- `pydantic>=2.0`

## 注意事项

- **自动统计功能** 仅支持 OneBot V11 协议（QQ 官方 API 无法获取群成员列表）
- 首次启动需要下载 Chromium，可能需要代理

## 许可证

MIT
