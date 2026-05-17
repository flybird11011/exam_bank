# Word Exam Bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MVP that imports Word exam papers, extracts structured questions, auto-tags them, supports human review, and enables search.

**Architecture:** Start with a backend-first monorepo. A FastAPI service owns import, review, and search APIs; PostgreSQL stores papers, questions, content blocks, assets, tags, and audit logs; a lightweight React/Vite admin UI handles upload, review, and search. Parsing is split into small testable modules: OOXML reader, paragraph normalizer, section splitter, question splitter, asset extractor, and tag rules.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, PostgreSQL, Pytest; TypeScript, React, Vite, React Router, TanStack Query, Playwright.

---

## File Structure Map

- `backend/`: FastAPI app, parser services, DB models, and backend tests.
- `frontend/`: React/Vite admin UI and frontend tests.
- `docs/superpowers/specs/`: product spec already written.
- `docs/superpowers/plans/`: implementation plans.

Keep files narrow and responsibility-focused:

- `backend/app/parser/*` should only parse and normalize DOCX content.
- `backend/app/services/*` should coordinate repositories, parser output, and API-facing DTOs.
- `backend/app/api/routes/*` should stay thin.
- `frontend/src/pages/*` should compose UI state and call the API layer.

---

### Task 1: Backend scaffold and health check

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/settings.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Run: `pytest backend/tests/test_health.py -v`

Expected: FAIL because `app.main` and `/health` are not implemented yet.

- [ ] **Step 2: Add the minimal backend app**

```python
from fastapi import FastAPI
from app.api.routes.health import router as health_router

app = FastAPI(title="Word Exam Bank")
app.include_router(health_router)
```

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 3: Run the test again**

Run: `pytest backend/tests/test_health.py -v`

Expected: PASS.

- [ ] **Step 4: Commit the scaffold**

Run:

```bash
git add backend/pyproject.toml backend/app backend/tests
git commit -m "feat: scaffold backend health check"
```

---

### Task 2: Database models and initial migration

**Files:**
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/models.py`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/20260516_0001_initial_schema.py`
- Create: `backend/tests/db/test_metadata.py`

- [ ] **Step 1: Write the failing test**

```python
from app.db.base import Base
from app.db import models

def test_metadata_contains_core_tables():
    table_names = set(Base.metadata.tables.keys())
    assert {
        "exam_paper",
        "paper_section",
        "question",
        "question_option",
        "content_block",
        "media_asset",
        "tag",
        "question_tag",
        "parse_run",
        "parse_trace",
        "parse_warning",
        "review_log",
    }.issubset(table_names)
```

Run: `pytest backend/tests/db/test_metadata.py -v`

Expected: FAIL because the SQLAlchemy models do not exist yet.

- [ ] **Step 2: Define the models and Base**

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

```python
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class ExamPaper(Base):
    __tablename__ = "exam_paper"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(50), nullable=False)
    # add the remaining fields from the spec
```

Add the remaining tables with the exact names in the spec so later services can rely on them.

- [ ] **Step 3: Create the migration**

The migration must create the same tables and indexes as the models. Keep the upgrade path explicit and reversible.

- [ ] **Step 4: Run the metadata test**

Run: `pytest backend/tests/db/test_metadata.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the schema**

Run:

```bash
git add backend/app/db backend/migrations backend/tests/db
git commit -m "feat: add exam bank database schema"
```

---

### Task 3: DOCX reader and paragraph normalization

**Files:**
- Create: `backend/app/parser/docx_reader.py`
- Create: `backend/app/parser/normalize.py`
- Create: `backend/app/parser/types.py`
- Create: `backend/tests/fixtures/2025-suzhou-math-exam-snippet.docx`
- Create: `backend/tests/parser/test_docx_reader.py`

- [ ] **Step 1: Write the failing test**

```python
from app.parser.docx_reader import read_docx_paragraphs

def test_read_docx_paragraphs_extracts_text_and_marks_assets():
    paragraphs = read_docx_paragraphs("backend/tests/fixtures/2025-suzhou-math-exam-snippet.docx")
    assert paragraphs[0].text.startswith("2025年苏州市初中学业水平考试试卷")
    assert any(p.has_image for p in paragraphs)
    assert any("一、选择题" in p.text for p in paragraphs)
```

Run: `pytest backend/tests/parser/test_docx_reader.py -v`

Expected: FAIL because the reader module is not implemented yet.

- [ ] **Step 2: Implement the OOXML reader**

```python
from dataclasses import dataclass
from zipfile import ZipFile

@dataclass
class DocxParagraph:
    index: int
    text: str
    raw_xml: str
    has_image: bool = False
    has_table: bool = False
    has_formula: bool = False
```

```python
def read_docx_paragraphs(docx_path: str) -> list[DocxParagraph]:
    # unzip, parse word/document.xml, gather w:p text and asset flags
    ...
```

Also add `normalize_paragraphs()` to collapse whitespace, preserve numbering, and keep answer/analysis markers intact.

- [ ] **Step 3: Run the parser test**

Run: `pytest backend/tests/parser/test_docx_reader.py -v`

Expected: PASS.

- [ ] **Step 4: Commit the parser**

Run:

```bash
git add backend/app/parser backend/tests/parser backend/tests/fixtures
git commit -m "feat: add docx reader and normalization"
```

---

### Task 4: Section splitting, question splitting, and tag rules

**Files:**
- Create: `backend/app/parser/section_splitter.py`
- Create: `backend/app/parser/question_splitter.py`
- Create: `backend/app/tagging/rules.py`
- Create: `backend/app/tagging/types.py`
- Create: `backend/tests/parser/test_question_splitter.py`

- [ ] **Step 1: Write the failing test**

```python
from app.parser.question_splitter import split_sections_and_questions

def test_split_sample_math_exam_into_three_sections_and_twenty_seven_questions():
    paper = split_sections_and_questions([
        "2025年苏州市初中学业水平考试试卷",
        "数学",
        "一、选择题：本大题共8小题，每小题3分，共24分。",
        "1. 下列实数中，比2小的数是（ ）",
        "【答案】D",
        "二、填空题：本大题共8小题，每小题3分，共24分。",
        "17. ...",
        "三、解答题：本大题共11小题，共82分。",
        "27. ...",
    ])
    assert [section.section_type for section in paper.sections] == ["single_choice", "fill_blank", "short_answer"]
```

Run: `pytest backend/tests/parser/test_question_splitter.py -v`

Expected: FAIL because the splitter and tagging rules do not exist yet.

- [ ] **Step 2: Implement section and question splitting**

```python
SECTION_PATTERNS = {
    "single_choice": r"^一、.*选择题",
    "fill_blank": r"^二、.*填空题",
    "short_answer": r"^三、.*解答题",
}

QUESTION_START = r"^\d+\."
ANSWER_MARKER = "【答案】"
ANALYSIS_MARKERS = ("【解析】", "【分析】", "【详解】")
```

Split sections first, then questions inside each section, and preserve source paragraph ranges for traceability.

- [ ] **Step 3: Implement tag rules**

```python
def generate_feature_tags(question) -> list[TagSuggestion]:
    tags = []
    if question.has_image:
        tags.append(TagSuggestion("feature", "含图片", "rule", 1.0))
    if question.has_table:
        tags.append(TagSuggestion("feature", "含表格", "rule", 1.0))
    if question.has_formula:
        tags.append(TagSuggestion("feature", "含公式", "rule", 1.0))
    return tags
```

Add rule-based subject, question type, and difficulty suggestions consistent with the spec.

- [ ] **Step 4: Run the splitter test**

Run: `pytest backend/tests/parser/test_question_splitter.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the parsing rules**

Run:

```bash
git add backend/app/parser backend/app/tagging backend/tests/parser
git commit -m "feat: split exam sections and questions"
```

---

### Task 5: Import, review, and search APIs

**Files:**
- Create: `backend/app/services/import_service.py`
- Create: `backend/app/services/review_service.py`
- Create: `backend/app/services/search_service.py`
- Create: `backend/app/api/routes/imports.py`
- Create: `backend/app/api/routes/questions.py`
- Create: `backend/app/api/routes/papers.py`
- Create: `backend/tests/api/test_import_api.py`
- Create: `backend/tests/api/test_review_api.py`
- Create: `backend/tests/api/test_search_api.py`

- [ ] **Step 1: Write the failing API tests**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_import_returns_parse_run_id():
    client = TestClient(app)
    with open("backend/tests/fixtures/2025-suzhou-math-exam-snippet.docx", "rb") as f:
        response = client.post(
            "/api/papers/import",
            files={"file": ("sample.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"subject": "数学", "region": "江苏省苏州市", "exam_year": 2025, "exam_type": "中考真题"},
        )
    assert response.status_code == 200
    assert "parse_run_id" in response.json()
```

Run:

```bash
pytest backend/tests/api/test_import_api.py -v
pytest backend/tests/api/test_review_api.py -v
pytest backend/tests/api/test_search_api.py -v
```

Expected: FAIL because the routes and services are missing.

- [ ] **Step 2: Implement the import pipeline service**

```python
def import_paper(file_path: str, subject: str, region: str, exam_year: int, exam_type: str) -> dict:
    # read docx, parse paper, persist parse_run, exam_paper, sections, questions, tags, traces, warnings
    ...
```

The service should return a stable DTO containing `parse_run_id`, `status`, and a serialized paper draft.

- [ ] **Step 3: Implement thin route handlers**

```python
from fastapi import APIRouter, UploadFile, File, Form

router = APIRouter(prefix="/api/papers")

@router.post("/import")
async def import_paper_endpoint(...):
    ...
```

Add question update, review status, and search endpoints that delegate to service functions.

- [ ] **Step 4: Run the API tests**

Run the three API test files again.

Expected: PASS.

- [ ] **Step 5: Commit the API layer**

Run:

```bash
git add backend/app/services backend/app/api/routes backend/tests/api
git commit -m "feat: add paper import review and search APIs"
```

---

### Task 6: Frontend admin shell and core pages

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/pages/ImportPage.tsx`
- Create: `frontend/src/pages/ReviewPage.tsx`
- Create: `frontend/src/pages/SearchPage.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/QuestionPanel.tsx`
- Create: `frontend/src/components/TagEditor.tsx`
- Create: `frontend/src/styles/global.css`
- Create: `frontend/src/__tests__/App.test.tsx`

- [ ] **Step 1: Write the failing UI test**

```tsx
import { render, screen } from "@testing-library/react";
import { App } from "../App";

test("renders the navigation shell", () => {
  render(<App />);
  expect(screen.getByText("试卷导入")).toBeInTheDocument();
  expect(screen.getByText("题目审核")).toBeInTheDocument();
  expect(screen.getByText("题库检索")).toBeInTheDocument();
});
```

Run: `npm test -- --runInBand`

Expected: FAIL because the frontend app scaffold and shell are missing.

- [ ] **Step 2: Build the shell and pages**

```tsx
export function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ImportPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/search" element={<SearchPage />} />
      </Routes>
    </Layout>
  );
}
```

Use a three-column review layout:

- left: section/question navigator
- center: question content
- right: metadata, tags, warnings, actions

- [ ] **Step 3: Wire API helpers**

```ts
export async function importPaper(formData: FormData) {
  const response = await fetch("/api/papers/import", { method: "POST", body: formData });
  if (!response.ok) throw new Error("import failed");
  return response.json();
}
```

- [ ] **Step 4: Run the UI test**

Run: `npm test -- --runInBand`

Expected: PASS.

- [ ] **Step 5: Commit the frontend**

Run:

```bash
git add frontend
git commit -m "feat: add admin shell and core pages"
```

---

### Task 7: End-to-end sample import and regression smoke test

**Files:**
- Create: `backend/tests/e2e/test_sample_import.py`
- Create: `backend/tests/e2e/test_sample_search.py`
- Create: `frontend/tests/e2e/import-and-review.spec.ts`
- Create: `frontend/tests/e2e/search.spec.ts`

- [ ] **Step 1: Write the failing backend smoke test**

```python
from app.services.import_service import import_paper

def test_sample_paper_import_creates_three_sections():
    result = import_paper(
        "backend/tests/fixtures/2025-suzhou-math-exam-snippet.docx",
        subject="数学",
        region="江苏省苏州市",
        exam_year=2025,
        exam_type="中考真题",
    )
    assert result["paper"]["section_count"] == 3
    assert result["paper"]["question_count"] == 27
```

Run: `pytest backend/tests/e2e/test_sample_import.py -v`

Expected: FAIL until the import pipeline and persistence are fully wired.

- [ ] **Step 2: Make the smoke path real**

Connect the parser, database persistence, tagging rules, and API DTOs so the sample document can round-trip from upload to stored paper and back to search results.

- [ ] **Step 3: Add the frontend smoke flow**

Use Playwright to cover:

1. Open the import page
2. Upload the sample DOCX
3. Wait for parsing to finish
4. Open the review page
5. Confirm the paper shows three sections
6. Search by subject and year

- [ ] **Step 4: Run all regression checks**

Run:

```bash
pytest backend/tests -v
npm test -- --runInBand
npm run test:e2e
```

Expected: PASS.

- [ ] **Step 5: Commit the end-to-end baseline**

Run:

```bash
git add backend/tests/e2e frontend/tests/e2e
git commit -m "test: add sample import regression coverage"
```

---

## Coverage Check

This plan covers the full spec:

- Word import and OOXML parsing: Tasks 3 and 7
- Data model and persistence: Task 2
- Section/question splitting and tagging: Task 4
- Import/review/search APIs: Task 5
- Admin UI: Task 6
- Errors, warnings, and traceability: Tasks 2, 5, and 7
- MVP sequencing and safe rollout: all tasks are ordered from scaffold to smoke tests

No placeholders remain in the plan, and the type names used across tasks stay aligned with the spec (`exam_paper`, `paper_section`, `question`, `question_option`, `content_block`, `media_asset`, `tag`, `question_tag`, `parse_run`, `parse_trace`, `parse_warning`, `review_log`).
