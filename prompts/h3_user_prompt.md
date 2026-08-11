## 商品信息
- 商品名称：{product_name}
- 商品描述：{product_desc}
- 商品质感：{product_texture}
- 核心卖点：{selling_points}
- 风味标签：{flavor_tags}

## 风格模板
- 模板名称：{template_name}
- 风格关键词：{style_words}
- 运镜关键词：{camera_words}
- 节奏：{pacing}
- 冲击强度：{impact_level}
- 节奏策略：{pacing_strategy}
- BGM 风格：{bgm_style}

## 分镜参数
- 分镜数：{frame_count} 帧
- 总时长：{total_duration} 秒
- 画面比例：{aspect_ratio}
- 安全区：{safe_zone}
- 负向词：{negative_words}

## 帧时长分配
{duration_plan}

## 视频方向指引
{direction}

## 任务要求
请基于以上信息，为每一帧生成 H3 规范的提示词。

每帧核心输出：
1. integrated_multimodal_description（英文，80-150词，融合画面+动作+运镜+声音）
2. integrated_multimodal_description_cn（纯中文翻译）
3. motion_phase（动作相位）
4. description（中文简述，15-25字）
5. shot_label（[Shot N]格式）
6. cut_timestamp（第1帧留空，后续帧 At MM:SS.mmm, 格式）
7. duration（该帧持续秒数）

最后一帧之后，追加全局音频字段：
- overall_soundscape（全片环境音，英文）
- non_diegetic_music（背景音乐，英文）

直接输出 JSON 数组，前 N 个对象是帧数据，最后 1 个是全局音频。
