# StoryFrame 项目状态

> 最后更新: 2026-07-25 | 版本 v0.9.2

## 概述
分镜图生成器 — 商品信息 → 分镜脚本 → 图片/视频提示词，PySide6 桌面应用。统一生成接口支持多 provider 切换。

## 当前状态
- **版本**: v0.9.1
- **阶段**: V2 两步生成实测 + transition 修复

## 已完成
- [x] 分镜脚本生成（LLM + JSON 流式解析）
- [x] 商品信息管理（读取/编辑/回写 Markdown）
- [x] 风格模板系统（9 预设 + 外部 JSON 配置）
- [x] 提示词模板化（prompts/ Markdown 模板）
- [x] 背景音乐选择 + 模板自动同步
- [x] 豆包图片/视频提示词一键复制（菜单选择中文/英文）
- [x] 冲击强度 + 节奏策略字段（duration_plan 已验证生效）
- [x] 口味标签提取 + 负向词按风格区分
- [x] JSON 解析容错增强（10 种异常处理）
- [x] Tokyo Night 深色主题配色
- [x] 视频方向输入框（自由指定调性/风格）
- [x] 商品列表自适应高度（不再被刷新按钮遮挡）
- [x] 画面描述去噪（安全区描述 + 负向词自动去除）
- [x] 底部按钮精简为豆包图片/视频两个菜单按钮（中文/英文选择）
- [x] Agnes AI 视频生成接入（core/video_client.py + 设置 UI + 主窗口按钮）
- [x] Agnes 图生视频全链路（Agnes 图片生成→公网URL→视频生成，无需手动上传图床）
- [x] **统一生成管理器**（core/generation_manager.py）— 图片+视频统一入口，provider 可切换
- [x] 图片 provider 统一：comfyui/kontext/sd/dalle/flux/agnes 共用同一设置
- [x] 视频 provider 统一：agnes（通过 GenerationManager 调用）
- [x] 设置 UI 统一：图片和视频各 provider 共用一套地址/Key/模型设置
- [x] 图片生成按钮改为走 GenerationManager
- [x] 视频生成按钮改为走 GenerationManager
- [x] 按钮文案统一："生成图片" / "🎥 生成视频"
- [x] system_prompt 纯中文翻译约束
- [x] 单帧重新生成（每帧卡片有 🔄 按钮，不满意可单独重生该帧提示词，保留已生成图片）
- [x] 风格模板管理（设置对话框新增「🎨 风格模板」Tab，可增/删/复制/编辑模板，保存到 templates.json）
- [x] **镜头模板库**（camera_templates/camera_templates.yaml）— 3 个快节奏标准化镜头模板（快速推近碎裂/甩镜定格揭示/急速拉远全貌）
- [x] **镜头模板评分系统**（core/scoring.py）— 对照模板逐项打分，支持修正建议和反馈记录

- [x] **动作相位系统（motion_phase）**: pre-action/mid-action/post-action/static 四阶段，解决图片与视频提示词不一致问题

## 进行中
- [ ] V2 两步生成实测验证（基调质量 + 逐帧质量 vs 旧一次性生成）✅ transition 已验证
- [ ] 评分系统 UI 集成（生成后自动评分+修正建议展示）

## 待办
- [ ] 口味标签/负向词的端到端验证
- [ ] UI 小屏幕滚动体验优化

- [ ] 镜头模板扩充（慢节奏模板：缓慢推近/弧线环绕/微距焦点变换）
- [ ] 反馈记录驱动的模板自动优化

### 🔥 运镜与动态表现路线图
- [x] **VM-P0-1**: 运镜-动态联动规则 → camera_motion 与 motion_hint 强绑定
- [x] **VM-P0-2**: 运镜词汇库扩充 → 12+ 种运镜及场景适配
- [x] **VM-P1-1**: 运镜节奏编排规则 → 开场冲击→中段加速→结尾收稳
- [x] **VM-P1-2**: 速度曲线-帧时长绑定规则
- [x] **VM-P2-1**: 图片提示词描述框架（六层结构+材质词汇表+灯光方案）
- [x] **VM-P2-2**: 图片提示词 few-shot 案例库（4 类质感示例）
- [x] **VM-P2-3**: 多模型推理支持（多 provider 配置 + 设置 UI + 主窗口快捷切换）

### ✅ 视频提示词精细化路线图（已完成）
- [x] **VP-P0-1**: motion_hint 三要素规则
- [x] **VP-P0-2**: 豆包视频模板结构化升级
- [x] **VP-P1-1**: 新增 video_prompt / video_prompt_cn 独立字段
- [x] **VP-P1-2**: camera_motion 起止构图规则
- [x] **VP-P2-1**: 帧间连贯性指令
- [x] **VP-P2-2**: 负面动态描述

## 已知问题
- LLM 流式输出偶尔截断 → 已加固容错，待观察
- 请求日志已加入 llm_request_*.txt
- 帧5 image_prompt 偶发中英混杂（如「整齐」混入英文）→ 需在 frame_prompt 强化纯英文约束
- 帧3/4/6 未匹配镜头模板（只有 3 个快节奏模板，缺少静态/创意类模板）

## 关键文件
| 文件 | 职责 |
|------|------|
| core/generation_manager.py | 统一生成管理器（图片+视频） |
| core/video_client.py | Agnes AI 视频客户端（被 GenerationManager 调用） |
| core/image_client.py | 旧图片客户端（已由 GenerationManager 替代） |
| core/llm_client.py | LLM 客户端 + JSON 提取容错 |
| core/storyboard.py | 分镜生成 |
| core/templates.py | 风格模板 + JSON 加载 |
| core/prompt_loader.py | 提示词加载器 |
| core/product_parser.py | 商品解析 + Markdown 回写 |
| core/scoring.py | 镜头模板评分系统 |
| camera_templates/camera_templates.yaml | 镜头模板库（快节奏3模板） |
| camera_templates/feedback_log.md | 测试反馈记录 |

| ui/main_window.py | 主窗口界面 |
| prompts/*.md | 提示词模板 |

## 最近变更
- **07-25**: transition 字段丢失修复 + V2 实测通过：frame_prompt.md 新增 transition 强制约束（必须写入 plan 指定值、不得改为 none）+ 过渡接口描述要求（whip pan 产品从对侧滑入/fade 渐显描述/morph 承接形变）+ JSON 输出模板新增 transition 字段。两轮 V2 实测：首轮 transition 4/6 丢失为 none → 修复后第二轮 6/6 全部正确保留，5 种过渡接口描述全部到位（whip pan 右侧滑入+运动模糊/speed ramp 静止加速/fade 光晕渐显）。帧1 完美匹配 fast_push_shatter 模板 8 项全 PASS。残留问题：image_prompt_cn 偶发中英混杂（settles/crust 未翻译）
- **07-24**: 镜头模板库 + 评分系统：新建 camera_templates/ 目录（3 个快节奏 YAML 模板 + 反馈记录），新建 core/scoring.py（TemplateScorer 评分器 + record_feedback 反馈记录），新建 prompts/modules/scoring_prompt.md（评分 LLM 提示词）。模板包含标准化镜头维度+变量模板+8项评分标准（满分100，达标线85）
- **07-22**: 单帧重新生成功能：storyboard.py 新增 regenerate_frame() 函数复用 generate_frame_detail 逻辑（temperature=0.9），FrameCard 卡片加 🔄 按钮，StoryboardView 新增 frame_regenerate 信号 + update_frame_data 方法，MainWindow 新增 RegenerateFrameWorker + _on_frame_regenerate/_on_regen_finished/_on_regen_error 处理链
- **07-20**: 修复豆包图片复制英文提示词实际复制中文的 bug：`get_doubao_image_prompt`/`get_doubao_video_prompt` 新增 `lang` 参数直接选字段，去掉 `_copy_doubao_prompt` 中不可靠的后替换逻辑
- **07-20**: 修复 Agnes 图片生成 400 错误：去掉 `response_format` 参数（Agnes 不支持），改为检查 `b64_json`/`url` 值非空判断返回格式，超时从 120s 提升到 300s
- **07-20**: 统一生成接口架构：新建 GenerationManager 统一管图片和视频生成，provider 可切换（comfyui/kontext/sd/dalle/flux/agnes），图片和视频按钮统一走同一接口，设置 UI 统一，按钮文案改为"生成图片"/"生成视频"
- **07-20**: Agnes 图生视频全链路：video_client.py 新增 AgnesImageClient，VideoWorker 改为先调图片API拿公网URL再传给视频API，修正视频轮询为 GET /v1/videos/{task_id}
- **07-20**: 两步生成架构：generate_storyboard_v2（基调→逐帧精生成），新增 plan_prompt.md + frame_prompt.md 模板，UI 加 stage/frame_done 信号 + 进度条
- **07-20**: 系统提示词模块化重构：system_prompt.md 拆分为 core.md + 4 个质感模块 + camera_motion.md，prompt_loader 按商品质感自动组装，token 节省 46-68%
- **07-20**: VM-P0-1 + VM-P0-2 + VM-P1-1 + VM-P1-2 完成（运镜联动+词汇库16种+节奏编排+速度曲线绑定）
- **07-20**: 新建运镜与动态表现路线图（VM-P0~P2 共 7 项），安装 prompt-images + ai-image-prompts-skill 技能
- **07-19**: 视频提示词精细化 VP-P0-1 + VP-P0-2 + VP-P2-2 + VP-P1-1 + VP-P1-2 + VP-P2-1（全部完成）
- **07-19**: 底部按钮精简为豆包图片/视频两个菜单按钮 + 画面描述去噪 + 纯中文约束
- **07-18**: 视频提示词增强（画面描述+过渡+速度节奏）+ 视频方向输入框 + 商品列表修复 + 灵动冲击模板
- **07-18**: 帧时长 duration_plan 验证通过 + SpinBox UI 修复 + 请求日志
- **07-18**: JSON 解析容错增强 + STATUS.md 项目状态管理
- **07-17**: 提示词模板化 + 背景音乐 + 冲击强度/节奏策略
- **07-16**: 刷新按钮 + 商品信息回写 + 豆包视频提示词修改
- **07-15**: 项目创建，基础分镜生成
