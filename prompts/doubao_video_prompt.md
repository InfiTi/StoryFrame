根据参考图生成{frame_count}帧竖屏视频，主体产品是{category}。

## 全局约束
- 9:16竖屏，主体始终在画面中间80%区域
- 商品外观与参考图严格一致
- 负向排除：{negative_words}
- 音乐：{bgm_style}
{style_line}

## 节奏约束
- 每帧画面必须有可见的物理运动（产品形变/碎片飞溅/汁水流动/雾气上升/光泽变化），禁止纯静态展示
- 短帧（≤1.5s）必须用 burst 或 fast 速度词描述动作
- 长帧（>1.5s）允许 ease-in-out，但前 60% 必须有运动，后 40% 才允许 hold
- 禁止使用 "sits still"、"remains stationary"、"static"、"no motion" 等静止描述
- video_prompt 中必须包含至少 1 个运动动词（飞溅/流动/碎裂/形变/飘动/滑落/膨胀/收缩/撞击）

## {frames_section}

逐帧按上述指令执行运动，帧间按transition衔接。
