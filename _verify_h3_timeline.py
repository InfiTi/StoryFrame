# -*- coding: utf-8 -*-
"""验证 H3 帧号时间轴改动"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core.prompt_loader import get_h3_frame_prompt, get_h3_plan_prompt
from core.templates import get_template  # 假设有这函数，没有就换

# 尝试加载模板
try:
    from core.templates import TEMPLATES, StyleTemplate
    template = TEMPLATES[0] if TEMPLATES else None
except Exception as e:
    template = None
    print("template load skipped:", e)

# 测试 frame prompt（第3帧，起始帧号 60，1.5s = 36帧）
fp = get_h3_frame_prompt(
    frame_num=3, total_frames=6, duration=1.5,
    product_name="华夫饼", product_desc="整箱华夫饼营养早餐",
    selling_points="拉丝,软糯", template=template,
    product_info="", prev_frame_summary="[Shot 2] ...",
    direction="", frame_plan={
        "narrative_beat": "撕开展示拉丝",
        "product_action": "华夫饼拉丝",
        "camera_motion": "Push In",
        "transition": "speed ramp",
    },
    frame_start_frame=60,
)
print("========== Frame Prompt (第3帧, 起始帧号60) ==========")
print(fp[:2500])
print("\n...\n")
print("关键检查:")
print("  含'帧号时间轴':", "帧号时间轴" in fp)
print("  含'Frame 60':", "Frame 60" in fp)
print("  含'Frame 60 - 95':", "Frame 60 - 95" in fp)
print("  含'80-150':", "80-150" in fp)
print("  含'不要限制字数':", "不要限制字数" in fp)
