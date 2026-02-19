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
    DATA_ROOT = plugin_config.mbtistats_data_dir.resolve()
else:
    DATA_ROOT = BOT_ROOT / "data" / "mbtistats"

DATA_ROOT.mkdir(parents=True, exist_ok=True)
logger.debug(f"[Config] Bot 根目录: {BOT_ROOT}")
logger.debug(f"[Config] 数据根目录: {DATA_ROOT}")

# ========== 数据目录（持久化存储） ==========
# 结构: data/mbtistats/data/v1/{group_id}/stats-data.json
DATA_DIR = DATA_ROOT / "data" / "v1"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ========== 缓存目录（可重建的临时文件） ==========
# 结构: data/mbtistats/cache/v1/{group_id}/mbti-stats-pic-{timestamp}.png
CACHE_DIR = DATA_ROOT / "cache" / "v1"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 配置文件
AUTO_STATS_DISABLED_FILE = DATA_ROOT / "auto_stats_disabled.txt"
AUTO_STATS_DISABLED_FILE.touch(exist_ok=True)


def get_group_data_dir(group_id: str) -> Path:
    """获取指定群的数据目录（用于 JSON 存档）"""
    group_dir = DATA_DIR / str(group_id)
    group_dir.mkdir(parents=True, exist_ok=True)
    return group_dir


def get_group_cache_dir(group_id: str) -> Path:
    """获取指定群的缓存目录（用于图片缓存）"""
    group_dir = CACHE_DIR / str(group_id)
    group_dir.mkdir(parents=True, exist_ok=True)
    return group_dir


def get_group_data_path(group_id: str) -> Path:
    """
    获取指定群的统计数据文件路径
    
    Returns:
        JSON 数据文件路径 (stats-data.json)
    """
    return get_group_data_dir(group_id) / "stats-data.json"


def get_chart_cache_path(group_id: str, timestamp: Optional[int] = None) -> Path:
    """
    获取图表缓存图片路径（带时间戳）
    
    Args:
        group_id: 群号
        timestamp: 时间戳（毫秒），不传则使用当前时间
    
    Returns:
        图片缓存路径
    """
    if timestamp is None:
        import time
        timestamp = int(time.time() * 1000)
    
    cache_dir = get_group_cache_dir(group_id)
    return cache_dir / f"mbti-stats-pic-{timestamp}.png"


def get_latest_chart_cache(group_id: str) -> Optional[Path]:
    """
    获取指定群最新的图表缓存文件
    
    Returns:
        最新的缓存文件路径，如果没有则返回 None
    """
    cache_dir = get_group_cache_dir(group_id)
    if not cache_dir.exists():
        return None
    
    # 查找所有 mbti-stats-pic-*.png 文件
    pic_files = list(cache_dir.glob("mbti-stats-pic-*.png"))
    if not pic_files:
        return None
    
    # 按修改时间排序，返回最新的
    return max(pic_files, key=lambda p: p.stat().st_mtime)
