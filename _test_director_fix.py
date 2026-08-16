"""验证 _build_director_script 修复后输出正确的时间戳"""
import json
import sys
sys.path.insert(0, '.')

with open(r'outputs/_cache/华夫饼整箱营养早餐速食面包蛋糕休闲品小吃懒人充饥健康解馋/20260815_011111.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

frames = cache['storyboard']['frames']

# 模拟修复后的 cut_timestamp（用代码累计计算）
elapsed = 0.0
for i, fr in enumerate(frames):
    if i == 0:
        fr['cut_timestamp'] = ''
    else:
        # _format_h3_timestamp 逻辑
        total_ms = int(round(elapsed * 1000))
        mm = total_ms // 60000
        ss = (total_ms % 60000) // 1000
        ms = total_ms % 1000
        if ms >= 1000:
            ms = 999
        fr['cut_timestamp'] = f'At {mm:02d}:{ss:02d}.{ms:03d},'
    elapsed += fr.get('duration', 0)

print('=== 修复后 cut_timestamp ===')
for fr in frames:
    n = fr.get('frame', 0)
    dur = fr.get('duration', 0)
    ts = fr.get('cut_timestamp', '')
    print(f'  Frame {n}: dur={dur}s, cut_timestamp={repr(ts)}')
print(f'  总时长: {elapsed}s')
print()

from core.prompt_loader import _build_director_script
director_text = _build_director_script(frames, lang='en')
print('=== 修复后导演台脚本（前2000字符）===')
print(director_text[:2000])
print('...')
print(f'  总字符数: {len(director_text)}')
print()

# 验证: 每个 [Shot N] 后是否有 At 时间戳（第1帧除外）
import re
shots = re.findall(r'\[Shot\s+(\d+)\]\s*(At\s+\d+:\d+\.\d+,)?', director_text)
print('=== 时间戳验证 ===')
for shot_num, ts in shots:
    has_ts = bool(ts)
    expected = shot_num != '1'  # 第1帧不需要
    status = 'OK' if has_ts == expected else 'FAIL'
    print(f'  Shot {shot_num}: timestamp={repr(ts)} {status}')
