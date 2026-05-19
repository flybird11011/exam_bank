from app.parser.types import DocxParagraph


def normalize_paragraphs(paragraphs: list[DocxParagraph]) -> list[DocxParagraph]:
    normalized: list[DocxParagraph] = []
    for paragraph in paragraphs:
        normalized.append(
            DocxParagraph(
                index=paragraph.index,
                text=paragraph.text,
                raw_xml=paragraph.raw_xml,
                has_image=paragraph.has_image,
                has_table=paragraph.has_table,
                has_formula=paragraph.has_formula,
                table_rows=[list(row) for row in paragraph.table_rows] if paragraph.table_rows else None,
                table_cells=
                [
                    [
                        list(cell_items)
                        for cell_items in row
                    ]
                    for row in paragraph.table_cells
                ]
                if paragraph.table_cells
                else None,
                asset_refs=list(paragraph.asset_refs),
                content_items=list(paragraph.content_items),
            )
        )
    return normalized
