from dataclasses import dataclass


@dataclass(slots=True)
class TagSuggestion:
    tag_type: str
    name: str
    source: str
    confidence: float

