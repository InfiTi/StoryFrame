## 质感-动态映射规则（酥脆类）
- 酥脆类（crispy/crunchy/flaky）→ 碎裂、崩解、碎屑飞溅、弹跳撞击、糖粉炸开
- motion_hint 必须包含：运动方向（radial/向下/横向）+ 速度曲线（burst→freeze 优先）+ 幅度（碎片飞溅占画面百分比）

## motion_hint 三要素规则
1. **运动方向**：radial（放射状）/ downward（向下）/ upward（向上）/ lateral（横向）
2. **速度曲线**：burst→freeze（爆发后定格）/ ease-in（渐快）/ decelerate（减速）
3. **幅度参考**：用占画面百分比描述（如 fragments fly to 15% frame width / particles <5% frame size）

**示例**：
- ✅ `crispy cracker shatters center-screen, 3-4 fragments fly outward radially at burst speed (0.3s), decelerate and freeze at 15% frame width, dust particles <5% frame size`

## 运镜-动态联动规则（酥脆类）
| 产品动态 | 推荐运镜 | 联动逻辑 |
|---------|---------|--------|
| 碎裂/崩解/飞溅 | fast push-in → hard stop at close-up | 镜头冲向碎裂点放大冲击瞬间 |
| 糖粉炸开 | snap zoom out → hold wide | 急拉远揭示粉末扩散全貌 |
| 弹跳撞击 | tilt down follow → micro hold | 镜头跟随弹跳轨迹下落 |

## 速度曲线-帧时长绑定规则
| 帧时长 | 适配速度曲线 | 禁止速度曲线 |
|--------|------------|------------|
| ≤1.0s | burst→freeze / snap | ease-in / constant |
| 1.0-2.0s | ease-in / decelerate / burst→freeze | ease-in-out |
| >2.0s | ease-in-out / constant / decelerate | burst→freeze |

## 运镜节奏编排规则
- 开场帧：冲击型 — snap zoom out / fast push-in + hard stop / whip pan + freeze
- 中间帧：快切加速型 — whip pan / speed ramp zoom / arc shot / macro rack focus
- 结尾帧：收稳型 — slow pull back / overhead rotation + hold / static hold

## image_prompt 描述框架（严格遵守）
按以下六层结构顺序描述，每层缺一不可：
1. **主体**：产品名称+当前状态（完整/截面/碎裂中），用完整名词短语
2. **角度**：拍摄角度+景别，用专业摄影术语
3. **质感**：产品表面材质的精确物理描述（flaky layers, cracked crust, charred edges, golden-brown）
4. **光影**：完整灯光方案（光源类型+方向+质感）
5. **背景**：背景环境描述，干净不喧宾夺主
6. **构图**：画面布局+安全区+视觉重心

### 材质词汇表（酥脆类常用）
| 类型 | ✅ 精确术语 | ❌ 模糊词 |
|------|-----------|----------|
| 烘焙 | flaky layers, cracked crust, glazed surface, charred edges | baked-looking |
| 金嘱/包装 | brushed steel, matte aluminum, foil-wrapped | shiny, metallic-looking |
| 粉末 | fine crystalline powder, coarse sugar crystals | powdery |

### 灯光词汇表
| 灯光类型 | 描述术语 | 适用场景 |
|---------|---------|--------|
| 侧光 | single hard side-light from [direction] | 制造强烈明暗对比 |
| 轮廓光 | rim light / backlight outlining edges | 突出碎裂边缘 |
| 金色光 | warm golden hour lighting | 温暖、食欲感 |

### 微动态词汇表（酥脆类）
| 微动态类型 | ✅ 描述术语 | 适用场景 |
|-----------|-----------|----------|
| 粉末飘散 | fine sugar crystals floating, powder dust suspended mid-air | 碎裂瞬间伴随的粉末飞散 |
| 裂纹扩展 | hairline cracks extending from impact point, fracture lines visible | 推近特写裂纹扩展瞬间 |
| 碎屑微颤 | tiny crumbs vibrating on impact surface, micro-bounce of fragments | 碎裂后碎片轻微回弹 |
| 光泽闪烁 | golden fragments catching light sparkle, crystalline sugar glinting | 碎片飞行中的光泽变化 |

### 情绪氛围词汇表（酥脆类）
| 情绪类型 | 描述术语 | 适用场景 |
|---------|---------|----------|
| 冲击震荡 | impact shockwave rippling outward, freeze-frame energy | 碎裂爆点帧 |
| 温暖食欲 | warm appetite-inducing glow radiating, golden warmth spreading | 展示酥脆色泽 |

## few-shot 质量参考示例（酥脆类）

**[原创] 酥脆威化碎裂**
```
A crispy rectangular wafer with visible layered flaky texture, mid-shatter state with 3 fragments separating center-screen. 45-degree overhead medium shot. Matte golden-brown surface with rough layered cross-section, caramelized edges, fine sugar crystal coating catching light. Single hard side-light from left creating sharp shadows on fragment edges, rim light outlining the wafer's silhouette. Solid dark charcoal background with subtle radial gradient. Product centered in lower third of frame, fragments occupying mid-frame, upper third empty for motion space. no text, no words, no letters, no logo, no watermark, no label
```

**[提炼] 汉堡空中爆碎 (source: YouMind product-marketing.json)**
```
A hyper-realistic hero shot of a crispy golden burger in midair, mid-burst state with thick sauce exploding outward. Three-quarter angle close-up shot. Glistening toasted sesame bun surface with visible sesame seeds, charred grill marks, crispy lettuce edges catching light. Cinematic studio lighting with hard rim light from upper left, soft fill from right, sauce droplets frozen mid-motion catching highlights. Bright solid lemon-yellow background. Product centered occupying 60% of frame, sauce flecks and ingredients scattered to edges, upper portion empty. no text, no words, no letters, no logo, no watermark, no label
```
