# H3 提示词模式实现记录

## 目标
为 StoryFrame 新增 H3 视频提示词生成模式，遵循 MiniMax H3 规范，不改动现有豆包模式。

## 改动文件清单

### 新增文件
1. **prompts/h3_system_prompt.md** — H3 系统提示词（12KB）
   - 完整 H3 规范：[Shot N] 分镜标签、切点时间戳格式、运镜三要素（类型+幅度+速度）
   - integrated_multimodal_description 多模态描述字段（画面+动作+声音）
   - overall_soundscape 全片环境音 + non_diegetic_music 背景音乐
   - 保留现有精华：产品六层描述框架、材质词表、质感-动态映射、运镜-动态联动规则
   - 输出 JSON 数组（前 N 帧数据 + 末尾全局音频对象）

2. **prompts/h3_user_prompt.md** — H3 用户提示词（2.7KB）
   - 产品信息、风格要求、分镜参数、帧时长分配
   - 时间戳计算规则（第1帧空，后续帧累加 duration）
   - 输出格式示例

### 修改文件
3. **core/prompt_loader.py** — 新增 3 个函数（约 160 行）
   - `get_h3_system_prompt(product_texture)` — 加载 H3 系统提示词，回退到模块化组装+H3 附录
   - `get_h3_user_prompt(...)` — 构建 H3 用户提示词
   - `get_h3_copy_prompt(frames, frame_count, lang)` — 从已生成帧数据构建 H3 复制文本
     - 支持 cn/en 双语
     - 非 H3 帧数据有 fallback（提示需用 H3 模式生成）

4. **ui/main_window.py** — 新增 H3 UI 组件（约 40 行）
   - H3 提示词按钮（紫色 #bb9af7，与豆包绿色/橙色区分）
   - `_show_h3_menu()` — 弹出中文/英文选择菜单
   - `_copy_h3_prompt(lang)` — 复制 H3 提示词到剪贴板
   - 在脚本生成完成和缓存加载时启用 H3 按钮

## 验收结果

### 1. 豆包模式回归 — PASS
- `get_doubao_image_prompt()` 和 `get_doubao_video_prompt()` 行为不变
- 测试验证中文内容正确输出

### 2. H3 模式生成 — PASS
- JSON 输出含 [Shot N] + cut_timestamp（At MM:SS.mmm 格式）
- camera_motion 含三要素（类型+幅度+速度，自然英语）
- integrated_multimodal_description 含画面+动作+声音描述
- 末尾全局对象含 overall_soundscape + non_diegetic_music

### 3. UI H3 复制按钮 — PASS
- 按钮在豆包视频按钮之后、视频生成按钮之前
- 点击弹出中文/英文菜单
- 复制内容格式正确（分镜段落 + 全片音频）

### 4. 应用启动 — PASS
- prompt_loader 导入无报错
- MainWindow 类导入无报错
- H3 方法存在性验证通过

## H3 复制示例（中文）
```
[Shot 1] (1.2s)

多模态描述: [Shot 1] 电影质感，中远景拍摄深色表面上的金色酥脆饼干...

运镜: 镜头以快速大幅度推向饼干
画面: 金色酥脆饼干碎裂，芝麻飞溅
...
---
[Shot 2] At 00:01.200, (2.0s)
...
---
[全片音频]
环境音: Steady ambient room tone...
背景音乐: Sparse electronic plucks...
```

## 约束遵守
- 未引入新依赖
- 未改动现有 prompts/ 模板文件（只新增 h3_*.md）
- 未改动豆包/即梦/Agnes 生成链路
- 未执行 git commit
- 备份目录 docs/backup-pre-h3/ 已创建（含原始改动文件副本）
