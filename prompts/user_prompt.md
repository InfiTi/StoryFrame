请为以下零食产品设计 {frame_count} 帧分镜脚本，用于图生视频带货素材制作。

【产品信息】
产品名称：{product_name}
产品描述：{product_desc}
核心质感：{product_texture}
核心卖点：{selling_points}
口味标签：{flavor_tags}
{spec_info}{review_tags}{copy_hints}{direction}
【风格模板】
模板名称：{template_name}
模板定位：{template_desc}
视觉风格关键词：{style_words}
镜头运动关键词：{camera_words}
冲击强度：{impact_level}
节奏策略：{pacing_strategy}
BGM风格：{bgm_style}

【硬性约束】
画面比例：{aspect_ratio}
构图安全区：{safe_zone}
负向排除词：{negative_words}

【分镜要求】
- 分镜数：{frame_count} 帧
- 总时长：{total_duration} 秒
- 帧时长分配（必须严格遵守以下时长）：
{duration_plan}
- 第1帧【爆点开场】：强动态瞬间（撞击/炸裂/飞溅），建立产品整体认知，第一秒抓眼球
- 第2~{mid_frame}帧【质感递进】：逐帧放大细节，聚焦截面/层次/涂层/质地，每帧一个核心卖点
- 第{frame_count}帧【记忆定格】：产品完整陈列特写，画面稳定清晰，呈现最诱人状态
- image_prompt 必须融入 {style_words} 视觉风格关键词
- camera_motion 必须融入 {camera_words} 镜头风格关键词，且与 {bgm_style} 节奏匹配
- motion_hint 必须严格基于 {product_texture} 质感设计动态，不得出现与物理属性矛盾的动作
- video_prompt 必须是完整的动作剧本：初始状态 → 运动轨迹 → 镜头运动 → 速度节奏 → 结束状态
- camera_motion 必须包含起止构图+运动距离+停顿状态

【帧间连贯性要求】
- 每帧的结束画面必须与下一帧的起始画面自然衔接，不允许突兀跳转
- 上一帧产品停留的位置 = 下一帧产品出现的位置（除非 transition 为 hard cut）
- 连续帧的镜头运动方向不要全部相同，避免单调（如连续3帧 push-in 不可接受）
- 除第1帧和最后一帧外，相邻帧的运动速度曲线应该有变化（不要全部 burst 或全部 constant）
- transition 为 whip pan / speed ramp / fade 时，前后帧的画面动态需要有呼应（如 whip pan 前帧结尾产品偏右，后帧开头产品从左进入）

请输出 JSON 数组。
