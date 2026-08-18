# -*- coding: utf-8 -*-
"""验证 H3 plan prompt 时间轴 + storyboard 调用链"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core.prompt_loader import get_h3_plan_prompt

try:
    from core.templates import TEMPLATES
    template = TEMPLATES[0] if TEMPLATES else None
except Exception:
    template = None

pp = get_h3_plan_prompt(
    product_name="华夫饼", product_desc="整箱华夫饼营养早餐",
    selling_points="拉丝,软糯", template=template,
    frame_count=6, total_duration=10.5, product_info="", direction=""
)
print("========== Plan Prompt ==========")
print(pp)
print()
print("关键检查:")
print("  含'Step 4.5':", "Step 4.5" in pp)
print("  含'帧号时间轴规划':", "帧号时间轴规划" in pp)
print("  含'Frame 0-23':", "Frame 0-23" in pp)
print("  含'product_action 必须用帧号区间':", "product_action 必须用帧号区间" in pp)
print("  含'80-150':", "80-150" in pp)
