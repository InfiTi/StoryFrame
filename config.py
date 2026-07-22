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
    # LLM 设置（多模型）
    "llm": {
        "current": "default",  # 当前使用的 provider 名称
        "providers": {
            "default": {
                "base_url": "http://localhost:1234/v1",
                "api_key": "lm-studio",
                "model": "local-model",
            }
        },
    },
    # 视频生成设置（Agnes AI）
    "video": {
        "provider": "agnes",            # 目前仅支持 agnes
        "base_url": "https://apihub.agnes-ai.com/v1",
        "api_key": "",                  # Agnes AI API Key
        "model": "agnes-video-v2.0",
        "image_model": "agnes-image-2.1-flash",  # 图生视频时用 Agnes 生成图片的模型
        "width": 1024,
        "height": 1024,
        "num_frames": 121,               # 帧数，需满足 8n+1
        "frame_rate": 24,               # 帧率
        "negative_prompt": "",          # 负面提示词
        "poll_interval": 5,             # 轮询间隔（秒）
        "timeout": 600,                 # 单任务超时（秒）
    },
    # 图片生成设置（统一 provider）
    "image": {
        "provider": "comfyui",  # comfyui | kontext | sd | dalle | flux | agnes
        "base_url": "http://127.0.0.1:8188",  # ComfyUI 默认地址
        "api_key": "",                  # DALL-E/Agnes 等 API Key
        "model": "agnes-image-2.1-flash",  # 模型名（各 provider 对应不同）
        "size": "1024x1024",
        "quality": "standard",
        "denoise": 0.6,                # img2img 去噪强度
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


def _migrate_llm_config(cfg: dict) -> dict:
    """迁移旧版 LLM 单模型配置到多模型格式"""
    llm = cfg.get("llm", {})
    # 如果有旧字段 base_url，用它们覆盖 providers.default
    old_url = llm.get("base_url")
    if old_url and "providers" in llm:
        # providers 存在但可能是默认占位值，用旧字段覆盖 default
        default_provider = llm["providers"].get("default", {})
        if not default_provider.get("base_url") or default_provider["base_url"] == "http://localhost:1234/v1":
            llm["providers"]["default"] = {
                "base_url": old_url,
                "api_key": llm.get("api_key", "lm-studio"),
                "model": llm.get("model", "local-model"),
            }
            # 清掉旧字段
            for k in ["base_url", "api_key", "model"]:
                llm.pop(k, None)
            cfg["llm"] = llm
    elif "providers" not in llm:
        # 旧格式，迁移
        old_config = {
            "base_url": old_url or "http://localhost:1234/v1",
            "api_key": llm.get("api_key", "lm-studio"),
            "model": llm.get("model", "local-model"),
        }
        cfg["llm"] = {
            "current": "default",
            "providers": {"default": old_config},
        }
    return cfg


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
        # 迁移旧版 LLM 配置
        merged = _migrate_llm_config(merged)
        return merged
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


def get_llm_config(cfg: dict = None) -> dict:
    """获取当前 LLM provider 的配置"""
    if cfg is None:
        cfg = load_config()
    llm = cfg.get("llm", {})
    current = llm.get("current", "default")
    providers = llm.get("providers", {})
    if current not in providers:
        # fallback to first available
        if providers:
            current = list(providers.keys())[0]
        else:
            return {"base_url": "", "api_key": "", "model": ""}
    return providers[current]


def save_config(cfg: dict):
    """保存配置到文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
