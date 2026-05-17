# Question Stem Image Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve and render images that belong to a question stem so the review page shows the original mixed text-and-image content in order.

**Architecture:** Extend DOCX parsing to capture inline stem content as ordered blocks, not just plain text. Persist extracted media on disk, transcode non-web-friendly stem images such as `WMF` to browser-displayable `PNG` when needed, reference them from `media_asset`, and return structured stem blocks from the paper detail API so the frontend can render text and images in sequence. Keep the existing plain-text fields for search and fallback behavior.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, SQLite, Vite, React 19, TypeScript.

---

### Task 1: Extract ordered stem content from DOCX paragraphs

**Files:**
- Modify: `backend/app/parser/types.py`
- Modify: `backend/app/parser/docx_reader.py`
- Test: `backend/tests/parser/test_docx_reader.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from app.parser.docx_reader import read_docx_paragraphs


def test_docx_reader_marks_paragraphs_with_inline_assets():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    paragraphs = read_docx_paragraphs(str(fixture))

    assert any(paragraph.has_image for paragraph in paragraphs)
    assert any(paragraph.asset_refs for paragraph in paragraphs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/parser/test_docx_reader.py -v`
Expected: fail because paragraphs currently only expose `has_image` and do not preserve ordered inline asset references.

- [ ] **Step 3: Write minimal implementation**

Implement ordered content capture in the DOCX reader:

```python
from dataclasses import dataclass, field


@dataclass(slots=True)
class DocxContentItem:
    kind: str
    text: str | None = None
    asset_ref: str | None = None


@dataclass(slots=True)
class DocxParagraph:
    index: int
    text: str
    raw_xml: str
    has_image: bool = False
    has_table: bool = False
    has_formula: bool = False
    asset_refs: list[str] = field(default_factory=list)
    content_items: list[DocxContentItem] = field(default_factory=list)
```

Parse `word/document.xml` together with `word/_rels/document.xml.rels`, identify inline drawing runs in each paragraph, and populate `content_items` in source order so the stem can later be rebuilt as mixed content.
For image assets that are not browser-displayable, write a PNG derivative alongside the original binary and point the review page at the PNG URL.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/parser/test_docx_reader.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/parser/types.py backend/app/parser/docx_reader.py backend/tests/parser/test_docx_reader.py
git commit -m "feat: preserve stem image references during docx parsing"
```

### Task 2: Persist extracted stem media and structured blocks

**Files:**
- Modify: `backend/app/services/import_service.py`
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_import_api.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_import_persists_stem_media_and_content_blocks():
    client = TestClient(app)
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with fixture.open("rb") as f:
        response = client.post(
            "/api/papers/import",
            files={"file": ("2025-suzhou-math-exam.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"subject": "数学", "region": "江苏省苏州市", "exam_year": 2025, "exam_type": "中考真题"},
        )

    assert response.status_code == 200
    body = response.json()
    first_question = body["paper"]["sections"][0]["questions"][0]
    assert "stem_blocks" in first_question
    assert any(block["kind"] == "image" for block in first_question["stem_blocks"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/api/test_import_api.py -v`
Expected: fail because the import response still only includes `stem_text`.

- [ ] **Step 3: Write minimal implementation**

Store stem content as ordered rows and media assets:

```python
# backend/app/services/import_service.py
from pathlib import Path
from uuid import uuid4

def _media_root() -> Path:
    return Path(__file__).resolve().parents[2] / "media"

def _store_media_asset(paper_id: str, question_id: str, file_name: str, payload: bytes) -> str:
    media_dir = _media_root() / paper_id / question_id
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / file_name
    target.write_bytes(payload)
    return f"/media/{paper_id}/{question_id}/{file_name}"
```

During import, create:
- one `content_block` row per stem text/image chunk in original order
- one `media_asset` row per extracted image
- a `stem_json` payload on `question` containing the ordered block references

Add a `/media` static mount in `backend/app/main.py` that serves the media directory so the frontend can display images directly.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/api/test_import_api.py -v`
Expected: pass, and the first question in the returned paper payload exposes stem block metadata.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/import_service.py backend/app/db/models.py backend/app/main.py backend/tests/api/test_import_api.py
git commit -m "feat: persist stem media and structured content blocks"
```

### Task 3: Render mixed stem content in the review page

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/ReviewPage.tsx`
- Modify: `frontend/src/components/QuestionPanel.tsx` if needed for block rendering
- Test: `frontend/src/__tests__/ReviewPage.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { test, expect } from "vitest";

test("renders stem image blocks in order", async () => {
  render(<ReviewPage />);

  expect(await screen.findByAltText("题干图片")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- --run src/__tests__/ReviewPage.test.tsx`
Expected: fail because the page only renders `stem_text`.

- [ ] **Step 3: Write minimal implementation**

Extend the API types to include structured blocks:

```ts
export type StemBlock =
  | { kind: "text"; text: string }
  | { kind: "image"; url: string; alt: string };

export type PaperQuestion = {
  id: string;
  question_no: string;
  question_type: string;
  stem_text: string | null;
  stem_blocks?: StemBlock[];
  answer_text: string | null;
  analysis_text: string | null;
  confidence: number | null;
  status: string;
};
```

Render `stem_blocks` in `ReviewPage` in sequence:

```tsx
function renderStemBlocks(blocks: StemBlock[] | undefined, fallbackText: string) {
  if (!blocks || blocks.length === 0) {
    return <p>{fallbackText}</p>;
  }

  return blocks.map((block, index) =>
    block.kind === "text" ? (
      <p key={index}>{block.text}</p>
    ) : (
      <img key={index} src={block.url} alt={block.alt} className="stem-image" />
    ),
  );
}
```

Keep the existing plain-text editor fields intact so reviewers can still edit `stem_text`, but show the image blocks above the editor so the visual source is obvious.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- --run src/__tests__/ReviewPage.test.tsx`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/pages/ReviewPage.tsx frontend/src/__tests__/ReviewPage.test.tsx
git commit -m "feat: render stem images in review page"
```

### Task 4: Verify end-to-end import and review behavior

**Files:**
- Modify: `backend/tests/e2e/test_sample_import.py`
- Modify: `backend/tests/e2e/test_sample_search.py` if the new payload affects search output

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


def test_imported_paper_exposes_stem_image_blocks_in_detail_api():
    client = TestClient(app)
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with fixture.open("rb") as f:
        response = client.post(
            "/api/papers/import",
            files={"file": ("2025-suzhou-math-exam.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"subject": "数学", "region": "江苏省苏州市", "exam_year": 2025, "exam_type": "中考真题"},
        )

    paper_id = response.json()["paper"]["paper_id"]
    detail = client.get(f"/api/papers/{paper_id}")

    assert detail.status_code == 200
    question = detail.json()["sections"][0]["questions"][0]
    assert question["stem_blocks"][1]["kind"] == "image"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/e2e/test_sample_import.py -v`
Expected: fail until the detail API returns structured stem blocks.

- [ ] **Step 3: Write minimal implementation**

Wire the paper detail route to include `stem_blocks`, and make sure the import flow persists enough metadata to reconstruct the order on demand.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/e2e/test_sample_import.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/e2e/test_sample_import.py
git commit -m "test: cover stem image round-trip"
```

### Verification Checklist

- [ ] `pytest backend/tests/parser/test_docx_reader.py -v`
- [ ] `pytest backend/tests/api/test_import_api.py -v`
- [ ] `pytest backend/tests/e2e/test_sample_import.py -v`
- [ ] `cd frontend && npm run test -- --run src/__tests__/ReviewPage.test.tsx`
- [ ] Open the review page and confirm question 2 shows the triangle diagram inside the stem flow, not as a detached attachment.
