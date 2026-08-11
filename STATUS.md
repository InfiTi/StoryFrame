# StoryFrame 项目状态

> 最后更新: 2026-08-12 | 版本 v0.13.0

## 概述
分镜图生成器 — 商品信息 → 分镜脚本 → 图片/视频提示词，PySide6 桌面应用。统一生成接口支持多 provider 切换。

## 当前状态
- **版本**: v0.12.0
- **阶段**: 三模式分镜生成（标准模式：预设驱动 + H3 普通：叙事驱动 + H3 导演台：ComfyUI H3 导演台脚本格式）

## 已完成
- [x] 分镜脚本生成（LLM + JSON 流式解析）
- [x] 商品信息管理（读取/编辑/回写 Markdown）
- [x] 风格模板系统（9 预设 + 外部 JSON 配置）
- [x] 提示词模板化（prompts/ Markdown 模板）
- [x] 背景音乐选择 + 模板自动同步
- [x] 豆包图片/视频提示词一键复制（菜单选择中文/英文）
- [x] 冲击强度 + 节奏策略字段（duration_plan 已验证生效）
- [x] 口味标签提取 + 负向词按风格区分
- [x] JSON 解析容错增强（10 种异常处理）
- [x] Tokyo Night 深色主题配色
- [x] 视频方向输入框（自由指定调性/风格）
- [x] 商品列表自适应高度（不再被刷新按钮遮挡）
- [x] 画面描述去噪（安全区描述 + 负向词自动去除）
- [x] 底部按钮精简为豆包图片/视频两个菜单按钮（中文/英文选择）
- [x] Agnes AI 视频生成接入（core/video_client.py + 设置 UI + 主窗口按钮）
- [x] Agnes 图生视频全链路（Agnes 图片生成→公网URL→视频生成，无需手动上传图床）
- [x] **统一生成管理器**（core/generation_manager.py）— 图片+视频统一入口，provider 可切换
- [x] 图片 provider 统一：comfyui/kontext/sd/dalle/flux/agnes 共用同一设置
- [x] 视频 provider 统一：agnes（通过 GenerationManager 调用）
- [x] 设置 UI 统一：图片和视频各 provider 共用一套地址/Key/模型设置
- [x] 图片生成按钮改为走 GenerationManager
- [x] 视频生成按钮改为走 GenerationManager
- [x] 按钮文案统一："生成图片" / "🎥 生成视频"
- [x] system_prompt 纯中文翻译约束
- [x] 单帧重新生成（每帧卡片有 🔄 按钮，不满意可单独重生该帧提示词，保留已生成图片）
- [x] 风格模板管理（设置对话框新增「🎨 风格模板」Tab，可增/删/复制/编辑模板，保存到 templates.json）
- [x] **镜头模板库扩充至 9 个**（3 快节奏 + 3 慢节奏 + 3 创意类）
- [x] **镜头模板评分系统**（core/scoring.py）— 对照模板逐项打分，支持修正建议和反馈记录
- [x] **动作相位系统（motion_phase）**: pre-action/mid-action/post-action/static 四阶段
- [x] **P0: 镜头模板扩充** — 新增 6 个模板（品味揭示/环绕展示/微距焦点变换/滑动变焦冲击/俯拍旋转/移轴微缩）
- [x] **P1: 帧间连贯性增强** — 上下文传递从简单描述升级为物理状态摘要（动作相位+运镜+动态趋势+过渡+视频起止状态），frame_prompt.md 新增物理状态连续性 5 项约束
- [x] **P2: 动态表现力提升** — core.md 新增 4 层动态表现力体系（主体动作/微表情/环境互动/情绪氛围），4 个质感模块各新增微动态词汇表+情绪氛围词汇表
- [x] **P3: 运动指令语义增强** — video_prompt 格式从箭头分隔改为自然语言（适配豆包/可灵/Runway 等主流模型），新增画质词+约束词，doubao_video_prompt.md 新增禁止动态+画质约束段
- [x] **视频提示词模板精简** — doubao_video_prompt.md 从 2000+ 字缩减到 180 字，删除冗余的 motion_phase 详细说明和运动规范
- [x] **风格参数注入视频提示词** — get_doubao_video_prompt 新增 style_name/style_words/camera_words 参数，UI 调用处同步传入，「灵动冲击」等风格特征真正传到视频模型
- [x] **frame block 精简** — 从 6 行键值对改为 3 行紧凑格式（参考图状态+video_prompt+转场）
- [x] **motion_phase 一致性约束** — frame_prompt.md 新增 motion_phase 与 motion_hint/image_prompt 严格一致性规则
- [x] **video_prompt 词数收紧** — 从 40-80 词改为 40-70 词，超 70 必须删减情绪修饰语
- [x] **禁止精确数值** — video_prompt 禁止写精确秒数和角度数值（如 0.6s, 270 degrees），用自然描述替代
- [x] **image_prompt_cn 纯中文约束** — 新增技术术语翻译参考（slate→深灰石板等）+ 禁止残留英文单词
- [x] **camera_motion 去箭头** — core.md 和 camera_templates.yaml 全部消除 → 箭头分隔，改为自然语句
- [x] **LLM 空响应重试** — chat_json 新增 max_retries=2，空返回自动重试 2 次，间隔 2 秒
- [x] **空结果警告** — generate_frame_detail 检测空结果并打印警告
- [x] **运动示意图（分镜蓝图）** — `core/motion_sketch.py` 黑白线稿+箭头+粒子，喂给视频模型理解运动
- [x] **示意图三模式** — programmatic（本地绘制）/ ai（Agnes 生成）/ hybrid（本地底稿+Agnes 精修）
- [x] **运动信息启发式提取** — 从 motion_hint/video_prompt/camera_motion 关键词解析结构化运动字段
- [x] **每帧 ✏️ 按钮 + 缩略图预览** — 一键生成/更新运动示意图，点击可放大
- [x] **三模式草稿按钮** — 每帧 ✏️（按设置）/ 🎨（AI 生成）/ 🧬（混合精修），缩略图放大、预览点空白关闭
- [x] **生成进度反馈** — 点击草稿按钮后进度条 + 分阶段状态（解析→绘制→调用接口→下载→完成），运行中禁用按钮，失败/异常弹窗
- [x] **预览点任意处关闭** — 图片预览窗口内任意位置（图片/空白/提示文字）点击即关闭
- [x] **进度条加高** — 从 4px 细条改为 20px，加粗 12px 百分比文字
- [x] **草稿提示词可配置** — 设置里可编辑 AI 生成/混合精修提示词模板，占位符 {shape} {motion} {direction} {speed} {particles} {camera} {description}
- [x] **图生视频优先用示意图** — 有示意图公网 URL 时直接作为视频输入
- [x] **视频 provider 切换** — agnes（API 直出）/ doubao（手动复制）/ comfyui（预留）
- [x] **修复 AgnesImageClient response_format 位置 bug** — 按文档移入 extra_body
- [x] **H3 模式实施（v0.12.0）** — 叙事驱动的 MiniMax H3 规范分镜生成，与标准模式并存
  - [x] Step 1: StoryboardFrame 新增 H3 字段（shot_label/cut_timestamp/integrated_multimodal_description/overall_soundscape/non_diegetic_music）
  - [x] Step 2: prompt_loader H3 生成函数（_load_few_shot + get_h3_system_prompt/user_prompt/plan_prompt/frame_prompt/copy_prompt）
  - [x] Step 3: storyboard.py 新增 generate_storyboard_h3()（plan→frame→audio 三阶段，cut_timestamp 代码累计计算）
  - [x] Step 4: UI 工具栏模式切换下拉框（标准/H3），Worker 按 mode 分流
  - [x] Step 5: FrameCard H3 字段展示（shot_label/cut_timestamp 标签 + 多模态描述 + 全片音频区域，空字段不显示）
  - [x] Step 6: few-shot 示例注入（按质感从 few_shot_extracted.json 读取 3 条，附格式警告）
  - [x] Step 7: 集成测试 + 文档更新（标准模式回归验证通过）

## 进行中
- [ ] 评分系统 UI 集成（生成后自动评分+修正建议展示）
- [ ] V2 两步生成实测验证（预设驱动 vs 旧 LLM 自由设计）
- [ ] H3 模式端到端实测（需 LLM API 调用，验证生成质量）
- [ ] H3 导演台脚本 → ComfyUI 实际粘贴验证
- [ ] 方案 A：ComfyUI API 自动提交 segments_json

## 待办
- [ ] 口味标签/负向词的端到端验证
- [ ] UI 小屏幕滚动体验优化
- [ ] 反馈记录驱动的模板自动优化
- [ ] 根据目标模型动态切换 video prompt 模板（豆包/可灵/Runway 各有偏好）
- [ ] 增加光影氛围字段（从场景设定推导或 LLM 生成）
- [ ] 增加负面提示字段（为支持负面提示的模型生成对应负面提示）

## 已知问题
- LLM 流式输出偶尔截断 → 已加固容错，待观察
- 评分系统尚未集成 UI

## 关键文件
| 文件 | 职责 |
|------|------|
| core/generation_manager.py | 统一生成管理器（图片+视频） |
| core/motion_sketch.py | 运动示意图（分镜蓝图）生成：程序化绘制 + Agnes AI 双模式 |
| core/video_client.py | Agnes AI 视频客户端（被 GenerationManager 调用） |
| core/llm_client.py | LLM 客户端 + JSON 提取容错 |
| core/storyboard.py | 分镜生成（V2 两步生成 + 物理状态摘要 + 单帧重生成） |
| core/templates.py | 风格模板 + JSON 加载 |
| core/prompt_loader.py | 提示词加载器（模块化组装 system prompt） |
| core/product_parser.py | 商品解析 + Markdown 回写 |
| core/scoring.py | 镜头模板评分系统 |
| camera_templates/camera_templates.yaml | 镜头模板库（9 模板：3快+3慢+3创意） |
| prompts/modules/core.md | 系统提示词核心（含动态表现力 4 层体系） |
| prompts/modules/frame_prompt.md | 逐帧生成提示词（含物理状态连续性约束） |
| prompts/modules/texture_*.md | 4 个质感模块（各含微动态+情绪氛围词汇表） |
| prompts/doubao_video_prompt.md | 豆包视频提示词模板（自然语言格式） |
| docs/video_model_prompt_research.md | 视频模型 prompt 最佳实践调研报告 |
| ui/main_window.py | 主窗口界面 |
| docs/h3-mode-design.md | H3 模式设计文档（已实施） |
| prompts/h3_system_prompt.md | H3 模式系统提示词（含 H3 规范 + few-shot 注入） |
| prompts/few_shot_extracted.json | 按质感分类的 few-shot 示例（4 类各 8 条） |

## 最近变更

### v0.13.0 (2026-08-12) — H3 模式重构：三模式 + 导演台脚本导出
- **三模式架构**: 模式下拉框从「标准/H3」扩展为「标准模式/H3 普通/H3 导演台」三个选项
- **H3 系统提示词精简**: h3_system_prompt.md 重写为仅生成 H3 原生字段（integrated_multimodal_description + audio），移除 image_prompt/camera_motion/motion_hint/video_prompt 等旧字段要求
- **H3 帧提示词精简**: get_h3_frame_prompt 更新为仅请求 H3 原生字段（多模态描述+中文翻译+动作相位+简述），不再要求派生旧字段
- **导演台脚本导出**: get_h3_copy_prompt 新增 fmt="director" 模式，输出 `[Shot N] At MM:SS.mmm, description` 连续文本 + `overall_soundscape:` / `non_diegetic_music:` 后缀，可直接粘贴到 ComfyUI H3 导演台文本界面
- **H3 按钮菜单扩展**: 从中文/英文两选项扩展为四选项（普通提示词中文/英文 + 导演台脚本中文/英文）
- **FrameCard 空字段优化**: 图片提示词/镜头运动/画面动态字段为空时不再显示占位符"—"，H3 模式下界面更干净
- **H3 系统提示词回退简化**: 移除旧的模块化组装+H3 后缀回退逻辑，改为最小化回退

### v0.12.0 (2026-08-10) — H3 模式实施（叙事驱动的 MiniMax H3 规范）
- **双模式并存**: 标准模式（预设驱动）+ H3 模式（叙事驱动），UI 工具栏可切换，默认标准模式
- **StoryboardFrame 扩展**: 新增 shot_label / cut_timestamp / integrated_multimodal_description / _cn / overall_soundscape / non_diegetic_music（标准模式下为空，不影响现有流程）
- **prompt_loader H3 函数**: get_h3_system_prompt（含 few-shot 注入）/ get_h3_user_prompt / get_h3_plan_prompt / get_h3_frame_prompt / get_h3_copy_prompt
- **generate_storyboard_h3()**: plan（叙事弧）→ frame（叙事优先，先写 integrated_multimodal_description 再派生其他字段）→ audio（全片音频）三阶段；cut_timestamp 由代码按 duration 累计计算
- **UI 展示**: FrameCard 新增 H3 字段展示（紫色标签 + 多模态描述 + 全片音频区域），空字段自动不显示
- **few-shot 注入**: 从 few_shot_extracted.json 按质感读取 3 条示例注入 system prompt，附格式警告（不模仿示例格式）
- **标准模式回归验证**: get_system_prompt 不注入 few-shot，generate_storyboard_v2 逻辑不变

### v0.11.0 (2026-08-08) — 运动示意图（分镜蓝图）
- 新增 `core/motion_sketch.py`：从分镜字段启发式提取主体/方向/速度/粒子/镜头 → 生成黑白线稿运动蓝图
- 三种模式：`programmatic`（Pillow 本地绘制）/ `ai`（Agnes 图片 API 按提示词模板）/ `hybrid`（本地底稿 + Agnes 图生图拿公网 URL）
- 示意图只画主体轮廓，不给产品外观细节（标注一确认）
- UI：每帧卡片新增 ✏️ 按钮 + 示意图缩略图；图生视频时优先用示意图公网 URL 作为输入图
- 设置：视频 provider 扩展为 agnes / doubao / comfyui 三选一；新增「运动示意图」设置组（启用/模式/画布尺寸/视频输入）
- 修复 `AgnesImageClient.generate_image` 把 `response_format` 放在顶层的问题（文档要求放 `extra_body`）

### v0.10.0 (2026-08-06) — 商业镜头预设库驱动架构
- **核心改造**: 从 LLM 自由设计运镜 → 商业镜头预设锁定运镜/角度/光线/速度/过渡
- 新增 `prompts/modules/shot_presets.md` — 12 个商业食品广告标准镜头预设（3 开场+6 中间+3 结尾）
- 新增 `prompt_loader.py` 中 `SHOT_PRESETS` 字典 + `TEXTURE_PRESET_MATRIX` 质感-预设矩阵 + `get_preset_sequence()` 预设序列生成
- 改造 `plan_prompt.md` — plan 阶段从预设库选镜头，不再自由设计运镜
- 改造 `frame_prompt.md` — LLM 只填产品变量，运镜/角度/光线/速度曲线/过渡由预设锁定
- 改造 `core.md` — 删除 LLM 自主设计运镜指令，改为预设驱动
- 改造 `storyboard.py` — generate_storyboard_v2 自动计算预设序列，强制覆盖 plan 的运镜和过渡字段
- 改造 `regenerate_frame` — 单帧重生成也传入预设参数
- 预设按质感+帧位自动分配: 酥脆→碎裂开场+快切中段+全景结尾，软糯→慢推开场+形变中段+特写结尾

### v0.9.5 (2026-08-04) — 视频提示词修复
### v0.9.4 (2026-08-03) — P0-P3 动画表现力增强
### v0.9.3 (2026-08-03) — 镜头模板扩充+帧间连贯性+动态表现力+运动指令语义
- **08-04**: LLM 空响应修复（v0.9.4→v0.9.5）：
  - 第6帧 LLM 返回空内容（Agnes API 偶发性空返回）→ chat_json 新增 max_retries=2 自动重试
  - generate_frame_detail 新增空结果检测警告
  - 验证 v0.9.4 修复效果：箭头全部清除 ✅、精确数值清除 ✅、camera_motion 自然语句 ✅、video_prompt 词数仍有超标（86词 vs 70词限制）
- **08-03 (晚)**: 视频提示词质量修复（v0.9.3→v0.9.4）：
  - doubao_video_prompt.md 从 2000+ 字精简到 180 字（删除冗余 motion_phase 说明和运动规范）
  - get_doubao_video_prompt 注入风格参数（style_name/style_words/camera_words），UI 同步传入
  - frame block 从 6 行键值对精简为 3 行紧凑格式
  - frame_prompt.md 新增 motion_phase 与 motion_hint 一致性强约束
  - video_prompt 词数限制从 40-80 收紧到 40-70 词
  - 禁止 video_prompt 写精确秒数/角度数值
  - image_prompt_cn 新增技术术语翻译参考表
  - core.md + camera_templates.yaml 全部消除 → 箭头（103 处）
- **08-03 (下午)**: P0-P3 动画表现力 4 方向增强全部完成：
  - P0 镜头模板扩充：3→9 个模板（+品味揭示/环绕展示/微距焦点变换/滑动变焦冲击/俯拍旋转/移轴微缩）
  - P1 帧间连贯性：storyboard.py 上下文传递从 description+camera_motion_cn 升级为物理状态摘要（6 维信息），frame_prompt.md 新增 5 项物理状态连续性约束
  - P2 动态表现力：core.md 新增 4 层动态表现力体系（主体动作/微表情/环境互动/情绪氛围）+ 质感选择规则表，4 个质感模块各新增微动态词汇表+情绪氛围词汇表
  - P3 运动指令语义：video_prompt 从 `[初始]→[运动]→[镜头]→[速度]→[结束]` 箭头格式改为自然语言连贯描述（适配豆包/可灵/Runway 等主流模型），新增画质词+约束词，doubao_video_prompt.md 新增禁止动态+画质约束段，camera_templates.yaml 中 3 个旧模板 video_prompt 同步更新
- **07-25**: transition 字段丢失修复 + V2 实测通过
- **07-24**: 镜头模板库 + 评分系统
- **07-22**: 单帧重新生成功能
- **07-20**: 统一生成接口 + Agnes 集成 + 两步生成 + 模块化提示词
- **07-19**: 视频提示词精细化（VP-P0~P2 全部完成）
- **07-18**: 视频提示词增强 + 视频方向输入框 + 商品列表修复
- **07-17**: 提示词模板化 + 背景音乐 + 冲击强度/节奏策略
- **07-16**: 刷新按钮 + 商品信息回写 + 豆包视频提示词修改
- **07-15**: 项目创建，基础分镜生成
