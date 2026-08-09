# 运镜与动态表现路线图

> 创建: 2026-07-20 | 状态: 待启动

## 背景

视频提示词精细化路线图（VP-P0~P2）已全部完成，motion_hint 三要素、video_prompt 动作剧本、camera_motion 起止构图等基础设施就位。

但实际图生视频效果仍不理想，核心短板转移到**运镜与动态表现**层面：

1. **运镜与产品动态脱节** — camera_motion 和 motion_hint 是两个独立字段，LLM 可能给出"镜头静止 + 产品碎裂"这种浪费组合
2. **运镜词汇有限** — 只有 push-in/pull back/orbit/tilt，缺少 whip pan+freeze、speed ramp zoom、macro rack focus 等高效运镜
3. **没有运镜节奏编排** — 有帧时长和转场节奏约束，但没有运镜本身的节奏模式（开场冲击→中段加速→结尾收稳）
4. **速度曲线与帧时长未绑定** — 0.8s 帧用 ease-in 合理，2.5s 帧用 burst→freeze 浪费剩余时间

同时，图片提示词质量也需要提升，已有两个外部技能可参考。

此外，需要支持多模型推理（Codex 等），对比不同模型生成分镜脚本的质量差异。

## 改动清单

### VM-P0-1: 运镜-动态联动规则
- **优先级**: P0（效果最明显）
- **改动文件**: `prompts/system_prompt.md`
- **工作量**: 小（加规则章节 + 联动示例）
- **内容**:
  - 新增「运镜-动态联动规则」章节，约束 camera_motion 必须与 motion_hint 形成配合关系
  - 按质感分类给出推荐运镜组合：
    - 酥脆类碎裂 → fast push-in 放大碎裂瞬间
    - 软糯类拉丝 → slow tilt up 跟随拉丝方向
    - 液态类流出 → micro-pan 跟随流动方向
    - 冰爽类雾气 → slow pull back 揭示冷气扩散
  - 禁止"镜头静止 + 强动态"的浪费组合（除非有明确设计意图）
- **状态**: ✅ 已完成

### VM-P0-2: 运镜词汇库扩充
- **优先级**: P0
- **改动文件**: `prompts/system_prompt.md`
- **工作量**: 小
- **内容**:
  - 扩充运镜词汇表，从现有 4-5 种扩展到 12+ 种：
    - whip pan + freeze（甩镜定格）
    - speed ramp zoom（变速缩放）
    - macro rack focus（焦点变换）
    - dutch angle tilt（倾斜角度）
    - overhead rotation（俯拍旋转）
    - snap zoom out（急速拉远）
    - dolly zoom（滑动变焦 / Vertigo 效果）
    - arc shot（弧线运镜）
  - 每种运镜给出使用场景和与质感的适配关系
- **状态**: ✅ 已完成

### VM-P1-1: 运镜节奏编排规则
- **优先级**: P1
- **改动文件**: `prompts/system_prompt.md`
- **工作量**: 中
- **内容**:
  - 新增「运镜节奏编排」章节，约束整体运镜节奏模式：
    - 开场帧：snap zoom / push-in + hard stop（一击抓眼）
    - 中段帧：连续快切 + whip pan（节奏加速）
    - 结尾帧：slow pull back + hold（收稳定调）
  - 约束运镜节奏与帧时长的配合关系
  - 约束相邻帧运镜不应重复（避免视觉疲劳）
- **状态**: ✅ 已完成

### VM-P1-2: 速度曲线-帧时长绑定规则
- **优先级**: P1
- **改动文件**: `prompts/system_prompt.md`
- **工作量**: 小
- **内容**:
  - 约束速度曲线与帧时长的适配关系：
    - ≤1.0s → burst→freeze / snap（瞬间爆发）
    - 1.0-2.0s → ease-in / decelerate（渐变节奏）
    - >2.0s → ease-in-out / constant（持续运动）
  - 禁止短帧用慢速曲线、长帧用爆发曲线
- **状态**: ✅ 已完成

### VM-P2-1: 图片提示词描述框架（融入外部技能）
- **优先级**: P2
- **改动文件**: `prompts/system_prompt.md`
- **工作量**: 中
- **内容**:
  - 融合 `prompt-images` 技能的摄影语言规则
  - 建立 image_prompt 描述框架：主体 → 角度 → 质感 → 光影 → 背景 → 构图
  - 材质精确命名规范（brushed steel / matte aluminum / frosted glass 等）
  - 灯光方案完整描述规范（soft diffused studio lighting / Rembrandt lighting 等）
- **参考**: `~/.agents/skills/prompt-images/SKILL.md`
- **验证**: 生成分镜，检查 image_prompt 是否按框架结构描述
- **状态**: ✅ 已完成

### VM-P2-2: 图片提示词 few-shot 案例库
- **优先级**: P2（长线收益）
- **改动文件**: `prompts/system_prompt.md` 或新建 `prompts/few_shot_examples.md`
- **工作量**: 中
- **内容**:
  - 从 YouMind 库（14841 条）筛选 20-30 条食品/零食相关优质 prompt
  - 作为 few-shot 示例注入 system_prompt
  - 按质感分类：酥脆类 / 软糯类 / 液态类 / 冰爽类各 5-8 条
- **参考**: `~/.agents/skills/ai-image-prompts-skill/references/product-marketing.json`
- **验证**: 生成分镜，对比加入 few-shot 前后 image_prompt 质量差异
- **状态**: ✅ 已完成

### VM-P2-3: 多模型推理支持（Codex 接入）
- **优先级**: P2
- **改动文件**: `config.py`, `core/llm_client.py`, `ui/main_window.py`, `ui/settings_dialog.py`
- **工作量**: 中
- **内容**:
  - config.json 的 llm 部分改为支持多模型配置：
    ```json
    "llm": {
      "current": "qwen",
      "providers": {
        "qwen": { "base_url": "...", "api_key": "...", "model": "..." },
        "codex": { "base_url": "...", "api_key": "...", "model": "..." }
      }
    }
    ```
  - LLMClient 支持按 provider 名称切换
  - 设置界面增加模型选择（下拉或快捷切换）
  - 主窗口可快速切换当前使用的模型
  - 保留向后兼容（旧 config.json 自动迁移）
- **验证**: 配置两个模型，切换后生成分镜，对比输出质量
- **状态**: ✅ 已完成

## 执行顺序

```
VM-P0-1 → VM-P0-2 → VM-P1-1 → VM-P1-2 → VM-P2-1 → VM-P2-2 → VM-P2-3
```

- P0 两项可以一起做（都是改 system_prompt.md，一次改完）
- P1 两项也可以合并
- P2 三项独立推进，VM-P2-3（多模型）可与 P2-1/P2-2 并行

每完成一项：
1. 更新本文件的状态标记（⬜→✅）
2. 更新 STATUS.md 待办勾选
3. 在 STATUS.md 最近变更中记录
4. 测试验证

### VM-P3: 运动示意图（分镜蓝图）
- **优先级**: P1
- **改动文件**: `core/motion_sketch.py`（新增）、`ui/`、`config.py`
- **工作量**: 中
- **内容**:
  - 新增 `core/motion_sketch.py`：黑白线稿 + 手绘箭头 + 粒子符号，喂给视频模型理解"画面怎么动"
  - 三种生成模式：`programmatic`（本地 Pillow 绘制）/ `ai`（Agnes 图片 API）/ `hybrid`（本地底稿 + Agnes 图生图精修拿公网 URL）
  - 从 `motion_hint` / `video_prompt` / `camera_motion` 关键词启发式提取结构化运动信息，不依赖 LLM 额外输出
  - 示意图阶段只画主体轮廓，不给产品外观细节
  - UI：每帧卡片 ✏️ 按钮生成/更新示意图 + 缩略图预览；图生视频时优先用示意图公网 URL 作为输入
- **状态**: ✅ 已完成

## 变更记录

| 2026-07-20 | VM-P0-1 运镜-动态联动规则 | ✅ 已完成 |
| 2026-07-20 | VM-P0-2 运镜词汇库扩充 | ✅ 已完成 |
| 2026-07-20 | VM-P1-1 运镜节奏编排规则 | ✅ 已完成 |
| 2026-07-20 | VM-P1-2 速度曲线-帧时长绑定规则 | ✅ 已完成 |
| 2026-07-20 | VM-P2-1 图片提示词描述框架 | ✅ 已完成 |
| 2026-07-20 | VM-P2-2 图片提示词 few-shot 案例库 | ✅ 已完成 |
| 2026-07-20 | VM-P2-3 多模型推理支持 | ✅ 已完成 |
| 2026-08-08 | VM-P3 运动示意图（分镜蓝图） | ✅ 已完成 |
