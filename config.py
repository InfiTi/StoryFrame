"""StoryFrame 配置文件"""

import json
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# 输出目录
OUTPUT_DIR = BASE_DIR / "outputs"

# 配置文件路径
CONFIG_FILE = BASE_DIR / "config.json"

# 默认配置
DEFAULT_CONFIG = {
    # LLM 设置
    "llm": {
        "base_url": "http://localhost:1234/v1",  # LMStudio 默认地址
        "api_key": "lm-studio",
        "model": "local-model",
    },
    # 图片生成设置
    "image": {
        "provider": "dalle",  # dalle | flux | sd
        "base_url": "http://localhost:7860",  # SD WebUI 默认地址
        "api_key": "",
        "model": "dall-e-3",
        "size": "1024x1024",
        "quality": "standard",
    },
    # 默认分镜数
    "storyboard": {
        "frame_count": 5,
        "duration": 15,  # 总时长（秒）
    },
    # 商品目录
    "product": {
        "directory": "",  # 商品信息 Markdown 所在目录
    },
    # 提示词缓存
    "cache": {
        "max_versions": 3,  # 每个商品保留最近 N 个版本
    },
}


def load_config() -> dict:
    """加载配置，如果不存在则创建默认配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # 合并默认值（防止新字段缺失）
        merged = DEFAULT_CONFIG.copy()
        for k, v in cfg.items():
            if isinstance(v, dict) and k in merged:
                merged[k].update(v)
            else:
                merged[k] = v
        return merged
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


def save_config(cfg: dict):
    """保存配置到文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
