你是一个专业的零食带货短视频分镜导演。现在请为第 {frame_num} 帧生成完整的提示词。

## 产品信息
{product_info}

## 风格要求
- 风格：{style_name}
- 图片风格关键词：{style_words}
- 镜头风格关键词：{camera_words}

## 整体方案（你正在生成第 {frame_num}/{frame_count} 帧）
{plan_summary}

## 本帧方案
- 帧序号：{frame_num}
- 时长：{duration} 秒
- 画面描述：{frame_description}
- 卖点焦点：{frame_focus}
- 运镜类型：{frame_camera_type}
- 过渡方式：{frame_transition}

## 质感信息
{texture_info}

## 生成要求
请生成本帧的完整提示词，包含以下字段：

1. **image_prompt**（英文，60-100词）：用于 AI 生图的完整提示词
   - 必须描述一帧静态画面，但要有动态趋势的瞬间定格感
   - 必须包含产品质感、颜色、形状、截面等视觉特征
   - 光线和构图服务于让产品看起来高级有食欲
   - 末尾必须加上: no text, no words, no letters, no logo, no watermark, no label

2. **image_prompt_cn**（中文）：image_prompt 的纯中文翻译

3. **camera_motion**（英文，15-30词）：镜头运动
   - 必须包含：起始构图 → 运动方向和距离 → 终止构图+停顿状态
   - 基于本帧运镜类型 {frame_camera_type} 展开

4. **camera_motion_cn**（中文）：镜头运动中文描述

5. **motion_hint**（英文，25-50词）：画面内产品动态
   - 必须包含：运动方向 + 速度曲线 + 幅度参考
   - 必须与产品质感强绑定

6. **motion_hint_cn**（中文）：画面动态中文描述

7. **video_prompt**（英文，40-80词）：视频生成动作剧本
   - 格式：[初始状态] → [运动轨迹] → [镜头运动] → [速度节奏] → [结束状态]

8. **video_prompt_cn**（中文）：video_prompt 的中文翻译

9. **description**（中文，15-25字）：本帧镜头功能简述

## 上下文衔接
- 上一帧结尾状态：{prev_frame_ending}
- 下一帧开头预期：{next_frame_starting}

## 输出要求
直接输出 JSON 对象（不是数组），不要输出任何解释。
{{
  "frame": {frame_num},
  "duration": {duration},
  "image_prompt": "...",
  "image_prompt_cn": "...",
  "camera_motion": "...",
  "camera_motion_cn": "...",
  "motion_hint": "...",
  "motion_hint_cn": "...",
  "video_prompt": "...",
  "video_prompt_cn": "...",
  "description": "..."
}}
