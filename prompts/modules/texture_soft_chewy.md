## 质感-动态映射规则（软糯类）
- 软糯类（soft/chewy/mochi）→ 轻压回弹、拉扯延展、缓慢形变、拉丝粘连
- motion_hint 必须包含：运动方向（向下/向上/横向）+ 速度曲线（ease-in-out/decelerate 优先）+ 幅度（形变占产品体积百分比）

## motion_hint 三要素规则
1. **运动方向**：downward（向下按压）/ upward（回弹向上）/ lateral（横向拉扯）
2. **速度曲线**：ease-in-out（先快后慢）/ decelerate（减速到停）/ ease-in（渐快）
3. **幅度参考**：用形变百分比描述（如 compressed 20% of height / stretched to 150% length）

**示例**：
- ✅ `soft mochi compressed downward 20% of its height in 0.2s burst, then ease-in-out recoil back to original shape over 0.4s, surface wrinkles form and smooth out`

## 运镜-动态联动规则（软糯类）
| 产品动态 | 推荐运镜 | 联动逻辑 |
|---------|---------|--------|
| 拉丝延展 | slow tilt up → hold at stretch point | 镜头跟随拉丝方向上移 |
| 轻压回弹 | overhead → slow push-in → hold | 俯拍推进放大形变细节 |
| 缓慢形变 | macro rack focus → hold | 焦点从整体转移到形变细节 |

## 速度曲线-帧时长绑定规则
| 帧时长 | 适配速度曲线 | 禁止速度曲线 |
|--------|------------|------------|
| ≤1.0s | burst→freeze | ease-in-out |
| 1.0-2.0s | ease-in / decelerate | ease-in-out |
| >2.0s | ease-in-out / constant / decelerate | burst→freeze |

## 运镜节奏编排规则
- 开场帧：冲击型 — fast push-in + hard stop / whip pan + freeze
- 中间帧：渐变型 — slow tilt up / macro rack focus / slow push-in
- 结尾帧：收稳型 — slow pull back / static hold

## image_prompt 描述框架（严格遵守）
按以下六层结构顺序描述，每层缺一不可：
1. **主体**：产品名称+当前状态（完整/被压缩/拉丝中/形变中）
2. **角度**：拍摄角度+景别
3. **质感**：产品表面材质的精确物理描述（glossy, sticky, translucent, smooth, elastic）
4. **光影**：完整灯光方案
5. **背景**：背景环境描述
6. **构图**：画面布局+安全区+视觉重心

### 材质词汇表（软糯类常用）
| 类型 | ✅ 精确术语 | ❌ 模糊词 |
|------|-----------|----------|
| 软质 | glossy surface, sticky texture, translucent, elastic, smooth | soft-looking |
| 粉末 | fine starch dusting, powdered sugar coating | powdery |

### 灯光词汇表
| 灯光类型 | 描述术语 | 适用场景 |
|---------|---------|--------|
| 柔光 | soft diffused studio lighting, gentle highlights | 均匀质感展示 |
| 侧光 | single soft side-light from [direction] | 突出表面起伏 |
| 体积光 | volumetric light beams with haze | 氛围感 |

### 微动态词汇表（软糯类）
| 微动态类型 | ✅ 描述术语 | 适用场景 |
|-----------|-----------|----------|
| 光泽呼吸 | glossy surface subtly shifting highlights, soft sheen pulsing | 表面光泽微微变化 |
| 表面张力 | surface tension visible, slight wobble on curved surface | 轻压回弹时的表面波动 |
| 淀粉飘散 | fine starch particles floating gently around product | 柔和的粉末飘浮 |
| 弹性微颤 | elastic surface micro-vibrating after release, jiggle settling | 回弹后的微颤 |

### 情绪氛围词汇表（软糯类）
| 情绪类型 | 描述术语 | 适用场景 |
|---------|---------|----------|
| 高级感凝固 | time-frozen elegance, luxurious stillness in slow motion | 慢镜头展示质感 |
| 温暖柔和 | warm gentle glow embracing product, soft warmth radiating | 展示软糯温暖感 |

## few-shot 质量参考示例（软糯类）

**[原创] 麻糬压缩回弹**
```
A soft chewy mochi ball with smooth glossy surface, mid-compression state showing surface wrinkles and deformation. Top-down 90-degree macro shot. Translucent white surface with subtle pink tint visible at edges, sticky glossy texture, faint powder dusting. Soft diffused studio lighting with gentle highlights on curved surface, subtle fill light from right. Clean off-white background with faint shadow beneath product. Product centered occupying 60% of frame, compression visible at bottom contact point. no text, no words, no letters, no logo, no watermark, no label
```

**[提炼] 墨西哥塔可爆料 (source: YouMind product-marketing.json)**
```
A high-end commercial food photograph of a soft tortilla taco, mid-toss state with ingredients separating from the shell. Three-quarter close-up angle. Warm golden tortilla surface with slight char spots, glossy filling of seasoned meat, fresh cilantro leaves, and crumbled cheese visible inside. Soft cinematic lighting highlighting tortilla texture and filling glossiness, subtle steam wisps rising, warm amber tones. Dark moody slate background with shallow depth of field. Product positioned center-left, ingredients scattering toward upper right, lower left empty. no text, no words, no letters, no logo, no watermark, no label
```
