from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.parser.docx_reader import _formula_text_is_weak, _should_use_formula_preview_image, read_docx_paragraphs


def _write_docx(path: Path, paragraph_xml: str) -> None:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {paragraph_xml}
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
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", root_rels_xml)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", root_rels_xml)


def test_read_docx_paragraphs_extracts_text_and_marks_assets():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))

    assert paragraphs[0].text.startswith("2025")
    assert any(p.has_image for p in paragraphs)
    assert any("A. 5\tB. 4\tC. 3\tD." in p.text for p in paragraphs)


def test_read_docx_paragraphs_preserves_inline_asset_order():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))

    paragraph = next(p for p in paragraphs if [item.kind for item in p.content_items] == ["text", "asset", "text"])

    assert [item.kind for item in paragraph.content_items] == ["text", "asset", "text"]
    assert len([item for item in paragraph.content_items if item.asset_ref]) == 1
    assert paragraph.content_items[0].text
    assert paragraph.content_items[-1].text


def test_read_docx_paragraphs_extracts_mathtype_equation_as_text():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))

    equation_paragraph = next(
        paragraph
        for paragraph in paragraphs
        if paragraph.has_formula and any(item.kind == "text" and item.text == "\u22121" for item in paragraph.content_items)
    )

    assert any(item.kind == "text" and item.text == "\u22121" for item in equation_paragraph.content_items)
    assert any(item.kind == "text" and item.source == "formula" for item in equation_paragraph.content_items)
    assert all(item.kind != "asset" for item in equation_paragraph.content_items)


def test_read_docx_paragraphs_keeps_mathtype_equations_as_text_without_preview_images():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))

    formula_paragraph = next(paragraph for paragraph in paragraphs if paragraph.has_formula)

    assert any(item.kind == "text" and item.text for item in formula_paragraph.content_items)
    assert any(item.kind == "text" and item.source == "formula" for item in formula_paragraph.content_items)
    assert all(item.kind != "asset" for item in formula_paragraph.content_items)


def test_formula_text_is_weak_keeps_single_symbol_formulas_as_text():
    assert _formula_text_is_weak("A") is False
    assert _formula_text_is_weak("AB") is False


def test_option_formula_text_does_not_fall_back_to_preview_images():
    assert _should_use_formula_preview_image("A", "A. 选项内容`tB. ", True) is False
    assert _should_use_formula_preview_image("B", "A. `tB. 选项内容", True) is False


def test_prime_marked_single_letter_formulas_stay_as_text():
    assert _formula_text_is_weak("A′") is False
    assert _should_use_formula_preview_image("A′", "过点", True) is False


def test_circle_symbol_label_formulas_stay_as_text():
    assert _should_use_formula_preview_image("⊙O", "以AB为直径的", True) is False


def test_malformed_fraction_chain_stays_as_formula_text():
    assert _should_use_formula_preview_image("(A′FBG)/(=)", "∴", True) is False


def test_read_docx_paragraphs_preserves_table_cell_paragraphs():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))

    table_paragraph = next(p for p in paragraphs if p.table_rows)

    assert table_paragraph.has_table
    assert len(table_paragraph.table_rows or []) == 2
    assert all(len(row) == 5 for row in table_paragraph.table_rows or [])


def test_read_docx_paragraphs_preserves_tabs_between_options():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))

    option_paragraph = next(p for p in paragraphs if p.text == "\t\t\tA. 5\tB. 4\tC. 3\tD. ")

    assert option_paragraph.text == "\t\t\tA. 5\tB. 4\tC. 3\tD. "


def test_read_docx_paragraphs_extracts_formula_text_blocks_for_options():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))

    option_paragraph = next(p for p in paragraphs if p.text == "\tA. \tB. ")

    assert any(item.kind == "text" and item.source == "formula" for item in option_paragraph.content_items)
    assert all(item.kind != "asset" for item in option_paragraph.content_items)


def test_read_docx_paragraphs_preserves_hard_line_breaks(tmp_path):
    fixture = tmp_path / "line-breaks.docx"
    _write_docx(
        fixture,
        """
<w:p>
  <w:r><w:t xml:space="preserve">First line</w:t></w:r>
  <w:r><w:br/></w:r>
  <w:r><w:t xml:space="preserve">Second line</w:t></w:r>
</w:p>
""".strip(),
    )

    paragraphs = read_docx_paragraphs(str(fixture))

    assert paragraphs[0].text == "First line\nSecond line"
    assert paragraphs[0].content_items[0].text == "First line\nSecond line"


def test_read_docx_paragraphs_preserves_docx_author_whitespace(tmp_path):
    fixture = tmp_path / "whitespace.docx"
    _write_docx(
        fixture,
        """
<w:p>
  <w:r><w:t xml:space="preserve">  padded text  </w:t></w:r>
</w:p>
""".strip(),
    )

    paragraphs = read_docx_paragraphs(str(fixture))

    assert paragraphs[0].text == "  padded text  "



