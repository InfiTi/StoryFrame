# H3 模式设计文档

> 创建: 2026-08-10 | 实施: 2026-08-10 | 状态: 已实施（v0.12.0，Step 1-7 全部完成）

## 背景

StoryFrame 现有分镜生成模式（以下简称"标准模式"）让 LLM 一次性/两步生成 15+ 个独立字段（image_prompt、camera_motion、video_prompt 等），各字段之间缺乏叙事连贯性。

MiniMax H3 的 skill（`h3-prompt-writing`）提供了一套不同的生成哲学：以 `integrated_multimodal_description` 为核心，画面+动作+声音+镜头+时间线一体化叙事，再从中派生其他字段。

**目标**：在 StoryFrame 中新增 H3 生成模式，与标准模式并存，UI 可切换。两种模式共享帧数据结构和 UI 卡片，只在 system prompt 和生成策略上分叉。

## 现有代码结构（必读）

### 生成流程

```
ui/main_window.py
  └─ _generate_script()              # 入口，读取 UI 参数
      └─ GenerateScriptWorker         # QThread Worker
          └─ generate_storyboard_v2() # V2 两步生成（plan → 逐帧）
              或 generate_storyboard()  # V1 一次性生成（回退）
```

### 关键文件

| 文件 | 职责 |
|------|------|
| `ui/main_window.py` | 主窗口、按钮、Worker 类 |
| `ui/storyboard_view.py` | 帧卡片展示（FrameCard） |
| `core/storyboard.py` | 分镜生成逻辑（V1/V2） |
| `core/prompt_loader.py` | 提示词组装（system/user/copy） |
| `core/llm_client.py` | LLM 客户端（流式 + JSON 容错） |
| `prompts/system_prompt.md` | 标准模式 system prompt |
| `prompts/modules/core.md` | 标准模式核心模块（预设驱动 + 动态表现力） |
| `prompts/modules/frame_prompt.md` | V2 逐帧生成 prompt |
| `prompts/modules/plan_prompt.md` | V2 plan 阶段 prompt |
| `prompts/h3_system_prompt.md` | H3 模式 system prompt（已存在，需改造） |
| `prompts/h3_user_prompt.md` | H3 模式 user prompt（已存在，需改造） |
| `prompts/few_shot_extracted.json` | 按质感分类的 few-shot 示例（已存在，未使用） |
| `docs/h3-ref/h3-prompt-writing/` | H3 skill 参考文档 |
| `docs/h3-ref/minimalist-product-ad-generator/` | 极简产品广告 skill 参考文档 |

### StoryboardFrame 数据结构

`core/storyboard.py` 中的 `StoryboardFrame` 是 dataclass，当前字段：
- frame, duration, motion_phase
- image_prompt, image_prompt_cn
- camera_motion, camera_motion_cn
- motion_hint, motion_hint_cn
- video_prompt, video_prompt_cn
- transition, description

H3 模式需要新增的字段（旧模式下为空字符串）：
- shot_label: `[Shot N]` 格式
- cut_timestamp: `At MM:SS.mmm,` 格式
- integrated_multimodal_description / _cn: 多模态综合描述
- overall_soundscape: 全片环境音
- non_diegetic_music: 背景音乐

## 兼容性分析

### UI 展示端（storyboard_view.py）

`FrameCard` 用 `frame_data.get("字段名", "")` 取值，**不关心字段来源**。

| 字段 | 标准模式 | H3 模式 | UI 已展示 |
|------|---------|---------|----------|
| image_prompt / _cn | ✅ | ✅ | ✅ |
| camera_motion / _cn | ✅ | ✅ | ✅ |
| motion_hint / _cn | ✅ | ✅ | ✅ |
| video_prompt / _cn | ✅ | ✅ | ✅ |
| description | ✅ | ✅ | ✅ |
| transition | ✅ | ✅ | ✅ |
| shot_label | ❌ | ✅ | ❌ 需加 |
| cut_timestamp | ❌ | ✅ | ❌ 需加 |
| integrated_multimodal_description / _cn | ❌ | ✅ | ❌ 需加 |
| overall_soundscape | ❌ | ✅（全片级） | ❌ 需加 |
| non_diegetic_music | ❌ | ✅（全片级） | ❌ 需加 |

**结论**：UI 只需小幅扩展，加几个可选展示区域。标准模式这些字段为空，不显示。

### 复制按钮

现有三套复制按钮（豆包图片/豆包视频/H3提示词）都通过 `frame_data.get()` 取值，H3 模式生成的帧同样有 `image_prompt` 和 `video_prompt`，豆包按钮照常工作。

**结论**：复制链路无需改动。

## 实施计划（小步提交）

### Step 1: 数据结构扩展

**文件**: `core/storyboard.py`
**改动**:
- `StoryboardFrame` dataclass 新增 5 个字段（默认空字符串）
- `Storyboard` 新增 `overall_soundscape` 和 `non_diegetic_music` 属性
- `to_dict()` 自动包含新字段（`dataclasses.asdict` 已处理）

**验证**: 旧模式生成的帧新字段为空，不影响现有展示和导出
**提交信息**: `feat: StoryboardFrame 新增 H3 字段（shot_label/cut_timestamp/integrated_multimodal_description/soundscape/music）`

### Step 2: prompt_loader H3 生成函数

**文件**: `core/prompt_loader.py`
**改动**:
- 改造 `get_h3_system_prompt()`：注入 few-shot 示例（从 `few_shot_extracted.json` 按质感读取）
- 改造 `get_h3_user_prompt()`：确保与标准模式 user prompt 参数一致
- 新增 `get_h3_frame_prompt()`：V2 逐帧生成时的 H3 frame prompt（核心是先写 integrated_multimodal_description 再派生其他字段）
- 新增 `get_h3_plan_prompt()`：V2 plan 阶段的 H3 prompt

**验证**: 函数可调用，返回非空字符串
**提交信息**: `feat: prompt_loader 新增 H3 生成策略（few-shot 注入 + 叙事优先的 frame prompt）`

### Step 3: storyboard.py H3 生成逻辑

**文件**: `core/storyboard.py`
**改动**:
- 新增 `generate_storyboard_h3()`：H3 模式的 V2 两步生成
  - plan 阶段：用 `get_h3_plan_prompt()`
  - frame 阶段：用 `get_h3_frame_prompt()`，LLM 先写 integrated_multimodal_description，再派生其他字段
  - audio 阶段：生成全片 overall_soundscape + non_diegetic_music
- 兼容 V2 的回调接口（on_plan_chunk / on_frame_chunk / on_frame_done / on_stage）

**验证**: 可独立调用，返回 Storyboard 对象
**提交信息**: `feat: storyboard.py 新增 generate_storyboard_h3()（叙事优先的两步生成）`

### Step 4: UI 模式切换

**文件**: `ui/main_window.py`
**改动**:
- 工具栏新增模式切换下拉框（标准模式 / H3 模式）
- `GenerateScriptWorker.__init__` 新增 `mode` 参数
- `_generate_script()` 根据 mode 选择 `generate_storyboard_v2()` 或 `generate_storyboard_h3()`
- 默认选标准模式（用户不主动切换则无感）

**验证**: 切换到 H3 模式可触发生成，标准模式行为不变
**提交信息**: `feat: UI 新增生成模式切换（标准/H3）`

### Step 5: UI 帧卡片 H3 字段展示

**文件**: `ui/storyboard_view.py`
**改动**:
- `FrameCard` 新增 H3 字段展示区域（shot_label + cut_timestamp 在帧号旁）
- 新增"多模态描述"区域（integrated_multimodal_description / _cn）
- 新增"全片音频"区域（overall_soundscape + non_diegetic_music，只在最后一帧显示）
- 所有新区域用 `frame_data.get("xxx", "")`，空则不显示

**验证**: H3 模式生成的帧卡片显示新字段，标准模式不显示
**提交信息**: `feat: 帧卡片新增 H3 字段展示（多模态描述/音频/标签）`

### Step 6: few-shot 示例注入

**文件**: `core/prompt_loader.py`（进一步完善）
**改动**:
- `_load_few_shot(product_texture)` 函数：从 `few_shot_extracted.json` 按质感读取 2-3 条示例
- 注入到 H3 system prompt 的 few-shot 段落
- 标准模式不注入（不影响）

**验证**: H3 system prompt 包含 few-shot 示例
**提交信息**: `feat: H3 模式注入 few-shot 示例（按质感分类）`

### Step 7: 集成测试 + 文档更新

**文件**: `STATUS.md`, `MEMORY.md`
**改动**:
- 更新 STATUS.md 到新版本
- 端到端验证：H3 模式生成 → 帧卡片展示 → 复制按钮
- 标准模式回归验证

**提交信息**: `docs: STATUS.md 更新 + H3 模式集成验证`

## 设计决策

### 为什么 H3 模式不删除 integrated_multimodal_description 的派生字段？

H3 的 `integrated_multimodal_description` 是叙事核心，但 StoryFrame 的下游消费者（豆包图片/视频复制、运动示意图提取）依赖 `image_prompt`、`video_prompt` 等独立字段。所以 H3 模式下，LLM 先写叙事描述，再从中派生独立字段——两种格式都产出，下游无需改动。

### 为什么不把 H3 作为标准模式的升级？

两种模式的生成哲学不同：
- 标准模式：预设驱动，字段独立填写，精细可控
- H3 模式：叙事驱动，一体化描述，连贯性优先

用户应该能根据目标模型选择：喂豆包用标准模式，喂 MiniMax H3 用 H3 模式。

### 为什么不改动 h3_system_prompt.md 和 h3_user_prompt.md？

这两个文件在 Step 1（commit 6b238a2）已经创建，内容基本可用。Step 2 在 prompt_loader 中改造组装逻辑，而不是改文件内容——这样回退容易，只改代码不改模板。

## 注意事项

- **每个 Step 是一次独立提交**，之间无强依赖（Step 3 依赖 Step 1+2，但 Step 4 不依赖 Step 3 的完整验证）
- **如果积分用完**，接手的 Agent 读这个文档 + STATUS.md 就能知道做到哪步、下一步做什么
- **不要一次性改多个 Step 的文件**，每个 Step 只改对应文件
- **标准模式不能受影响**，每个 Step 提交后都要确认旧流程正常
