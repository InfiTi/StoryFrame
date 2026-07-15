"""导出功能"""

import json
import shutil
from pathlib import Path
from typing import List
from .storyboard import Storyboard


def export_json(storyboard: Storyboard, output_path: str):
    """导出分镜脚本为 JSON"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(storyboard.to_json())


def export_markdown(storyboard: Storyboard, output_path: str):
    """导出分镜脚本为 Markdown"""
    lines = [
        f"# {storyboard.product_name} - 分镜脚本",
        "",
        f"- **风格**：{storyboard.style_name}",
        f"- **产品描述**：{storyboard.product_desc}",
        f"- **分镜数**：{len(storyboard.frames)}",
        "",
        "---",
        "",
    ]

    for frame in storyboard.frames:
        lines.extend([
            f"## 第 {frame.frame} 帧 ({frame.duration}s)",
            "",
            f"**画面描述**：{frame.description}",
            "",
            f"**图片提示词（EN）**：",
            f"```\n{frame.image_prompt}\n```",
            "",
        ])
        if frame.image_prompt_cn:
            lines.extend([
                f"**图片提示词（CN）**：",
                f"```\n{frame.image_prompt_cn}\n```",
                "",
            ])
        lines.extend([
            f"**镜头运动（EN）**：{frame.camera_motion}",
            "",
        ])
        if frame.camera_motion_cn:
            lines.append(f"**镜头运动（CN）**：{frame.camera_motion_cn}")
            lines.append("")
        if frame.motion_hint:
            lines.append(f"**画面动态（EN）**：{frame.motion_hint}")
            lines.append("")
        if frame.motion_hint_cn:
            lines.append(f"**画面动态（CN）**：{frame.motion_hint_cn}")
            lines.append("")
        if frame.image_path:
            lines.append(f"![第{frame.frame}帧]({frame.image_path})")
            lines.append("")
        lines.extend(["---", ""])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def export_package(storyboard: Storyboard, output_dir: str):
    """导出完整包（JSON + Markdown + 图片）"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 导出 JSON
    export_json(storyboard, str(out / "storyboard.json"))

    # 导出 Markdown
    export_markdown(storyboard, str(out / "storyboard.md"))

    # 复制图片
    images_dir = out / "images"
    images_dir.mkdir(exist_ok=True)
    for frame in storyboard.frames:
        if frame.image_path and Path(frame.image_path).exists():
            ext = Path(frame.image_path).suffix
            dst = images_dir / f"frame_{frame.frame}{ext}"
            shutil.copy2(frame.image_path, dst)

    return str(out)
