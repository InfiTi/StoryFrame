# 视频提示词精细化路线图

> 创建: 2026-07-19 | 状态: 进行中

## 背景

当前提示词体系已具备良好基础（质感-动态映射、安全区、节奏策略、帧时长分配），但视频生成的精细度存在以下短板：

1. **动态描述不够量化** — motion_hint 是自然语言，视频模型无法理解"飞溅多远、多快、什么方向"
2. **视频提示词复用图片描述** — 豆包视频模板用 image_prompt 凑合，缺少独立的"动作剧本"
3. **镜头运动缺少起止位置** — "fast push-in" 不够，需要从哪推到哪、推多远
4. **帧间缺乏连贯性** — 每帧独立生成，容易出现跳戏
5. **缺少负面动态** — 有负面排除词（no text），但没有负面动态（禁止相机抖动等）

## 改动清单

### VP-P0-1: motion_hint 三要素规则
- **优先级**: P0（立竿见影）
- **改动文件**: `prompts/system_prompt.md`
- **工作量**: 小（加规则说明 + 示例）
- **内容**:
  - motion_hint 必须包含三要素：
    - 运动方向：radial / downward / upward / spiral / lateral
    - 速度曲线：burst→freeze / ease-in / constant / decelerate
    - 幅度参考：占画面百分比（如 particles <5% frame size）
  - 更新示例展示量化描述风格
- **验证**: 生成一次分镜，检查 motion_hint 是否包含三要素
- **状态**: ✅ 已完成

### VP-P0-2: 豆包视频模板结构化升级
- **优先级**: P0（立竿见影）
- **改动文件**: `prompts/doubao_video_prompt.md`, `core/prompt_loader.py`
- **工作量**: 中（模板重构 + prompt_loader 适配）
- **内容**:
  - 每帧从"画面描述/镜头/动态/时长"升级为：
    ```
    ### 第 N 帧（duration）
    - 起始画面：初始状态描述
    - 运动指令：产品动态 + 幅度
    - 镜头：起止构图 + 运动路径
    - 速度节奏：速度曲线描述
    - 结束画面：定格状态
    - 转场到下一帧：transition 类型
    ```
  - prompt_loader.py 的 `get_doubao_video_prompt` 适配新结构
- **验证**: 生成视频提示词，检查每帧是否包含完整动作剧本
- **状态**: ✅ 已完成

### VP-P1-1: 新增 video_prompt 独立字段
- **优先级**: P1（中等投入）
- **改动文件**: `core/storyboard.py`, `prompts/system_prompt.md`, `core/prompt_loader.py`, `ui/main_window.py`
- **工作量**: 中（数据结构变更 + 多处适配）
- **内容**:
  - StoryboardFrame 新增 `video_prompt: str` 和 `video_prompt_cn: str`
  - system_prompt.md 增加字段说明：
    > video_prompt: 英文，写给视频生成模型的完整指令，包含：画面初始状态 + 运动轨迹 + 镜头运动 + 速度节奏 + 结束状态
  - prompt_loader.py 适配新字段
  - UI 展示新字段
- **验证**: 生成分镜，检查 video_prompt 是否为独立的动作剧本而非图片描述
- **状态**: ✅ 已完成

### VP-P1-2: camera_motion 起止构图规则
- **优先级**: P1（中等投入）
- **改动文件**: `prompts/system_prompt.md`
- **工作量**: 小（加规则 + 示例）
- **内容**:
  - camera_motion 必须包含：
    - 起始构图：wide / medium / macro / close-up
    - 终止构图：wide / medium / macro / close-up
    - 运动时长：占该帧时长的百分比
    - 停顿时长：剩余时间的 hold
  - 示例：`dolly forward from wide to macro in 0.8s (67% of frame), hold macro 0.4s`
- **验证**: 生成分镜，检查 camera_motion 是否包含起止构图
- **状态**: ✅ 已完成

### VP-P2-1: 帧间连贯性指令
- **优先级**: P2（长线收益）
- **改动文件**: `prompts/user_prompt.md`, 可选 `core/storyboard.py`
- **工作量**: 中
- **内容**:
  - user_prompt.md 增加连贯性要求：
    > 相邻帧之间的产品位置、角度、光线方向必须保持一致或通过镜头运动自然过渡
  - 可选：StoryboardFrame 新增 `continuity_hint` 字段，描述与上一帧的衔接关系
  - 豆包视频模板中加入帧间衔接提示
- **验证**: 生成多帧视频，检查产品位置/光线是否连贯
- **状态**: ✅ 已完成（user_prompt.md 已加帧间连贯性要求，暂不新增 continuity_hint 字段，保持数据结构简洁）

### VP-P2-2: 负面动态描述
- **优先级**: P2（低成本高收益）
- **改动文件**: `prompts/doubao_video_prompt.md`
- **工作量**: 小
- **内容**:
  - 视频模板加入禁止动态：
    ```
    - 禁止动态：相机抖动、产品滚出画面、画面变形扭曲、闪烁、色块跳变、主体模糊
    ```
- **验证**: 检查视频提示词输出中是否包含负面动态描述
- **状态**: ✅ 已完成（随 VP-P0-2 一同完成，禁止动态已写入 doubao_video_prompt.md）

## 执行顺序

```
VP-P0-1 → VP-P0-2 → VP-P1-1 → VP-P1-2 → VP-P2-1 → VP-P2-2
```

每完成一项：
1. 更新本文件的状态标记（⬜→✅）
2. 更新 STATUS.md 待办勾选
3. 在 STATUS.md 最近变更中记录
4. 测试验证

## 变更记录

| 日期 | 任务 | 状态 |
|------|------|------|
| 2026-07-19 | VP-P0-1 motion_hint 三要素规则 | ✅ 已完成 |
| 2026-07-19 | VP-P0-2 豆包视频模板结构化升级 | ✅ 已完成 |
| 2026-07-19 | VP-P2-2 负面动态描述 | ✅ 已完成（随 P0-2） |
| 2026-07-19 | VP-P1-1 新增 video_prompt 独立字段 | ✅ 已完成 |
| 2026-07-19 | VP-P1-2 camera_motion 起止构图规则 | ✅ 已完成 |
| 2026-07-19 | VP-P2-1 帧间连贯性指令 | ✅ 已完成 |
