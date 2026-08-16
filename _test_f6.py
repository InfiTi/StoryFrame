import json, re
with open('outputs/_cache/华夫饼整箱营养早餐速食面包蛋糕休闲品小吃懒人充饥健康解馋/20260813_000803.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

fr = data['storyboard']['frames'][5]  # Frame 6
motion_hint = str(fr.get("motion_hint", "") or "")
video_prompt = str(fr.get("video_prompt", "") or "")
imd = str(fr.get("integrated_multimodal_description", "") or "")
imd_cn = str(fr.get("integrated_multimodal_description_cn", "") or "")

text_raw = f"{motion_hint} {video_prompt}".strip()
if not text_raw:
    text_raw = f"{imd} {imd_cn}"
text = text_raw.lower()

print(f"text (first 500): {text[:500]}")
print()

# Check drop
drop_kws = ("drop", "fall", "plunge", "drip", "pour", "cascade down", "tumble down", "settle", "descend", "sink", "slide down", "roll down")
for k in drop_kws:
    m = re.search(r'\b' + re.escape(k) + r'\b', text)
    if m:
        ctx = text[max(0,m.start()-20):m.start()+len(k)+20]
        print(f"Drop matched: '{k}' in context: ...{ctx}...")
