# StoryFrame 🎬 分镜图生成器

专为零食带货短视频设计的分镜设计工具，服务于"图生视频"工作流。

## 功能

- 📝 输入产品信息 + 选择风格模板 → AI 生成分镜脚本
- 🎨 8种预置风格：高端、升格、慢镜头、超近距离、日系清新、国潮、活力动感、温暖治愈
- 🖼️ 一键生成全部分镜图片（支持 DALL-E / Flux / Stable Diffusion）
- 📋 每帧包含：图片提示词（英文）+ 镜头运动描述（英文）+ 画面描述（中文）
- 📦 导出 JSON / Markdown / 完整包（含图片）

## 安装

```bash
cd E:\AI\StoryFrame
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 配置

### LLM 设置
- **LMStudio（本地）**：API 地址填 `http://localhost:1234/v1`，API Key 填 `lm-studio`，模型名填你加载的模型
- **远程 API**：填入对应 API 地址和 Key 即可（需兼容 OpenAI 格式）

### 图片生成设置
- **DALL-E**：填入 OpenAI API 地址和 Key
- **Flux**：兼容 OpenAI 格式的 Flux API
- **Stable Diffusion**：填入 SD WebUI 地址（默认 `http://localhost:7860`）

## 使用流程

1. 填写零食名称、产品描述、卖点
2. 选择风格模板（如"高端"、"超近距离"等）
3. 设置分镜数和总时长
4. 点击「生成分镜脚本」→ AI 生成各帧的提示词和镜头描述
5. 点击「生成全部图片」→ 逐帧生成分镜图
6. 导出 JSON / Markdown / 完整包

## 工作流说明

```
产品信息 → LLM 生成提示词 → 图片API生成分镜图 → 图生视频
           (每帧含图片提示词     (确定角度和画面)     (按镜头描述运动)
            + 镜头运动描述)
```

## 项目结构

```
StoryFrame/
├── main.py              # 入口
├── config.py            # 配置管理
├── requirements.txt     # 依赖
├── core/
│   ├── llm_client.py    # LLM 客户端（OpenAI 兼容）
│   ├── image_client.py  # 图片生成客户端
│   ├── storyboard.py    # 分镜脚本生成
│   ├── templates.py     # 风格模板定义
│   └── exporter.py      # 导出功能
├── ui/
│   ├── main_window.py   # 主窗口
│   ├── settings_dialog  # 设置对话框
│   └── storyboard_view  # 分镜时间轴
└── outputs/             # 生成的图片和JSON
```
