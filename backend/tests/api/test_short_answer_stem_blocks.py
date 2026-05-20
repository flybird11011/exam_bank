from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import zipfile

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


def test_short_answer_media_bearing_end_marker_paragraph_keeps_image(monkeypatch):
    paragraphs = [
        DocxParagraph(
            index=0,
            text="29. short_answer stem intro",
            raw_xml="<w:p/>",
            content_items=[DocxContentItem(kind="text", text="29. short_answer stem intro")],
        ),
        DocxParagraph(
            index=1,
            text="答案",
            raw_xml="<w:p/>",
            has_image=True,
            asset_refs=["rId9"],
            content_items=[
                DocxContentItem(kind="text", text="答案"),
                DocxContentItem(kind="asset", asset_ref="rId9"),
            ],
        ),
    ]

    monkeypatch.setattr(
        import_service,
        "_store_media_asset",
        lambda **_kwargs: {
            "id": "asset-1",
            "storage_url": "/media/paper-1/question-1/image.png",
            "file_name": "image.png",
            "original_file_name": "image.png",
        },
    )

    with TemporaryDirectory() as temp_dir:
        archive_path = Path(temp_dir) / "empty.zip"
        with zipfile.ZipFile(archive_path, "w"):
            pass

        with zipfile.ZipFile(archive_path) as archive:
            blocks = import_service._build_stem_blocks(
                session=DummySession(),
                archive=archive,
                relationships={"rId9": "media/image1.png"},
                paper_id="paper-1",
                question_id="question-1",
                question_paragraphs=paragraphs,
                question_type="short_answer",
            )

    assert [block["kind"] for block in blocks] == ["text", "image"]
    assert blocks[1]["asset_ref"] == "rId9"
