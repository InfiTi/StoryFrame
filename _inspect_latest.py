import json
with open(r'outputs\_cache\华夫饼整箱营养早餐速食面包蛋糕休闲品小吃懒人充饥健康解馋\20260815_011111.json', encoding='utf-8') as f:
    data = json.load(f)
frames = data['storyboard']['frames']
print('=== 全部6帧字段长度 ===')
for fr in frames:
    vp = fr.get('video_prompt') or ''
    imd = fr.get('integrated_multimodal_description') or ''
    print(f"Frame {fr['frame']}: video_prompt={len(vp)}字 imd={len(imd)}字 shot_label={fr.get('shot_label')} desc={fr.get('description')}")
print()
print('=== Frame 5 完整 imd ===')
print(frames[4].get('integrated_multimodal_description'))
print()
print('=== Frame 5 完整 imd_cn ===')
print(frames[4].get('integrated_multimodal_description_cn'))
