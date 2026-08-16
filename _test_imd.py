import json
with open('outputs/_cache/华夫饼整箱营养早餐速食面包蛋糕休闲品小吃懒人充饥健康解馋/20260813_000803.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for fr in data['storyboard']['frames']:
    imd = fr.get('integrated_multimodal_description', '')
    cn = fr.get('integrated_multimodal_description_cn', '')
    desc = fr.get('description', '')
    print(f'--- Frame {fr["frame"]} ---')
    print(f'desc: {desc}')
    print(f'IMD:  {imd[:300]}')
    print(f'CN:   {cn[:150]}')
    print()
