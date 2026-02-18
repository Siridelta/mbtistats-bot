"""
插件配置和数据路径管理
"""

from pathlib import Path
from nonebot import get_driver, logger

# 获取 NoneBot 驱动和配置
driver = get_driver()

# 确定 Bot 根目录（优先使用 env_file 所在目录）
if driver.config.env_file:
    BOT_ROOT = Path(driver.config.env_file).parent.resolve()
else:
    BOT_ROOT = Path.cwd().resolve()
    logger.warning(f"[Config] 未配置 env_file，使用当前工作目录: {BOT_ROOT}")

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
