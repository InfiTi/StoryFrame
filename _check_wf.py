import json

with open(r'E:\AIGC\ComfyUI\ComfyUI_windows_portable\ComfyUI\user\default\workflows\4.0导演台工作流  8-8.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

for node in wf.get('nodes', []):
    ctype = node.get('type', '')
    title = node.get('title', '')
    if 'h3' in ctype.lower() or 'director' in ctype.lower() or 'dir' in ctype.lower():
        nid = node.get('id')
        print(f'Node: type={ctype}, title={title}, id={nid}')
        widgets = node.get('widgets_values', [])
        print(f'  widgets count: {len(widgets)}')
        for i, w in enumerate(widgets):
            wstr = str(w)
            if len(wstr) > 500:
                wstr = wstr[:500] + '...'
            print(f'  [{i}]: {wstr}')
        print()
