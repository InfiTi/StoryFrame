"""镜头模板评分系统

对照镜头模板的评分标准，对 LLM 生成的分镜提示词逐项打分。
支持自动评分 + 修正建议 + 反馈记录。

用法：
    from core.scoring import TemplateScorer
    scorer = TemplateScorer()
    result = scorer.score(frame_dict, template_id="fast_push_shatter")
    if not result.passed:
        print(result.fixes)
"""

import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from .llm_client import LLMClient

CAMERA_TEMPLATES_FILE = Path(__file__).parent.parent / "camera_templates" / "camera_templates.yaml"
FEEDBACK_LOG_FILE = Path(__file__).parent.parent / "camera_templates" / "feedback_log.md"
SCORING_PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "modules" / "scoring_prompt.md"


@dataclass
class ItemScore:
    """单项评分"""
    criterion: str
    weight: int
    score: int
    reason: str
    fix: str = ""


@dataclass
class ScoreResult:
    """评分结果"""
    total_score: int
    max_score: int
    passed: bool
    item_scores: List[ItemScore] = field(default_factory=list)
    summary: str = ""
    fixes: List[str] = field(default_factory=list)
    raw_response: str = ""


@dataclass
class CameraTemplate:
    """镜头模板"""
    id: str
    name: str
    category: str
    applicable_scene: str
    dimensions: dict
    image_prompt_template: str
    motion_hint_template: str
    camera_motion_template: str
    video_prompt_template: str
    variables: dict
    scoring_criteria: List[dict]


def load_camera_templates() -> List[CameraTemplate]:
    """加载镜头模板库"""
    if not CAMERA_TEMPLATES_FILE.exists():
        return []
    data = yaml.safe_load(CAMERA_TEMPLATES_FILE.read_text(encoding="utf-8"))
    templates = []
    for item in data or []:
        templates.append(CameraTemplate(
            id=item["id"],
            name=item["name"],
            category=item.get("category", ""),
            applicable_scene=item.get("适用场景", item.get("applicable_scene", "")),
            dimensions=item.get("dimensions", {}),
            image_prompt_template=item.get("image_prompt_template", ""),
            motion_hint_template=item.get("motion_hint_template", ""),
            camera_motion_template=item.get("camera_motion_template", ""),
            video_prompt_template=item.get("video_prompt_template", ""),
            variables=item.get("variables", {}),
            scoring_criteria=item.get("scoring_criteria", []),
        ))
    return templates


def get_camera_template(template_id: str) -> Optional[CameraTemplate]:
    """根据 ID 获取镜头模板"""
    for t in load_camera_templates():
        if t.id == template_id:
            return t
    return None


class TemplateScorer:
    """镜头模板评分器"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def score(self, frame: dict, template_id: str) -> ScoreResult:
        """对单帧提示词进行评分

        Args:
            frame: 分镜帧字典（包含 image_prompt, motion_hint, camera_motion 等字段）
            template_id: 镜头模板 ID

        Returns:
            ScoreResult 评分结果
        """
        template = get_camera_template(template_id)
        if not template:
            return ScoreResult(
                total_score=0, max_score=100, passed=False,
                summary=f"未找到模板: {template_id}",
                fixes=["检查模板 ID 是否正确"],
            )

        # 构建评分 prompt
        scoring_system = SCORING_PROMPT_FILE.read_text(encoding="utf-8") if SCORING_PROMPT_FILE.exists() else ""

        # 模板信息（只传评分标准和维度，不传完整模板文本）
        template_info = {
            "template_id": template.id,
            "template_name": template.name,
            "dimensions": template.dimensions,
            "scoring_criteria": template.scoring_criteria,
        }

        user_msg = (
            f"## 镜头模板信息\n```json\n{json.dumps(template_info, ensure_ascii=False, indent=2)}\n```\n\n"
            f"## 待评审的分镜帧\n```json\n{json.dumps(frame, ensure_ascii=False, indent=2)}\n```\n\n"
            f"请按评分标准逐项打分，输出 JSON。"
        )

        # 调用 LLM 评分
        response = self.llm.chat(
            system_prompt=scoring_system,
            user_prompt=user_msg,
            stream=False,
        )

        # 解析评分结果
        return self._parse_score_response(response, template)

    def score_frames(self, frames: List[dict], template_id: str) -> List[ScoreResult]:
        """对多帧提示词批量评分"""
        return [self.score(f, template_id) for f in frames]

    def _parse_score_response(self, response: str, template: CameraTemplate) -> ScoreResult:
        """解析 LLM 返回的评分 JSON"""
        max_score = sum(c["weight"] for c in template.scoring_criteria) or 100

        try:
            # 尝试提取 JSON
            from .llm_client import extract_json
            data = extract_json(response)
            if isinstance(data, dict):
                total = data.get("total_score", 0)
                passed = data.get("passed", total >= 85)
                items = []
                for item in data.get("item_scores", []):
                    items.append(ItemScore(
                        criterion=item.get("criterion", ""),
                        weight=item.get("weight", 0),
                        score=item.get("score", 0),
                        reason=item.get("reason", ""),
                        fix=item.get("fix", ""),
                    ))
                return ScoreResult(
                    total_score=total,
                    max_score=max_score,
                    passed=passed,
                    item_scores=items,
                    summary=data.get("summary", ""),
                    fixes=data.get("fixes", []),
                    raw_response=response,
                )
        except Exception:
            pass

        # 解析失败
        return ScoreResult(
            total_score=0, max_score=max_score, passed=False,
            summary="评分解析失败，LLM 返回格式异常",
            fixes=["检查 LLM 返回是否为有效 JSON"],
            raw_response=response,
        )


def record_feedback(template_id: str, product_name: str, score: int,
                     feeling: str, improvement: str):
    """记录测试反馈到 feedback_log.md

    Args:
        template_id: 镜头模板 ID
        product_name: 商品名称
        score: 本次评分
        feeling: 使用感受（一句话）
        improvement: 改进方向（一句话）
    """
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    if not FEEDBACK_LOG_FILE.exists():
        FEEDBACK_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        FEEDBACK_LOG_FILE.write_text(
            "# 镜头模板反馈记录\n\n"
            "| 日期 | 模板 | 商品 | 评分 | 感受 | 改进方向 |\n"
            "|------|------|------|------|------|----------|\n",
            encoding="utf-8",
        )

    content = FEEDBACK_LOG_FILE.read_text(encoding="utf-8")
    # 在表格末尾（示例行之前）插入新行
    lines = content.split("\n")
    new_row = f"| {today} | {template_id} | {product_name} | {score} | {feeling} | {improvement} |"

    # 找到最后一个 | 开头的行，在其后插入
    last_table_line = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and not line.strip().startswith("|--") and not line.strip().startswith("| -"):
            last_table_line = i

    if last_table_line >= 0:
        lines.insert(last_table_line + 1, new_row)
        FEEDBACK_LOG_FILE.write_text("\n".join(lines), encoding="utf-8")


def get_feedback_history(template_id: str = "") -> List[str]:
    """获取某个模板的反馈历史（或全部反馈）"""
    if not FEEDBACK_LOG_FILE.exists():
        return []
    content = FEEDBACK_LOG_FILE.read_text(encoding="utf-8")
    lines = [l for l in content.split("\n") if l.strip().startswith("|") and "---" not in l and "日期" not in l and l.strip() != "| - | - | - | - | - | - |"]
    if template_id:
        lines = [l for l in lines if template_id in l]
    return lines
