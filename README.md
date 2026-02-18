# NoneBot2 MBTI Stats Plugin

自动统计群聊 MBTI 类型分布的 NoneBot2 插件。

## 功能

- 自动识别群名片/昵称中的 MBTI 类型
- 生成类型分布统计图
- 生成特质维度分布图
- 历史数据追踪（折线图趋势）
- 定时自动统计推送

## 安装

```bash
pip install nonebot-plugin-mbtistats
```

或使用 `nb-cli`:

```bash
nb plugin install nonebot-plugin-mbtistats
```

## 依赖

安装插件时会自动安装以下依赖：
- `nonebot2>=2.4.0`
- `nonebot-plugin-apscheduler>=0.5.0`
- `playwright>=1.56.0`
- `jinja2>=3.1.6`

首次使用前需要安装 Playwright 浏览器：

```bash
playwright install chromium
```

## 配置

在 `.env` 文件中添加：

```env
# 自动统计相关
auto_stats_debug=false          # 调试模式（保存图片但不发送）
auto_stats_run_on_startup=false # 启动时执行一次
```

## 使用

群聊中发送：
- `/mbti` 或 `/MBTI` - 生成当前群的 MBTI 统计图

## 许可证

MIT
