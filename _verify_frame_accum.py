# -*- coding: utf-8 -*-
"""模拟 H3 全片帧号累计，验证 6 帧连续无重叠"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

durations = [1.0, 1.5, 1.5, 1.5, 3.0, 1.5]
frame_start = 0
print("帧号累计（24fps）:")
for i, d in enumerate(durations):
    fc = max(1, round(d * 24))
    end = frame_start + fc - 1
    print(f"  Shot {i+1}: {d}s = {fc}帧  Frame {frame_start}-{end}")
    frame_start += fc
print(f"总帧数: {frame_start}（{sum(durations)}s × 24 = {sum(durations)*24}）")
