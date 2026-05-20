from types import SimpleNamespace

import pytest

from app.parser.types import DocxContentItem, DocxParagraph
from app.services import import_service


class DummySession:
    def add(self, _obj):
        return None


def test_build_stem_blocks_keeps_formula_text_items_without_ocr(monkeypatch):
    paragraph = DocxParagraph(
        index=0,
        text="f(x)=x^2+1",
        raw_xml="<w:p/>",
        content_items=[
            DocxContentItem(kind="text", text="f(x)="),
            DocxContentItem(kind="text", text="x^2+1", source="formula"),
            DocxContentItem(kind="asset", asset_ref="rId1"),
        ],
    )

    stored_asset = {
        "id": "asset-1",
        "file_name": "inline.png",
        "storage_url": "/media/paper-1/question-1/inline.png",
        "original_file_name": "inline.emf",
    }

    monkeypatch.setattr(import_service, "_stem_paragraphs", lambda paragraphs, question_type=None: paragraphs)
    monkeypatch.setattr(import_service, "_store_media_asset", lambda **_kwargs: stored_asset)

    numeric_calls: list[str] = []

    def fake_numeric(path):
        numeric_calls.append(str(path))
        return None

    monkeypatch.setattr(import_service, "recognize_small_numeric_image", fake_numeric)

    blocks = import_service._build_stem_blocks(
        session=DummySession(),
        archive=SimpleNamespace(),
        relationships={},
        paper_id="paper-1",
        question_id="question-1",
        question_paragraphs=[paragraph],
    )

    assert blocks[0] == {"kind": "text", "text": "f(x)="}
    assert blocks[1] == {"kind": "text", "text": "x^2+1", "source": "formula"}
    assert blocks[2]["kind"] == "image"
    assert numeric_calls == []


def test_build_stem_blocks_keeps_table_paragraphs_even_when_table_text_looks_like_options(monkeypatch):
    table_paragraph = DocxParagraph(
        index=0,
        text="A. 图 A\tB. 图 B\tC. 图 C\tD. 图 D",
        raw_xml="<w:tbl/>",
        has_table=True,
        table_rows=[["A. 图 A", "B. 图 B", "C. 图 C", "D. 图 D"]],
        content_items=[DocxContentItem(kind="text", text="A. 图 A\tB. 图 B\tC. 图 C\tD. 图 D")],
    )
    option_paragraph = DocxParagraph(
        index=1,
        text="A. 亭台在水中的“倒影”A\tB. 碧水中变浅的“池底”B\tC. 漏窗在墙壁上的“影子”C\tD. 夕阳下水中的“太阳”D",
        raw_xml="<w:p/>",
        content_items=[
            DocxContentItem(kind="text", text="A. 亭台在水中的“倒影”A\tB. 碧水中变浅的“池底”B\tC. 漏窗在墙壁上的“影子”C\tD. 夕阳下水中的“太阳”D")
        ],
    )

    monkeypatch.setattr(import_service, "_store_media_asset", lambda **_kwargs: None)
    monkeypatch.setattr(import_service, "recognize_small_numeric_image", lambda _path: None)

    blocks = import_service._build_stem_blocks(
        session=DummySession(),
        archive=SimpleNamespace(),
        relationships={},
        paper_id="paper-1",
        question_id="question-1",
        question_paragraphs=[table_paragraph, option_paragraph],
    )

    assert blocks[0]["kind"] == "table"
    assert blocks[0]["rows"] == [["A. 图 A", "B. 图 B", "C. 图 C", "D. 图 D"]]


def test_build_analysis_blocks_uses_small_text_ocr_for_inline_images(monkeypatch):
    paragraph = DocxParagraph(
        index=0,
        text="【详解】∴摩天轮半径为",
        raw_xml="<w:p/>",
        content_items=[
            DocxContentItem(kind="text", text="【详解】∴摩天轮"),
            DocxContentItem(kind="asset", asset_ref="rId1"),
            DocxContentItem(kind="text", text="半径为"),
        ],
    )

    stored_asset = {
        "id": "asset-1",
        "file_name": "inline.png",
        "storage_url": "/media/paper-1/question-1/inline.png",
        "original_file_name": "inline.wmf",
    }

    monkeypatch.setattr(import_service, "_store_media_asset", lambda **_kwargs: stored_asset)
    monkeypatch.setattr(import_service, "recognize_small_text_image", lambda _path: "-")

    blocks = import_service._build_analysis_blocks(
        session=DummySession(),
        archive=SimpleNamespace(),
        relationships={},
        paper_id="paper-1",
        question_id="question-1",
        question_paragraphs=[paragraph],
    )

    assert all(block["kind"] == "text" for block in blocks)
    assert "".join(block["text"] for block in blocks) == "∴摩天轮的半径为"
@pytest.mark.skip(reason="covered by ascii regression test")
def test_build_stem_blocks_keeps_option_like_paragraphs_inside_short_answer_stems(monkeypatch):
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
            text="继续题干内容",
            raw_xml="<w:p/>",
            content_items=[DocxContentItem(kind="text", text="继续题干内容")],
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
        "继续题干内容",
        "【答案】",
    ]
