from app.parser.types import DocxParagraph
from app.services.import_service import _derive_paper_title, build_paper_title


def test_structured_title_wins_over_docx_title_candidate():
    paragraphs = [
        DocxParagraph(
            index=0,
            text="2025年苏州市中考物理试卷",
            raw_xml="<w:p />",
        )
    ]

    assert _derive_paper_title(
        paragraphs,
        subject="物理",
        region="苏州",
        exam_year=2025,
        exam_type="中考",
        source_file_name="2025-suzhou-physics.docx",
    ) == build_paper_title("物理", "苏州", 2025, "中考")

