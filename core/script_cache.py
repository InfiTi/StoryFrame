"""分镜脚本缓存管理

缓存结构：outputs/_cache/<商品名>/<时间戳>.json
每个商品保留最近 max_versions 个版本。
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


CACHE_DIR = Path("outputs") / "_cache"


def _sanitize_name(name: str) -> str:
    """清理商品名作为文件夹名"""
    # 去掉非法字符
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    return safe[:80]  # 限制长度


def get_cache_dir(product_name: str) -> Path:
    """获取商品的缓存目录"""
    return CACHE_DIR / _sanitize_name(product_name)


def save_cache(product_name: str, storyboard_data: dict, style_name: str = "") -> Path:
    """保存分镜脚本到缓存，返回文件路径"""
    cache_dir = get_cache_dir(product_name)
    cache_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cache_file = cache_dir / f"{timestamp}.json"

    cache_data = {
        "timestamp": timestamp,
        "product_name": product_name,
        "style_name": style_name,
        "storyboard": storyboard_data,
    }

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

    return cache_file


def list_cache(product_name: str, max_versions: int = 3) -> list[dict]:
    """列出商品的缓存版本，按时间倒序"""
    cache_dir = get_cache_dir(product_name)
    if not cache_dir.exists():
        return []

    files = sorted(cache_dir.glob("*.json"), reverse=True)
    result = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            result.append({
                "file": str(f),
                "timestamp": data.get("timestamp", f.stem),
                "style_name": data.get("style_name", ""),
                "frame_count": len(data.get("storyboard", {}).get("frames", [])),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return result[:max_versions] if max_versions > 0 else result


def load_cache(file_path: str) -> Optional[dict]:
    """加载缓存文件，返回 storyboard 数据"""
    p = Path(file_path)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("storyboard")


def cleanup_cache(product_name: str, max_versions: int = 3):
    """清理旧缓存，只保留最近 max_versions 个版本"""
    cache_dir = get_cache_dir(product_name)
    if not cache_dir.exists():
        return

    files = sorted(cache_dir.glob("*.json"), reverse=True)
    if len(files) <= max_versions:
        return

    for f in files[max_versions:]:
        f.unlink(missing_ok=True)


def get_cache_dir_for_product(product_name: str) -> Optional[Path]:
    """获取商品的缓存目录，如果不存在返回 None"""
    d = get_cache_dir(product_name)
    return d if d.exists() else None
