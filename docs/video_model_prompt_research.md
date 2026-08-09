# 视频生成模型 Prompt 最佳实践调研报告

> 调研时间：2026-08-03  
> 调研目标：为 StoryFrame 项目的 video_prompt 字段优化提供依据，目标模型为豆包（Seedance）视频生成 API，同时兼顾可灵（Kling）、Runway Gen-3、Luma Dream Machine、Pika 等主流图生视频模型。

---

## 一、各模型 Prompt 格式偏好对比

### 1. 豆包 / Seedance 2.0（火山引擎）

**官方公式（S-A-C-S-C）：**

```
主体(Subject) + 动作(Action) + 运镜(Camera) + 风格(Style) + 约束(Constraints)
```

完整版公式：
```
主体 + 动作 + 场景 + 光影 + 镜头语言 + 风格 + 画质 + 约束
```

**核心特点：**
- 对**动作描述**的理解能力极强，但要求用词精准
- 偏好**缓慢、连贯、自然**的动作词（"缓慢转身"、"轻轻抬手"），避免"夸张、高速、剧烈"
- 支持**时间顺序叙事**（分镜写法），如"开头近景特写脸部，慢慢拉远成全景"
- **必须显式加约束词**：面部稳定不变形、人体结构正常、动作自然流畅
- 运镜术语识别能力强，支持英文专业术语（Dolly In, Orbit, Tracking, Pull Back 等）
- 支持中英文混合 prompt

**官方文档：** 字节飞书文档 `bytedance.larkoffice.com/wiki/A5RHwWhoBiOnjukIIw6cu5ybnXQ`

**示例：**
```
一位年轻女生在海边慢走，微风拂动头发，微笑看向镜头，黄昏暖光，中景，缓慢推镜，画面流畅稳定，4K高清，电影感，面部清晰不变形，人体结构正常，细节丰富。
```

**图生视频专用模板：**
```
基于参考图保持人物样貌与服装一致，[动作描述]，动作缓慢自然流畅，不僵硬不变形，稳定运镜，高清细节，电影质感。
```

### 2. 可灵 Kling（快手）

**官方公式：**

```
提示词 = (镜头语言 + 光影) + 主体(主体描述) + 主体运动 + 场景(场景描述) + (氛围)
```

图生视频简化版：
```
提示词 = 主体 + 运动, 背景 + 运动
```

**核心特点：**
- 最核心三要素：**主体 + 运动 + 场景**
- 镜头语言与运镜控制是**分离的**（有独立的运镜控制参数）
- 主体描述鼓励用**多个短句列举**（发型发色、服饰穿搭、五官形态、肢体姿态）
- 运动状态不宜过于复杂，符合 5s 视频可展现的范围
- 支持中文自然语言描述
- 对"微距、特写、浅焦、慢动作、缩时摄影、跟随、穿越、前推、后拉、俯视、仰拍"等中文运镜术语理解良好

**示例：**
```
中景拍摄、背景虚化、氛围光照，一只大熊猫戴着黑框眼镜在咖啡厅看书，书本放在桌子上，桌子上还有一杯咖啡、冒着热气，旁边是咖啡厅的窗户，电影级调色
```

### 3. Runway Gen-3 Alpha

**官方公式：**

```
[camera movement]: [establishing scene]. [additional details].
```

**核心特点：**
- **英文优先**，结构化程度最高
- 冒号分隔运镜和场景描述，句号分隔附加细节
- 关键词分类明确：相机风格、灯光、移动、速度、运动类型、风格与审美
- 支持 Motion Brush、高级摄像机控制、导演模式等独立控制工具
- Gen-3 Alpha 经过**高度描述性、时间密集的字幕训练**，能理解复杂的时间序列指令
- 支持双向关键帧控制（起始+终点图像）

**官方提示词指南：** `help.runwayml.com/hc/en-us/articles/30586818553107-Gen-3-Alpha-Prompting-Guide`

**示例：**
```
Low angle static shot: The camera is angled up at a woman wearing all orange as she stands in a tropical rainforest with colorful flora. The dramatic sky is overcast and gray.
```

```
An extreme close-up shot of an ant emerging from its nest. The camera pulls back revealing a neighborhood beyond the hill.
```

### 4. Luma Dream Machine

**格式偏好：** 自然语言描述

**核心特点：**
- **无需专业提示词**，自然对话式描述即可
- 强调"描述性提示"：场景 + 主体 + 动作 + 环境
- 支持图生视频、文生视频、关键帧控制、视频扩展和循环
- 自动匹配摄像机运动，无需显式指定运镜指令（但可以写）
- 对中文支持一般，英文效果更佳
- 擅长生成"流畅的运动、电影摄影和戏剧效果"

**示例：**
```
A Song Dynasty scholar stands in an ancient Song Dynasty temple, holding an oil-paper umbrella in his hand and carrying a backpack, looking around.
```

### 5. Pika

**格式偏好：** 自然语言 + 参数标签

**核心特点：**
- 支持纯自然语言描述
- 也支持结构化参数：`-gs` (guidance scale), `-neg` (负面提示), `-ar` (宽高比), `-seed`
- 镜头控制通过特定参数实现（如 `-camera zoom in`）
- 风格选择通过参数指定（3D动画、动漫、电影等）
- 图生视频可不输入 prompt，仅上传图片
- 1.5 版本引入"Pikaffects"特效库

**示例：**
```
A cat wearing space suit, 3D -gs 12 -neg "morphing, distorted, blurry" -ar 16:9
```

---

## 二、Prompt 格式偏好对比表

| 维度 | 豆包/Seedance 2.0 | 可灵 Kling | Runway Gen-3 | Luma Dream Machine | Pika |
|------|-------------------|------------|--------------|---------------------|------|
| **语言偏好** | 中英文混合 | 中文优先 | 英文优先 | 英文优先 | 英文优先 |
| **格式类型** | 结构化公式(S-A-C-S-C) | 结构化公式(主体+运动+场景) | 结构化([运镜]: [场景]. [细节].) | 自然语言 | 自然语言+参数标签 |
| **运镜指令** | 支持中英文术语 | 中文术语+独立运镜控制 | 英文术语+独立摄像机控制 | 自动匹配，可显式写 | 参数控制(-camera) |
| **动作描述** | 极重视，需缓慢连贯 | 重视，不宜复杂 | 重视，时间序列描述 | 自然描述即可 | 自然描述即可 |
| **约束词** | 必须显式加(不变形/不僵硬) | 可选 | 通过负面提示 | 不需要 | 通过-neg参数 |
| **画质词** | 必加(4K/超高清/电影质感) | 可选(氛围) | 通过风格关键词 | 不需要 | 可选 |
| **时间/分镜** | 支持叙事顺序 | 不支持 | 支持(时间密集训练) | 部分支持 | 不支持 |
| **图生视频** | 需加"基于参考图保持一致" | 主体+运动,背景+运动 | 上传图片+动作描述 | 上传图片+描述 | 上传图片即可 |
| **负面提示** | 在约束中写明 | 不支持 | 不支持 | 不支持 | 支持(-neg) |

---

## 三、运镜指令理解能力对比

| 运镜指令 | 豆包/Seedance | 可灵 | Runway Gen-3 | Luma | Pika |
|----------|---------------|------|--------------|------|------|
| **Push-in / Dolly In** | ✅ 优秀 | ✅ 优秀 | ✅ 优秀 | ✅ 良好 | ✅ 良好 |
| **Pull Back / Dolly Out** | ✅ 优秀 | ✅ 优秀 | ✅ 优秀 | ✅ 良好 | ✅ 良好 |
| **Orbit / 环绕** | ✅ 优秀 | ✅ 良好 | ✅ 优秀 | ⚠️ 一般 | ⚠️ 一般 |
| **Tracking / 跟拍** | ✅ 优秀 | ✅ 优秀 | ✅ 优秀 | ✅ 良好 | ✅ 良好 |
| **Pan / 横移 (Truck)** | ✅ 优秀 | ✅ 优秀 | ✅ 优秀 | ✅ 良好 | ✅ 良好 |
| **Tilt / 俯仰** | ✅ 良好 | ✅ 良好 | ✅ 优秀 | ⚠️ 一般 | ⚠️ 一般 |
| **Whip Pan / 甩镜头** | ⚠️ 一般 | ⚠️ 一般 | ✅ 良好 | ⚠️ 一般 | ❌ 较差 |
| **Crane / 升降** | ✅ 良好 | ✅ 良好 | ✅ 优秀 | ✅ 良好 | ⚠️ 一般 |
| **Handheld / 手持** | ✅ 良好 | ✅ 良好 | ✅ 优秀 | ✅ 良好 | ⚠️ 一般 |
| **FPV Drone** | ✅ 良好 | ⚠️ 一般 | ✅ 优秀 | ✅ 良好 | ❌ 较差 |
| **Macro / 微距** | ✅ 优秀 | ✅ 优秀 | ✅ 优秀 | ✅ 良好 | ✅ 良好 |
| **低角度/仰拍** | ✅ 优秀 | ✅ 优秀 | ✅ 优秀 | ✅ 良好 | ✅ 良好 |
| **俯拍/航拍** | ✅ 优秀 | ✅ 优秀 | ✅ 优秀 | ✅ 良好 | ✅ 良好 |

**关键发现：**
- 豆包/Seedance 和 Runway Gen-3 对运镜术语理解能力最强
- 可灵对中文运镜术语理解优秀，英文术语也支持
- Luma 倾向于自动匹配运镜，显式指定效果一般
- Pika 的运镜控制主要依赖参数，对复杂运镜支持较弱
- **所有模型都建议：运镜写稳、写简单，复杂运镜交给后期剪辑**

---

## 四、对 StoryFrame 当前 video_prompt 格式的优化建议

### 当前格式
```
[初始状态] → [运动轨迹] → [镜头运动] → [速度节奏] → [结束状态]
```

### 问题分析

1. **箭头分隔符（→）不是任何模型的原生格式**：所有主流模型都用自然语言或冒号/逗号分隔，箭头可能被模型误解为文字内容
2. **缺少主体描述**：当前格式没有显式的主体外观描述（服装、姿态等），这在豆包和可灵中是关键要素
3. **缺少约束词**：豆包/Seedance 强制要求"不变形、不僵硬、面部稳定"等约束，当前格式缺失
4. **缺少画质/风格词**：所有模型都受益于画质描述（4K、电影质感等）
5. **速度节奏独立成段过于碎片化**：速度应融入动作描述中，而非独立段落
6. **缺少场景/环境描述**：当前格式没有场景细节
7. **缺少光影描述**：光影是提升画面质感的关键元素

### 推荐新格式

```
[主体描述] 在 [场景描述] 中，[初始状态]，[运动动作（含速度节奏）]，[镜头运动]，[光影氛围]，[结束状态]。[画质风格词]，[约束词]。
```

**具体示例：**
```
一位穿白色连衣裙的年轻女生在阳光斑驳的林间小道上，初始站定微笑，开始缓慢向前行走，微风轻拂裙摆，镜头平稳跟拍并缓慢推近，暖色调逆光，丁达尔光效，最终停下回望镜头。4K高清，电影质感，画面流畅稳定，面部清晰不变形，人体结构正常。
```

### 格式调整要点

| 调整项 | 旧格式 | 新格式 | 原因 |
|--------|--------|--------|------|
| 分隔符 | `→` 箭头 | 逗号/句号自然语言 | 所有模型都用自然语言 |
| 主体描述 | 无 | 开头明确主体外观 | 豆包/可灵的核心要素 |
| 场景描述 | 无 | 加入环境细节 | 所有模型的核心要素 |
| 速度节奏 | 独立段落 | 融入动作描述 | 避免碎片化，模型更好理解 |
| 光影氛围 | 无 | 新增 | 提升画面质感 |
| 画质风格 | 无 | 结尾添加 | 所有模型受益 |
| 约束词 | 无 | 结尾添加 | 豆包/Seedance 强制要求 |
| 镜头运动 | 独立段落 | 融入自然语言 | 更符合模型理解方式 |

---

## 五、推荐的通用 Prompt 模板（兼容多模型）

### 模板 A：图生视频通用模板（推荐 StoryFrame 使用）

```
{subject_description}在{scene_description}中，{initial_state}，{motion_description}，{camera_movement}，{lighting_atmosphere}，{end_state}。{quality_style}，{constraints}。
```

**字段说明：**

| 字段 | 说明 | 示例 |
|------|------|------|
| `subject_description` | 主体外观描述（服装、发型、姿态） | 一位穿白色连衣裙的年轻女生 |
| `scene_description` | 场景/环境描述 | 阳光斑驳的林间小道 |
| `initial_state` | 初始状态 | 站定微笑 |
| `motion_description` | 运动动作 + 速度节奏 | 缓慢向前行走，微风轻拂裙摆 |
| `camera_movement` | 镜头运动 | 镜头平稳跟拍并缓慢推近 |
| `lighting_atmosphere` | 光影氛围 | 暖色调逆光，丁达尔光效 |
| `end_state` | 结束状态 | 最终停下回望镜头 |
| `quality_style` | 画质与风格 | 4K高清，电影质感 |
| `constraints` | 约束词（豆包必需） | 画面流畅稳定，面部清晰不变形 |

### 模板 B：豆包/Seedance 专用优化版

```
主体(S)：{subject_description}，外观与参考图保持一致。
动作(A)：{initial_state}，{motion_description}，{end_state}。
运镜(C)：{camera_movement}，稳定流畅。
风格(S)：{quality_style}，{lighting_atmosphere}。
约束(C)：面部清晰不变形，人体结构正常，动作自然不僵硬，无模糊无重影。
```

### 模板 C：Runway Gen-3 兼容版（英文）

```
{camera_movement}: {subject_description} in {scene_description}. {initial_state}, {motion_description}, {end_state}. {lighting_atmosphere}, {quality_style}.
```

### 模板 D：可灵兼容版

```
{镜头语言}，{光影}，{subject_description}{主体描述}，{initial_state}，{motion_description}，{end_state}，{scene_description}，{氛围}。
```

### 模板 E：极简通用版（最低兼容性）

```
{subject_description}在{scene_description}中{motion_description}，{camera_movement}，{end_state}。
```

---

## 六、StoryFrame 实施建议

### 短期（立即可做）

1. **将 video_prompt 的 `→` 分隔符改为自然语言逗号句号**
2. **在 prompt 生成时增加主体描述字段**（从角色设定中提取服装、发型等）
3. **在 prompt 尾部固定追加约束词和质量词**
4. **将速度节奏融入动作描述**，不再独立成段

### 中期（下个迭代）

1. **根据目标模型动态切换模板**：检测到豆包 API 用模板 B，Runway 用模板 C，可灵用模板 D
2. **增加光影氛围字段**：从场景设定中推导或由 LLM 生成
3. **增加负面提示字段**：为支持负面提示的模型（Pika、豆包）生成对应的负面提示

### 长期

1. **A/B 测试不同模板的生成效果**，用实际视频质量反馈优化模板
2. **建立运镜指令词库**：中英文对照，按效果分级
3. **根据豆包 API 的实际返回结果迭代 prompt 格式**

---

## 七、参考来源

| 来源 | 链接 |
|------|------|
| Seedance 2.0 官方使用手册 | bytedance.larkoffice.com/wiki/A5RHwWhoBiOnjukIIw6cu5ybnXQ |
| Seedance 2.0 提示词终极指南 | blog.csdn.net/chenbo980/article/details/158178821 |
| 可灵AI官方提示词公式 | zhuanlan.zhihu.com/p/714829166 |
| 可灵AI提示词公式详解 | blog.csdn.net/u011886447/article/details/140592170 |
| Runway Gen-3 官方提示词指南 | help.runwayml.com/hc/en-us/articles/30586818553107 |
| Runway Gen-3 开放公告 | cloud.tencent.com/developer/article/2455431 |
| AI视频运镜描述大全（上） | toutiao.com/article/7447051116666012175 |
| AI视频运镜描述大全（下） | toutiao.com/article/7447071192785175075 |
| Luma Dream Machine 官方 | lumalabs.ai/dream-machine |
| Pika 使用指南 | blog.csdn.net/qq_28550263/article/details/134657306 |
| Seedance 2.0 镜头控制实战手册 | blog.csdn.net/CeshirenTester/article/details/158500660 |

---

## 附录：运镜术语中英文对照表

| 中文 | 英文 | 适用场景 |
|------|------|----------|
| 缓慢推镜 | Dolly In / Push-in | 聚焦细节，强化情感 |
| 缓慢拉远 | Dolly Out / Pull Back | 渐入全景，展示环境 |
| 平稳横移 | Truck / Pan | 场景展开，引导视线 |
| 环绕拍摄 | Orbit | 展示主体全貌 |
| 跟拍 | Tracking Shot | 跟随主体运动 |
| 升降拍摄 | Crane Shot | 空间层次变化 |
| 仰拍 | Low-angle Shot | 强化压迫感/高大感 |
| 俯拍 | High-angle Shot / Drone | 全局视角 |
| 特写 | Close-up / Macro | 细节展示 |
| 中景 | Medium Shot | 人物半身 |
| 远景 | Wide Shot / Establishing | 环境建置 |
| 手持拍摄 | Handheld | 纪实感，紧张氛围 |
| FPV穿越 | FPV Drone Shot | 沉浸式，高速运动感 |
| 慢动作 | Slow Motion | 强化瞬间，情感渲染 |
| 延时摄影 | Time-lapse | 时间流逝感 |
