## 质感-动态映射规则（冰爽类）
- 冰爽类（frozen/icy）→ 雾气升腾、冷凝水珠、冰霜剥落、冷气下沉
- motion_hint 必须包含：运动方向（向上雾气/向下冷气/横向剥落）+ 速度曲线（ease-in/constant 优先）+ 幅度（雾气扩散范围/水珠大小）

## motion_hint 三要素规则
1. **运动方向**：upward（雾气升腾）/ downward（冷气下沉）/ lateral（冰霜横向剥落）
2. **速度曲线**：ease-in（渐快扩散）/ constant（匀速上升）/ decelerate（减速到停）
3. **幅度参考**：用扩散范围描述（如 mist rises to 30% frame height / frost particles scatter to 10% frame width）

**示例**：
- ✅ `cold mist rises upward from frozen can top, ease-in acceleration over 0.4s, reaching 30% frame height, condensation droplets form and grow on surface`

## 运镜-动态联动规则（冰爽类）
| 产品动态 | 推荐运镜 | 联动逻辑 |
|---------|---------|--------|
| 雾气升腾 | slow tilt up → hold at fog top | 镜头跟随雾气上升 |
| 冷凝水珠 | macro push-in → rack focus to droplet | 推进+焦点转移到水珠 |
| 冰霜剥落 | overhead rotation 30° → hard stop | 旋转展示剥落过程 |

## 速度曲线-帧时长绑定规则
| 帧时长 | 适配速度曲线 | 禁止速度曲线 |
|--------|------------|------------|
| ≤1.0s | burst→freeze | ease-in-out |
| 1.0-2.0s | ease-in / decelerate | ease-in-out |
| >2.0s | ease-in-out / constant / decelerate | burst→freeze |

## 运镜节奏编排规则
- 开场帧：冲击型 — macro push-in + hard stop / snap zoom out（冷气爆发）
- 中间帧：跟随型 — slow tilt up / macro rack focus / slow push-in
- 结尾帧：收稳型 — slow pull back / static hold

## image_prompt 描述框架（严格遵守）
按以下六层结构顺序描述，每层缺一不可：
1. **主体**：产品名称+当前状态（完整/冷凝中/雾气中/冰霜剥落中）
2. **角度**：拍摄角度+景别
3. **质感**：产品表面材质的精确物理描述（crystalline, frost coating, condensation, misty）
4. **光影**：完整灯光方案
5. **背景**：背景环境描述
6. **构图**：画面布局+安全区+视觉重心

### 材质词汇表（冰爽类常用）
| 类型 | ✅ 精确术语 | ❌ 模糊词 |
|------|-----------|----------|
| 冻品 | crystalline ice crystals, frost coating, condensation droplets | cold, icy |
| 金嘱/包装 | brushed aluminum, matte steel, frosted can surface | shiny can |

### 灯光词汇表
| 灯光类型 | 描述术语 | 适用场景 |
|---------|---------|--------|
| 冷光 | cool blue-tinted lighting | 冰爽感、冷调 |
| 侧光 | single hard side-light from [direction] | 突出冰晶折射 |
| 轮廓光 | rim light outlining edges | 突出雾气轮廓 |

### 微动态词汇表（冰爽类）
| 微动态类型 | ✅ 描述术语 | 适用场景 |
|-----------|-----------|----------|
| 雾气袅袅 | cold mist curling upward gently, white vapor drifting skyward | 冷雾从产品上升 |
| 冷凝结珠 | condensation droplets forming and growing, water beads sliding slowly | 罐装/瓶装冷饮表面 |
| 冰晶折射闪烁 | ice crystals catching light and sparkling, frost glinting subtly | 冰晶表面的光泽变化 |
| 霜层剥落 | frost flakes detaching softly, ice layer cracking silently | 冰棒/冻品表面 |

### 情绪氛围词汇表（冰爽类）
| 情绪类型 | 描述术语 | 适用场景 |
|---------|---------|----------|
| 清凉扩散 | cool refreshing aura spreading outward, icy chill radiating | 展示冰爽感 |
| 夏日透爽 | crisp summer freshness, cooling breeze sensation | 饮料/冰淇淋类 |

## few-shot 质量参考示例（冰爽类）

**[原创] 冰霜饮料罐冷凝**
```
A frozen beverage can with crystalline frost coating and condensation droplets, cold mist rising from top. Eye-level medium shot with slight low angle. Brushed aluminum surface with frost crystal texture, water droplets of varying sizes, white vapor curling upward. Cool blue-tinted lighting from front-left, rim light catching frost crystals creating sparkle, dark background. Solid deep navy background with gradient lighter at top. Product centered occupying lower two-thirds, mist rising into upper third. no text, no words, no letters, no logo, no watermark, no label
```

**[提炼] 冰淇淋甜筒融化 (source: YouMind product-marketing.json)**
```
Hyper-realistic commercial food photograph of a vanilla ice cream cone, mid-melt state with soft-serve swirl beginning to droop. Eye-level close-up shot. Creamy off-white ice cream with visible vanilla bean specks, glossy melting surface with slow drips running down, golden waffle cone texture with grid pattern. Cinematic lighting with warm golden key light from left, cool fill from right creating temperature contrast. Shallow depth of field, bokeh background in warm cream tones. Product centered occupying 70% of frame, melt drip trailing to lower third. no text, no words, no letters, no logo, no watermark, no label
```
