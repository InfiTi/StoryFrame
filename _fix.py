import pathlib

p = pathlib.Path('core/prompt_loader.py')
content = p.read_text(encoding='utf-8')

# Fix broken f-strings: literal newline inside f-string should be \n
# Pattern: f"...\n" split across lines
content = content.replace(
    'block = f"### 第 {frame_num} 帧（{duration:.1f}s）\n"',
    'block = f"### 第 {frame_num} 帧（{duration:.1f}s)\\n"'
)
content = content.replace(
    'block += f"**参考图相位**：{phase_cn}\n"',
    'block += f"**参考图相位**：{phase_cn}\\n"'
)

p.write_text(content, encoding='utf-8')
print("Fixed")
