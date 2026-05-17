from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from app.parser import mathtype


def test_extract_mathtype_equation_text_recovers_formula_from_ole_stream():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with zipfile.ZipFile(fixture) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        rels_xml = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        rel_map = {relationship.get("Id"): relationship.get("Target") for relationship in rels_xml}
        equation_ref = next(
            node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            for node in document_xml.iter()
            if node.tag.endswith("}OLEObject") and node.get("ProgID") == "Equation.DSMT4"
        )
        ole_bytes = archive.read(f"word/{rel_map[equation_ref]}")

    text = mathtype.extract_mathtype_equation_text(ole_bytes)

    assert text is not None
    assert text == "\u22121"


def test_extract_mathtype_equation_text_uses_pure_python_fallback_when_pythoncom_is_missing(monkeypatch):
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with zipfile.ZipFile(fixture) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        rels_xml = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        rel_map = {relationship.get("Id"): relationship.get("Target") for relationship in rels_xml}
        equation_ref = next(
            node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            for node in document_xml.iter()
            if node.tag.endswith("}OLEObject") and node.get("ProgID") == "Equation.DSMT4"
        )
        ole_bytes = archive.read(f"word/{rel_map[equation_ref]}")

    monkeypatch.setattr(mathtype, "pythoncom", None)

    text = mathtype.extract_mathtype_equation_text(ole_bytes)

    assert text is not None
    assert text == "\u22121"


def test_extract_mathtype_equation_text_preserves_prime_superscripts():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with zipfile.ZipFile(fixture) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        rels_xml = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        rel_map = {relationship.get("Id"): relationship.get("Target") for relationship in rels_xml}
        equation_ref = next(
            node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            for node in document_xml.iter()
            if node.tag.endswith("}OLEObject")
            and node.get("ProgID") == "Equation.DSMT4"
            and node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") == "rId144"
        )
        ole_bytes = archive.read(f"word/{rel_map[equation_ref]}")

    text = mathtype.extract_mathtype_equation_text(ole_bytes)

    assert text is not None
    assert text == "\u25b3A\u2032BE"


def test_extract_mathtype_equation_text_recovers_embellished_option_formula():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with zipfile.ZipFile(fixture) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        rels_xml = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        rel_map = {relationship.get("Id"): relationship.get("Target") for relationship in rels_xml}
        equation_ref = next(
            node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            for node in document_xml.iter()
            if node.tag.endswith("}OLEObject")
            and node.get("ProgID") == "Equation.DSMT4"
            and node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") == "rId149"
        )
        ole_bytes = archive.read(f"word/{rel_map[equation_ref]}")

    text = mathtype.extract_mathtype_equation_text(ole_bytes)

    assert text is not None
    assert text == "A\u2032D\u2225BE"


def test_extract_mathtype_equation_text_recovers_root_formula_in_option_b():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with zipfile.ZipFile(fixture) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        rels_xml = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        rel_map = {relationship.get("Id"): relationship.get("Target") for relationship in rels_xml}
        equation_ref = next(
            node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            for node in document_xml.iter()
            if node.tag.endswith("}OLEObject")
            and node.get("ProgID") == "Equation.DSMT4"
            and node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") == "rId151"
        )
        ole_bytes = archive.read(f"word/{rel_map[equation_ref]}")

    text = mathtype.extract_mathtype_equation_text(ole_bytes)

    assert text is not None
    assert text == "A\u2032C=\u221a2A\u2032D"


def test_extract_mathtype_equation_text_recovers_analysis_formula_with_tail_eof():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with zipfile.ZipFile(fixture) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        rels_xml = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        rel_map = {relationship.get("Id"): relationship.get("Target") for relationship in rels_xml}
        equation_ref = next(
            node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            for node in document_xml.iter()
            if node.tag.endswith("}OLEObject")
            and node.get("ProgID") == "Equation.DSMT4"
            and node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") == "rId245"
        )
        ole_bytes = archive.read(f"word/{rel_map[equation_ref]}")

    text = mathtype.extract_mathtype_equation_text(ole_bytes)

    assert text is not None
    assert text == "∠EFA\u2032=∠A\u2032GB=∠EA\u2032B=90°"


def test_extract_mathtype_equation_text_formats_fraction_without_outer_parentheses():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with zipfile.ZipFile(fixture) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        rels_xml = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        rel_map = {relationship.get("Id"): relationship.get("Target") for relationship in rels_xml}
        equation_ref = next(
            node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            for node in document_xml.iter()
            if node.tag.endswith("}OLEObject")
            and node.get("ProgID") == "Equation.DSMT4"
            and node.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") == "rId255"
        )
        ole_bytes = archive.read(f"word/{rel_map[equation_ref]}")

    text = mathtype.extract_mathtype_equation_text(ole_bytes)

    assert text is not None
    assert text == "A\u2032F=1/2BG=1/2(10\u2212x)"
