from types import SimpleNamespace

from app.parser.types import DocxContentItem, DocxParagraph
from app.services import import_service


class DummySession:
    def add(self, _obj):
        return None


def test_short_answer_stems_do_not_stop_at_option_like_paragraphs(monkeypatch):
    paragraphs = [
        DocxParagraph(
            index=0,
            text="32. short_answer stem intro",
            raw_xml="<w:p/>",
            content_items=[DocxContentItem(kind="text", text="32. short_answer stem intro")],
        ),
        DocxParagraph(
            index=1,
            text="A. embedded choice-like paragraph should stay in the stem",
            raw_xml="<w:p/>",
            content_items=[
                DocxContentItem(kind="text", text="A. embedded choice-like paragraph should stay in the stem")
            ],
        ),
        DocxParagraph(
            index=2,
            text="continue stem content",
            raw_xml="<w:p/>",
            content_items=[DocxContentItem(kind="text", text="continue stem content")],
        ),
        DocxParagraph(
            index=3,
            text="【答案】",
            raw_xml="<w:p/>",
            content_items=[DocxContentItem(kind="text", text="【答案】")],
        ),
    ]

    monkeypatch.setattr(import_service, "_store_media_asset", lambda **_kwargs: None)
    monkeypatch.setattr(import_service, "recognize_small_numeric_image", lambda _path: None)

    blocks = import_service._build_stem_blocks(
        session=DummySession(),
        archive=SimpleNamespace(),
        relationships={},
        paper_id="paper-1",
        question_id="question-1",
        question_paragraphs=paragraphs,
        question_type="short_answer",
    )

    assert [block["text"] for block in blocks] == [
        "32. short_answer stem intro",
        "A. embedded choice-like paragraph should stay in the stem",
        "continue stem content",
    ]
