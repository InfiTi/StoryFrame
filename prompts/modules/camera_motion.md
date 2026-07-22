## 运镜词汇库（必须从中选择）
生成 camera_motion 时必须使用以下标准化运镜术语，禁止自创运镜名称：

### 基础运镜
| 术语 | 含义 | 适用场景 |
|------|------|---------|
| push-in | 推进（镜头靠近产品） | 放大细节、制造冲击 |
| pull back | 拉远（镜头远离产品） | 揭示全貌、收尾定格 |
| orbit | 环绕（围绕产品旋转） | 展示立体感、全貌 |
| tilt up/down | 上下摇（镜头纵向旋转） | 跟随上下方向动态 |
| pan left/right | 左右摇（镜头横向旋转） | 跟随横向动态 |
| static hold | 静止保持 | 产品自身动态足够强时 |

### 高级运镜
| 术语 | 含义 | 适用场景 |
|------|------|---------|
| whip pan + freeze | 甩镜定格（快速甩动后急停） | 转场冲击、节奏加速 |
| speed ramp zoom | 变速缩放（先快后慢或先慢后快） | 节奏变化、突出关键瞬间 |
| macro rack focus | 焦点变换（从一个细节转移到另一个） | 转移视觉焦点、展示多个卖点 |
| dutch angle tilt | 倾斜角度（镜头歪斜） | 制造不安/冲击/颠覆感 |
| overhead rotation | 俯拍旋转（从正上方旋转） | 展示全貌、适合扁平产品 |
| snap zoom out | 急速拉远（瞬间扩大视野） | 揭示惊喜、从细节到全景 |
| dolly zoom | 滑动变焦（推进+拉远同步，Vertigo 效果） | 制造眩晕/冲击感 |
| arc shot | 弧线运镜（沿弧线移动） | 展示侧面+正面的过渡 |
| macro push-in | 微距推进（极近距离推进） | 极端细节展示 |
| tilt-shift | 移轴（制造微缩效果） | 产品微缩景观感 |

### 运镜选择规则
1. 每帧从词汇库中选择 1-2 种运镜组合，不要超过 2 种
2. 相邻帧的运镜必须不同（避免视觉疲劳）
3. 运镜必须参照质感模块中的「质感-运镜推荐组合」表选择

## camera_motion 起止构图规则（严格遵守）
camera_motion 必须包含以下要素，缺一不可：
1. **起始构图**：镜头开始时的位置/角度（如 centered medium shot, top-down 45°）
2. **运动方向和距离**：镜头如何移动+移动幅度（如 push-in 20% closer, orbit 90° clockwise, pull back to wide shot）
3. **终止构图+停顿**：镜头结束位置 + 是否停顿（如 hard stop at close-up, hold for 0.3s）

示例：
- `centered medium shot → fast push-in 30% closer → extreme close-up, hard stop hold 0.2s`
- `top-down 45° → quick orbit 90° clockwise around product → side profile, brief hold`
- `wide shot from below → tilt up 30° to eye level → centered medium shot, freeze`

## 速度曲线-运镜配合
速度曲线不仅约束产品动态，也约束运镜节奏：
- burst→freeze → 运镜也用 fast + hard stop（如 fast push-in + hard stop）
- ease-in → 运镜也用 accelerating（如 speed ramp zoom 先慢后快）
- decelerate → 运镜也用 decelerating（如 push-in 减速到 hold）
- ease-in-out → 运镜也用 smooth in/out（如 slow pull back 渐慢）
- constant → 运镜用匀速（如 orbit 匀速旋转）

## 运镜节奏禁忌
- ❌ 所有帧都用 push-in（单调递进）
- ❌ 所有帧都用 static hold（浪费运镜表现力）
- ❌ 开场帧用 slow pull back（节奏太慢，失去钩子作用）
- ❌ 结尾帧用 whip pan（收不住，没有定格感）
- ❌ 相邻两帧用完全相同的运镜组合
