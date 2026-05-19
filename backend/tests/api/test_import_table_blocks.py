from base64 import b64decode
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import zipfile

from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app
from app.parser.docx_reader import read_docx_paragraphs
from app.services import import_service


def test_import_exposes_table_blocks_for_question_seven():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with TestClient(app) as client:
        with fixture.open("rb") as f:
            response = client.post(
                "/api/papers/import",
                files={
                    "file": (
                        "2025-suzhou-math-exam.docx",
                        f,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={
                    "subject": "math",
                    "region": "suzhou",
                    "exam_year": 2025,
                    "exam_type": "exam",
                },
            )
        paper_id = response.json()["paper"]["paper_id"]
        detail = client.get(f"/api/papers/{paper_id}").json()

    seventh_question = detail["sections"][0]["questions"][6]
    stem_blocks = seventh_question["stem_blocks"]

    table_block = next(block for block in stem_blocks if block["kind"] == "table")

    assert table_block["rows"][0][0]["text"] == "温度t(°C)"
    assert table_block["rows"][0][0]["blocks"][1]["source"] == "formula"
    assert table_block["rows"][0][1]["text"] == "−10"
    assert table_block["rows"][0][1]["blocks"] == [{"kind": "text", "text": "−10", "source": "formula"}]
    assert table_block["rows"][1][0]["text"] == "声音传播的速度v(m/s)"
    assert table_block["rows"][1][0]["blocks"][1]["source"] == "formula"
    assert table_block["rows"][1][1:] == [
        {"text": "324", "blocks": [{"kind": "text", "text": "324"}]},
        {"text": "330", "blocks": [{"kind": "text", "text": "330"}]},
        {"text": "336", "blocks": [{"kind": "text", "text": "336"}]},
        {"text": "348", "blocks": [{"kind": "text", "text": "348"}]},
    ]


def test_build_stem_blocks_falls_back_when_table_cells_attribute_is_missing():
    paragraph = SimpleNamespace(
        text="表格题干",
        table_rows=[["A", "B"]],
    )

    with TemporaryDirectory() as temp_dir:
        archive_path = Path(temp_dir) / "empty.zip"
        with zipfile.ZipFile(archive_path, "w"):
            pass

        with zipfile.ZipFile(archive_path) as archive, get_session() as session:
            blocks = import_service._build_stem_blocks(
                session=session,
                archive=archive,
                relationships={},
                paper_id="paper-1",
                question_id="question-1",
                question_paragraphs=[paragraph],
            )

    assert blocks[0]["kind"] == "table"
    assert blocks[0]["rows"] == [["A", "B"]]


def _write_docx_with_table_image(path: Path) -> None:
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <w:body>
    <w:tbl>
      <w:tr>
        <w:tc>
          <w:p>
            <w:r><w:t>A</w:t></w:r>
          </w:p>
        </w:tc>
        <w:tc>
          <w:p>
            <w:r>
              <w:drawing>
                <a:graphic>
                  <a:graphicData>
                    <a:pic>
                      <a:blipFill>
                        <a:blip r:embed="rId2"/>
                      </a:blipFill>
                    </a:pic>
                  </a:graphicData>
                </a:graphic>
              </w:drawing>
            </w:r>
          </w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    document_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>
"""
    png_bytes = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO4N0d0AAAAASUVORK5CYII=")

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", root_rels_xml)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", document_rels_xml)
        archive.writestr("word/media/image1.png", png_bytes)


def test_build_stem_blocks_rebuilds_table_cells_from_raw_xml_for_image_tables():
    with TemporaryDirectory() as temp_dir:
        fixture = Path(temp_dir) / "table-image.docx"
        _write_docx_with_table_image(fixture)
        table_paragraph = next(p for p in read_docx_paragraphs(str(fixture)) if p.table_rows)
        legacy_paragraph = SimpleNamespace(
            text=table_paragraph.text,
            raw_xml=table_paragraph.raw_xml,
            table_rows=table_paragraph.table_rows,
        )

        with zipfile.ZipFile(fixture) as archive, get_session() as session:
            blocks = import_service._build_stem_blocks(
                session=session,
                archive=archive,
                relationships={"rId2": "media/image1.png"},
                paper_id="paper-1",
                question_id="question-1",
                question_paragraphs=[legacy_paragraph],
            )

    assert blocks[0]["kind"] == "table"
    assert blocks[0]["rows"][0][1]["blocks"][0]["kind"] == "image"


def test_build_stem_blocks_rebuilds_when_table_cells_have_legacy_string_shape():
    with TemporaryDirectory() as temp_dir:
        fixture = Path(temp_dir) / "table-image.docx"
        _write_docx_with_table_image(fixture)
        table_paragraph = next(p for p in read_docx_paragraphs(str(fixture)) if p.table_rows)
        legacy_paragraph = SimpleNamespace(
            text=table_paragraph.text,
            raw_xml=table_paragraph.raw_xml,
            table_rows=table_paragraph.table_rows,
            table_cells=[["A", ""]],
        )

        with zipfile.ZipFile(fixture) as archive, get_session() as session:
            blocks = import_service._build_stem_blocks(
                session=session,
                archive=archive,
                relationships={"rId2": "media/image1.png"},
                paper_id="paper-1",
                question_id="question-1",
                question_paragraphs=[legacy_paragraph],
            )

    assert blocks[0]["kind"] == "table"
    assert blocks[0]["rows"][0][1]["blocks"][0]["kind"] == "image"


def test_rebuild_table_cells_ignores_extra_return_items_from_table_extractor(monkeypatch):
    paragraph = SimpleNamespace(
        text="表格题干",
        raw_xml='<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
    )

    def fake_extract_table_rows(*args, **kwargs):
        return (["row-text"], [[["cell"]]], "extra")

    monkeypatch.setattr(import_service, "_extract_table_rows", fake_extract_table_rows)

    with TemporaryDirectory() as temp_dir:
        archive_path = Path(temp_dir) / "empty.zip"
        with zipfile.ZipFile(archive_path, "w"):
            pass

        with zipfile.ZipFile(archive_path) as archive:
            cells = import_service._rebuild_table_cells_from_raw_xml(paragraph, archive, {})

    assert cells == [[["cell"]]]
