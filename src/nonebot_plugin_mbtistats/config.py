"""
插件配置和数据路径管理
"""

import sys
from pathlib import Path
from nonebot import logger

# 确定 Bot 根目录
# sys.path[0] 是 Python 启动时的脚本目录（即 bot.py 所在目录）
BOT_ROOT = Path(sys.path[0]).resolve()
logger.debug(f"[Config] Bot 根目录: {BOT_ROOT}")

# 数据根目录（可配置，默认为 data/mbtistats/）
# TODO: 后续可改为从 pydantic Config 读取
DATA_DIR = BOT_ROOT / "data" / "mbtistats"
DATA_DIR.mkdir(parents=True, exist_ok=True)

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
