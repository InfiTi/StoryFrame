"""模拟导演台前端 parseOfficialScript 解析修复后的脚本"""
import re

def parse_official_script(text):
    """简化版 parseOfficialScript（移植 JS 逻辑）"""
    t = str(text or "")
    shot_re = re.compile(r'\[Shot\s+(\d+)\s*\]', re.IGNORECASE)
    marks = []
    for m in shot_re.finditer(t):
        marks.append((m.start(), m.end()))
    
    has_label = bool(re.search(r'integrated_multimodal_description\s*[:：]', t, re.IGNORECASE))
    if not has_label and not (len(marks) >= 2 and re.search(r'At\s+\d{1,3}:\d{2}', t)):
        return None
    if not marks:
        return None
    
    # 切镜
    at_re = re.compile(r'^[\s,，]*At\s+(?:(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?|(\d+(?:\.\d+)?)\s*s)\s*[,，]?\s*', re.IGNORECASE)
    
    # 声音字段
    snd_m = re.search(r'overall_soundscape\s*[:：]', t, re.IGNORECASE)
    mus_m = re.search(r'non_diegetic_music\s*[:：]', t, re.IGNORECASE)
    
    region_end = len(t)
    for mm in [snd_m, mus_m]:
        if mm and mm.start() > marks[0][0]:
            region_end = min(region_end, mm.start())
    
    shots = []
    for i, (start, end) in enumerate(marks):
        to = marks[i+1][0] if i+1 < len(marks) else region_end
        body = t[end:to].strip()
        shot_start = None
        am = at_re.match(body)
        if am:
            if am.group(1) is not None:
                shot_start = int(am.group(1)) * 60 + int(am.group(2)) + (float('0.' + am.group(3)) if am.group(3) else 0)
            else:
                shot_start = float(am.group(4))
            body = body[am.end():].strip()
        shots.append({'start': shot_start, 'body': body})
    
    if not shots:
        return None
    if shots[0]['start'] is None:
        shots[0]['start'] = 0
    
    # 计算每镜时长
    last_raw = 0
    for i in range(len(shots)):
        d = 0
        if shots[i]['start'] is not None:
            for j in range(i+1, len(shots)):
                if shots[j]['start'] is not None:
                    d = shots[j]['start'] - shots[i]['start']
                    break
        if not (d > 0):
            d = last_raw
        if d > 0:
            last_raw = d
        shots[i]['dur'] = d if d > 0 else 0
    
    total = shots[-1]['start'] + shots[-1]['dur'] if shots else 0
    return {'shots': shots, 'total': total, 'seg_count': len(shots)}


# 读取修复后的导演台脚本
import json
import sys
sys.path.insert(0, '.')

with open(r'outputs/_cache/华夫饼整箱营养早餐速食面包蛋糕休闲品小吃懒人充饥健康解馋/20260815_011111.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

frames = cache['storyboard']['frames']

# 修复 cut_timestamp
elapsed = 0.0
for i, fr in enumerate(frames):
    if i == 0:
        fr['cut_timestamp'] = ''
    else:
        total_ms = int(round(elapsed * 1000))
        mm = total_ms // 60000
        ss = (total_ms % 60000) // 1000
        ms = total_ms % 1000
        if ms >= 1000:
            ms = 999
        fr['cut_timestamp'] = f'At {mm:02d}:{ss:02d}.{ms:03d},'
    elapsed += fr.get('duration', 0)

from core.prompt_loader import _build_director_script
director_text = _build_director_script(frames, lang='en')

# 解析
result = parse_official_script(director_text)
if result is None:
    print('ERROR: parseOfficialScript 返回 None!')
else:
    print(f'=== parseOfficialScript 解析结果 ===')
    print(f'总时长: {result["total"]}s')
    print(f'镜头数: {result["seg_count"]}')
    print()
    for s in result['shots']:
        print(f'  Shot: start={s["start"]}s, dur={s["dur"]}s')
    print()
    print(f'<= 15s? {result["total"] <= 15.083}')
    print(f'→ 将合并成 1 段生成（而非 autoSplitByDuration）')
