"""
插件配置和数据路径管理
"""

import sys
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from nonebot import logger
from nonebot.plugin import get_plugin_config


class PluginConfig(BaseModel):
    """插件配置类"""
    
    # 数据目录配置
    mbtistats_data_dir: Optional[Path] = Field(
        default=None,
        description="数据存储目录，默认为 Bot 目录下的 data/mbtistats/"
    )
    
    # 自动统计配置
    mbtistats_auto_stats_hour: int = Field(
        default=0,
        description="自动统计的小时（0-23）"
    )
    mbtistats_auto_stats_minute: int = Field(
        default=0,
        description="自动统计的分钟（0-59）"
    )
    mbtistats_auto_stats_debug: bool = Field(
        default=False,
        description="调试模式：保存图片但不发送"
    )
    mbtistats_auto_stats_run_on_startup: bool = Field(
        default=False,
        description="启动时立即执行一次统计"
    )
    
    # 渲染配置
    mbtistats_render_timeout: int = Field(
        default=30,
        description="Playwright 渲染超时时间（秒）"
    )
    mbtistats_viewport_width: int = Field(
        default=1050,
        description="渲染视口宽度"
    )
    mbtistats_viewport_height: int = Field(
        default=2500,
        description="渲染视口高度"
    )


# 获取插件配置
plugin_config = get_plugin_config(PluginConfig)

# 确定 Bot 根目录
# sys.path[0] 是 Python 启动时的脚本目录（即 bot.py 所在目录）
BOT_ROOT = Path(sys.path[0]).resolve()

# 数据根目录（优先使用配置，否则用默认）
if plugin_config.mbtistats_data_dir:
    DATA_DIR = plugin_config.mbtistats_data_dir.resolve()
else:
    DATA_DIR = BOT_ROOT / "data" / "mbtistats"

DATA_DIR.mkdir(parents=True, exist_ok=True)
logger.debug(f"[Config] Bot 根目录: {BOT_ROOT}")
logger.debug(f"[Config] 数据目录: {DATA_DIR}")

# 子目录
V1_DIR = DATA_DIR / "v1"  # 兼容旧数据迁移
V1_DIR.mkdir(parents=True, exist_ok=True)

CACHE_DIR = V1_DIR / "cache-charts"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 文件路径
AUTO_STATS_DISABLED_FILE = DATA_DIR / "auto_stats_disabled.txt"
AUTO_STATS_DISABLED_FILE.touch(exist_ok=True)


def get_group_cache_dir(group_id: str) -> Path:
    """获取指定群的缓存目录"""
    return CACHE_DIR / str(group_id)


def get_group_cache_paths(group_id: str) -> tuple[Path, Path]:
    """
    获取指定群的缓存文件路径
    
    Returns:
        (img_cache_path, data_cache_path)
    """
    group_dir = get_group_cache_dir(group_id)
    group_dir.mkdir(parents=True, exist_ok=True)
    
    img_cache = group_dir / "mbti-stats.png"
    data_cache = group_dir / "mbti-stats.json"
    
    return img_cache, data_cache
