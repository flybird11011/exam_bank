from __future__ import annotations

import re
from dataclasses import asdict

from app.tagging.types import TagSuggestion


def generate_paper_tags(lines: list[str]) -> list[dict]:
    text = "\n".join(lines)
    tags = [TagSuggestion("subject", "数学", "rule", 1.0)]

    if "选择题" in text:
        tags.append(TagSuggestion("feature", "含选择题", "rule", 1.0))
    if "填空题" in text:
        tags.append(TagSuggestion("feature", "含填空题", "rule", 1.0))
    if "解答题" in text:
        tags.append(TagSuggestion("feature", "含解答题", "rule", 1.0))

    return [asdict(tag) for tag in tags]


def generate_question_tags(question_text: str, question_type: str) -> list[dict]:
    text = question_text
    tags = [TagSuggestion("question_type", question_type, "rule", 0.99)]

    if any(marker in text for marker in ("图", "如图", "示意图", "坐标")):
        tags.append(TagSuggestion("feature", "含图片或图形", "rule", 0.92))
    if any(marker in text for marker in ("表", "表格", "统计", "数据")):
        tags.append(TagSuggestion("feature", "含表格", "rule", 0.88))
    if any(marker in text for marker in ("=", "∠", "△", "π", "x", "y")):
        tags.append(TagSuggestion("feature", "含公式或符号", "rule", 0.75))

    if question_type == "single_choice":
        tags.append(TagSuggestion("difficulty", "简单", "model", 0.82))
    elif question_type == "fill_blank":
        tags.append(TagSuggestion("difficulty", "中等", "model", 0.78))
    else:
        tags.append(TagSuggestion("difficulty", "较难", "model", 0.72))

    return [asdict(tag) for tag in tags]
