# MathType Linux Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make embedded MathType formulas extract as text on VPS/Linux, not just on Windows.

**Architecture:** Keep the current Windows `pythoncom` path, but add a pure-Python OLE Compound File reader fallback that can read the `Equation Native` stream on Linux. Feed that stream into the existing MathType equation parser so the downstream DOCX parsing logic does not change. Add tests that force the fallback path and verify the same formula text is recovered.

**Tech Stack:** Python 3.10+, FastAPI backend, Pytest, standard library, existing MathType parser.

---

### Task 1: Add a Linux-compatible OLE fallback for Equation Native

**Files:**
- Modify: `backend/app/parser/mathtype.py`

- [ ] **Step 1: Write the failing test**

```python
from app.parser import mathtype


def test_extract_mathtype_equation_text_uses_linux_fallback_when_pythoncom_is_missing(monkeypatch):
    monkeypatch.setattr(mathtype, "pythoncom", None)
    ole_bytes = ...
    assert mathtype.extract_mathtype_equation_text(ole_bytes) == "..."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/parser/test_mathtype.py::test_extract_mathtype_equation_text_uses_linux_fallback_when_pythoncom_is_missing -v`
Expected: FAIL because the fallback path is not implemented yet.

- [ ] **Step 3: Write minimal implementation**

Implement a pure-Python reader that can open the embedded OLE compound file bytes, locate the `Equation Native` stream, and return its bytes. Keep the existing MathType stream parser unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/parser/test_mathtype.py::test_extract_mathtype_equation_text_uses_linux_fallback_when_pythoncom_is_missing -v`
Expected: PASS and the returned text matches the existing Windows path.

- [ ] **Step 5: Commit**

```bash
git add backend/app/parser/mathtype.py backend/tests/parser/test_mathtype.py
git commit -m "fix: add linux fallback for mathtype extraction"
```

### Task 2: Cover the docx reader path on non-Windows

**Files:**
- Modify: `backend/tests/parser/test_docx_reader.py`

- [ ] **Step 1: Write the failing test**

```python
from app.parser import docx_reader


def test_read_docx_paragraphs_keeps_formula_text_without_pythoncom(monkeypatch):
    monkeypatch.setattr(docx_reader, "extract_mathtype_equation_text", lambda _ole: None)
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/parser/test_docx_reader.py::test_read_docx_paragraphs_keeps_formula_text_without_pythoncom -v`
Expected: FAIL until the new fallback is wired through correctly.

- [ ] **Step 3: Write minimal implementation**

Ensure the DOCX reader still emits formula text blocks from the fallback stream on Linux and does not regress the current image filtering logic.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/parser/test_docx_reader.py::test_read_docx_paragraphs_keeps_formula_text_without_pythoncom -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/parser/test_docx_reader.py
git commit -m "test: cover mathtype fallback through docx reader"
```

### Task 3: Verify the full parser suite

**Files:**
- None

- [ ] **Step 1: Run the relevant parser tests**

Run:
```bash
pytest backend/tests/parser/test_mathtype.py backend/tests/parser/test_docx_reader.py backend/tests/api/test_import_formula_text_passthrough.py -q
```

- [ ] **Step 2: Confirm the result**

Expected: all tests pass with no warnings from the formula extraction path.

