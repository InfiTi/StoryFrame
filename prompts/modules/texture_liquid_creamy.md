## 质感-动态映射规则（液态/夹心类）
- 液态/夹心类（gooey/creamy/saucy）→ 爆浆流出、滴落、融化扩散、夹心溢出
- motion_hint 必须包含：运动方向（向下/向外扩散）+ 速度曲线（decelerate/ease-in 优先）+ 幅度（流动距离占画面百分比）

## motion_hint 三要素规则
1. **运动方向**：downward（向下滴落）/ radial（向外爆浆）/ lateral（横向扩散）
2. **速度曲线**：decelerate（减速到停）/ ease-in（渐快）/ ease-in-out（先快后慢）
3. **幅度参考**：用流动距离描述（如 syrup flows to 20% frame height / drips reach lower third）

**示例**：
- ✅ `round dessert ball cracks open, viscous caramel flows downward from rupture, decelerating over 0.5s, reaching 25% frame height, droplets clinging to edge`

## 运镜-动态联动规则（液态/夹心类）
| 产品动态 | 推荐运镜 | 联动逻辑 |
|---------|---------|--------|
| 爆浆流出 | micro-pan follow flow → hold | 镜头微平移跟随流动方向 |
| 滴落 | tilt down follow → close-up hold | 镜头跟随滴落轨迹下移 |
| 融化扩散 | slow pull back → hold wide | 拉远展示扩散范围 |

## 速度曲线-帧时长绑定规则
| 帧时长 | 适配速度曲线 | 禁止速度曲线 |
|--------|------------|------------|
| ≤1.0s | burst→freeze | ease-in-out |
| 1.0-2.0s | ease-in / decelerate | ease-in-out |
| >2.0s | ease-in-out / constant / decelerate | burst→freeze |

## 运镜节奏编排规则
- 开场帧：冲击型 — snap zoom out / fast push-in + hard stop（爆浆瞬间）
- 中间帧：跟随型 — micro-pan follow flow / tilt down follow / macro rack focus
- 结尾帧：收稳型 — slow pull back / static hold

## image_prompt 描述框架（严格遵守）
按以下六层结构顺序描述，每层缺一不可：
1. **主体**：产品名称+当前状态（完整/截面/爆浆中/融化中）
2. **角度**：拍摄角度+景别
3. **质感**：产品表面材质的精确物理描述（viscous, glossy, creamy, bubbling, dripping）
4. **光影**：完整灯光方案
5. **背景**：背景环境描述
6. **构图**：画面布局+安全区+视觉重心

### 材质词汇表（液态/夹心类常用）
| 类型 | ✅ 精确术语 | ❌ 模糊词 |
|------|-----------|----------|
| 液态 | viscous syrup, glossy cream, translucent jelly, bubbling sauce | liquid, wet |
| 涂层 | glossy chocolate coating, molten drizzle, caramel glaze | chocolatey |

### 灯光词汇表
| 灯光类型 | 描述术语 | 适用场景 |
|---------|---------|--------|
| 金色光 | warm golden hour lighting | 温暖、食欲感 |
| 侧光 | single hard side-light from [direction] | 突出流动质感 |
| 体积光 | volumetric light beams with haze | 氛围感、热气感 |

### 微动态词汇表（液态/夹心类）
| 微动态类型 | ✅ 描述术语 | 适用场景 |
|-----------|-----------|----------|
| 酱汁微颤 | viscous sauce surface micro-rippling, droplet surface tension wobbling | 流动中酱汁的轻微震荡 |
| 气泡生成破裂 | tiny bubbles forming and popping on surface, carbonation rising | 饮料/碳酸类产品 |
| 滴落涟漪 | single droplet falling with splash ripple, viscous thread stretching | 滴落瞬间 |
| 蒸汽袅袅 | faint steam wisps rising gently, heat vapor curling upward | 热食类产品 |
| 光泽流动 | glossy surface reflection shifting, wet sheen sliding slowly | 涂层表面的光泽变化 |

### 情绪氛围词汇表（液态/夹心类）
| 情绪类型 | 描述术语 | 适用场景 |
|---------|---------|----------|
| 温暖流动 | warm appetite-inducing flow radiating, golden warmth spreading outward | 展示流心/爆浆的食欲感 |
| 甜蜜氤氲 | sweet aromatic mist enveloping, sugary haze floating | 甜品/夹心类氛围 |

## few-shot 质量参考示例（液态/夹心类）

**[原创] 夹心爆浆流心**
```
A round dessert ball with cracked shell leaking viscous caramel filling, mid-burst state with syrup flowing downward. 30-degree angle close-up shot. Glossy chocolate-brown shell surface with crack pattern, warm amber caramel flowing from rupture, thick viscous droplets clinging to edge. Warm golden hour lighting from upper left, rim light on flowing syrup creating amber glow. Dark moody background with faint steam wisps. Product positioned center-left, caramel flow trailing to lower right third, upper right empty. no text, no words, no letters, no logo, no watermark, no label
```

**[提炼] 威化饼干巧克力涂层 (source: YouMind ecommerce-main-image.json)**
```
Ultra high detail commercial food photograph of a crispy wafer bar with glossy chocolate coating, mid-drip state with molten chocolate flowing down one side. 45-degree overhead medium close-up. Layers of flaky wafer visible at broken edge, smooth reflective chocolate surface with pooling droplets, fine cocoa powder dusting on top. High-contrast studio lighting with soft glow accents and rim highlights on chocolate sheen. Luxury gradient backdrop in honey gold and cocoa brown tones, floating chocolate particles. Product centered in lower two-thirds, drip trailing to lower right. no text, no words, no letters, no logo, no watermark, no label
```
