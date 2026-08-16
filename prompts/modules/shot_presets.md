# 商业食品广告标准镜头预设库

这不是"参考"，是**强制执行标准**。每一帧的运镜、角度、光线、过渡方式由预设锁定，你只负责填入产品信息。

## 使用规则
1. plan 阶段：根据帧位（开场/中间/结尾）+ 产品质感，从下表选择预设
2. frame 阶段：严格按所选预设的维度生成画面，运镜/光线/角度/速度曲线不得修改
3. 你填入的只有：产品名称、产品状态、质感细节、表面细节、背景颜色、形变/动作描述
4. 预设中的 `→` 表示运镜轨迹（如 `medium shot → push-in → close-up`），不是箭头分隔符

---

## 开场帧预设（第 1 帧，黄金 3 秒钩子）

### PRESET-O1: 微距碎裂冲击（酥脆类专用）
```
景别: medium shot → extreme close-up
运镜: fast push-in + hard stop
速度: burst to freeze
角度: 45° overhead
光线: single hard side-light from left + rim light
背景: solid dark color, subtle radial gradient
主体动作: 产品碎裂/崩解/飞溅，碎片向外放射
过渡到下一帧: whip pan
```
画面要点：产品在碎裂的 40% 瞬间定格，3-4 块碎片飞在半空，中心仍可辨认但裂纹可见

### PRESET-O2: 慢推质感揭示（软糯类专用）
```
景别: medium close-up → close-up
运镜: slow push-in + hold
速度: ease-in-out
角度: eye-level slight three-quarter
光线: soft diffused key from upper right + warm side-backlight
背景: solid warm light color, subtle gradient
主体动作: 产品缓慢形变（拉丝延展/酱汁缓流/轻压回弹）
微动态约束: 必须有可见形变（拉丝延展≥画面5%、酱汁流动方向明确、轻压形变≥10%），禁止产品完全静止
过渡到下一帧: speed ramp
```
画面要点：产品处于形变开始阶段，表面光泽可见，有明显的"即将变化"张力

### PRESET-O3: 俯拍全貌定格（冰爽/液态类专用）
```
景别: wide overhead → medium overhead
运镜: pull back + hold
速度: decelerate
角度: 90° overhead
光线: top soft diffused + side fill
背景: textured surface (marble/slate/wood)
主体动作: 产品静止，周围有冷凝水珠/雾气/气泡等氛围元素
微动态约束: 雾气必须有明显上升轨迹或冷凝水珠必须有滑落方向，禁止纯静止氛围
过渡到下一帧: fade
```
画面要点：产品从正上方俯拍，周围氛围元素（冷凝/雾气/光斑）开始出现

---

## 中间帧预设（第 2~N-1 帧，快切卖点展示）

### PRESET-M1: 甩镜滑入揭示（通用转场）
```
景别: off-center close-up → centered medium shot
运镜: whip pan + freeze
速度: burst to freeze
角度: eye-level three-quarter
光线: soft diffused + crisp rim light on leading edge
背景: solid color or gradient
主体动作: 产品从画面一侧滑入定格，或配料飞入画面
过渡到下一帧: whip pan 或 speed ramp
```
画面要点：产品从一侧滑入，运动模糊拖尾在身后，定格在画面中心

### PRESET-M2: 微距焦点转移（多层结构产品）
```
景别: macro close-up → macro close-up（焦点变换）
运镜: rack focus
速度: decelerate
角度: macro three-quarter
光线: focused hard light on subject + soft ambient fill
背景: solid color with heavy bokeh
主体动作: 焦点从产品的一个细节转移到产品的另一个细节（两个焦点都必须是产品本身，禁止引入包装/道具/背景元素）
微动态约束: 焦点转移过程中必须有 1 个可见物理变化（光泽流动/纹理膨胀/汁水渗出），不是单纯景深变化
过渡到下一帧: hard cut 或 whip pan
```
画面要点：近处细节清晰，远处细节虚化，焦点正在转移的瞬间。两个焦点必须是同一产品的不同部位（如表面纹理→截面层次、外观→质感细节）

### PRESET-M3: 弧线环绕展示（立体感产品）
```
景别: medium shot → medium shot（角度变化）
运镜: arc shot 90° + hold
速度: constant to decelerate
角度: eye-level, 0° → 90°
光线: three-point lighting + rim light
背景: solid color with gentle gradient
主体动作: 产品静止或微小动态（蒸汽/光泽变化）
微动态约束: 环绕过程中必须有表面光泽变化（反光角度位移）或蒸汽飘动，禁止纯静止环绕
过渡到下一帧: speed ramp 或 fade
```
画面要点：产品在环绕过程中展示侧面+正面，立体感强

### PRESET-M4: 急速拉远揭示（从细节到全貌）
```
景别: extreme close-up → wide shot
运镜: snap zoom out + hold
速度: burst to decelerate
角度: slight overhead
光线: volumetric light from upper left
背景: dark gradient with radial glow
主体动作: 粉末/碎片/配料扩散后定格全貌
过渡到下一帧: hard cut 或 whip pan
```
画面要点：从极近的细节突然拉远，揭示产品全貌和周围的扩散物

### PRESET-M5: 俯拍旋转（扁平产品/切片展示）
```
景别: overhead full shot → overhead full shot（旋转）
运镜: overhead rotation 180° + hold
速度: constant to decelerate
角度: 90° overhead
光线: top soft diffused + side fill
背景: textured surface (wood/marble/slate)
主体动作: 产品静止，背景纹理随旋转移动
微动态约束: 旋转过程中必须有汁水/碎屑/粉末等微粒位移，禁止纯静止旋转
过渡到下一帧: fade 或 speed ramp
```
画面要点：从正上方看产品，旋转过程中展示完整形态和排列

### PRESET-M6: 慢推形变特写（软糯/液态类质感展示）
```
景别: close-up → extreme close-up
运镜: slow push-in + hold
速度: ease-in-out
角度: eye-level slight three-quarter
光线: soft diffused key + warm rim light
背景: solid warm color, subtle gradient
主体动作: 产品形变进行中（拉丝/流心/滴落/压缩回弹）
微动态约束: 形变必须≥15%可见变化（拉丝长度、流心扩散范围、压缩深度），禁止形变幅度<10%
过渡到下一帧: speed ramp 或 morph
```
画面要点：形变进行到 50% 的瞬间，质感细节（光泽/黏连/弹性）清晰可见

### PRESET-M7: 急推爆点特写（通用冲击型）
```
景别: medium shot → extreme close-up
运镜: fast push-in + hard stop
速度: burst to freeze
角度: 45° overhead
光线: single hard side-light + rim light
背景: solid dark color
主体动作: 产品局部瞬间形变/爆裂/飞溅，冲击瞬间定格
过渡到下一帧: whip pan 或 hard cut
```
画面要点：快速推进到极近景，产品在推进终点发生冲击性形变（碎裂/爆浆/弹跳），碎片/汁水在画面中飞溅定格

### PRESET-M8: 快速横切对比（多卖点快闪）
```
景别: close-up → close-up（横向位移）
运镜: quick pan + freeze
速度: burst to freeze
角度: eye-level
光线: soft diffused + crisp rim light
背景: solid color or gradient
主体动作: 产品从一侧快速横移到中心定格，或配料飞入撞击产品
过渡到下一帧: speed ramp 或 hard cut
```
画面要点：产品或配料以快速横移进入画面，运动模糊拖尾，定格时展示撞击/落点瞬间

---

## 结尾帧预设（最后 1 帧，记忆定格）

### PRESET-E1: 拉远全景定格（通用收尾）
```
景别: close-up → wide shot
运镜: slow pull back + hold
速度: ease-in-out
角度: eye-level slight overhead
光线: warm soft key light + gentle rim light
背景: solid color with warm gradient
主体动作: 产品静止，最佳状态展示（完整/切面/排列）
微动态约束: 允许镜头慢拉，但前 60% 必须有残余动态（余温蒸汽/光泽收敛/汁水回流），后 40% 才允许 hold
过渡: none（最后一帧）
```
画面要点：产品在最佳状态下的完整展示，画面稳定清晰，留下食欲记忆点

### PRESET-E2: 俯拍排列全景（多片/多件产品）
```
景别: overhead wide shot → hold
运镜: static hold（或微缓 pull back）
速度: constant
角度: 90° overhead
光线: top soft diffused + side fill
背景: textured surface
主体动作: 产品静止，整齐排列展示
微动态约束: 允许静止排列，但画面中必须有 1 处微动态元素（蒸汽尾迹/水珠滑落/光泽闪烁）
过渡: none（最后一帧）
```
画面要点：多件产品从正上方俯拍的整齐排列，仪式感收尾

### PRESET-E3: 慢推极致特写（高端质感收尾）
```
景别: close-up → extreme close-up
运镜: slow push-in + hold
速度: decelerate
角度: eye-level three-quarter
光线: soft diffused key + dramatic rim light
背景: dark solid color with subtle gradient
主体动作: 产品静止，表面质感极致展示
微动态约束: 推进过程中必须有表面光泽渐变或纹理细节放大可见变化，禁止纯静止推近
过渡: none（最后一帧）
```
画面要点：极近景下产品质感的极致展示，光影戏剧化，高级感凝固

---

## 预设选择矩阵

### 按质感+帧位选择

| 质感 | 开场(第1帧) | 中间帧(轮换) | 结尾帧 |
|------|-----------|------------|--------|
| 酥脆类 | PRESET-O1 | PRESET-M1 → M2 → **M7** → M4 → M1（轮换） | PRESET-E1 |
| 软糯类 | PRESET-O2 | PRESET-M6 → **M7** → M2 → **M8** → M6（轮换） | PRESET-E3 |
| 液态/夹心类 | PRESET-O2 | PRESET-M6 → **M7** → M4 → **M8** → M6（轮换） | PRESET-E1 |
| 冰爽类 | PRESET-O3 | PRESET-M3 → **M8** → M5 → **M7** → M3（轮换） | PRESET-E2 |

### 中间帧轮换规则
1. 按"→"顺序轮换，不重复相邻帧用相同预设
2. 如果帧数 > 中间预设数量，从第一个重新开始轮换
3. 相邻两帧的运镜必须不同（预设已保证，但需检查）

### 过渡方式自动推导
每个预设已内置过渡方式（见上方各预设的"过渡到下一帧"字段），plan 阶段直接使用，不需要 LLM 自行决定。

**例外**：如果总帧数 ≤ 2，所有过渡用 hard cut。

### 禁止事项
- ❌ 禁止 LLM 自行设计运镜方式
- ❌ 禁止使用预设库之外的运镜术语
- ❌ 禁止修改预设中的角度、光线、速度曲线
- ❌ 禁止相邻两帧使用相同预设（除非总帧数 ≤ 3）
