# Paper Reimport Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect repeated Word imports by file fingerprint and let the user replace the old paper with the newly imported one, while fully deleting the old paper tree and its stored media.

**Architecture:** Add a paper lifecycle service that owns two concerns: duplicate detection from the uploaded `.docx` bytes and hard cleanup of a paper tree. The existing import service keeps parsing Word content, but it delegates duplicate lookup and old-paper cleanup so the import flow stays readable. The frontend import page becomes a two-stage flow: initial upload, then a confirmation state if the backend reports a duplicate.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite/Postgres-compatible schema migration, React 19, Vite, Vitest, Testing Library.

---

### Task 1: Add file fingerprint storage and duplicate lookup

**Files:**
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/services/import_service.py`
- Create: `backend/app/services/paper_lifecycle_service.py`
- Modify: `backend/app/api/routes/imports.py`
- Modify: `backend/migrations/versions/20260516_0001_initial_schema.py` or add a new migration for the new column
- Modify or create: `backend/tests/api/test_import_api.py`

- [ ] **Step 1: Write the failing tests**

Add tests that import the same fixture twice and assert the second call reports a duplicate instead of silently creating a second paper. The assertions should cover:

```python
assert response.status_code == 200
body = response.json()
assert body["duplicate_found"] is True
assert body["existing_paper"]["paper_id"] == first_paper_id
assert body["duplicate_policy"] == "ask"
```

Also add a test that verifies a newly imported paper stores a stable file fingerprint in `exam_paper.source_file_hash`.

- [ ] **Step 2: Run the backend tests and verify they fail**

Run:

```bash
pytest backend/tests/api/test_import_api.py -v
```

Expected: the new duplicate and hash assertions fail because the schema and response fields do not exist yet.

- [ ] **Step 3: Implement the minimal schema and lookup support**

Add `source_file_hash` to `ExamPaper`, persist it during import, and expose a helper in `backend/app/services/paper_lifecycle_service.py` that:

- reads the upload bytes
- computes `sha256`
- looks up an existing paper by that hash
- returns `None` when no match exists

Wire `backend/app/api/routes/imports.py` so the import endpoint accepts a `duplicate_policy` form field with values `ask`, `replace`, and `keep_both`, defaulting to `ask`.

- [ ] **Step 4: Run the backend tests again**

Run:

```bash
pytest backend/tests/api/test_import_api.py -v
```

Expected: the duplicate detection and fingerprint assertions pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py backend/app/services/import_service.py backend/app/services/paper_lifecycle_service.py backend/app/api/routes/imports.py backend/migrations/versions/20260516_0001_initial_schema.py backend/tests/api/test_import_api.py
git commit -m "feat: detect duplicate paper imports"
```

### Task 2: Implement hard delete cleanup and replace-on-import flow

**Files:**
- Modify: `backend/app/services/import_service.py`
- Modify/Create: `backend/app/services/paper_lifecycle_service.py`
- Modify: `backend/app/api/routes/imports.py`
- Modify or create: `backend/tests/api/test_import_api.py`
- Create if needed: `backend/tests/services/test_paper_lifecycle_service.py`

- [ ] **Step 1: Write the failing tests**

Add tests for the replacement path:

```python
def test_replace_duplicate_import_deletes_old_paper_tree():
    # import fixture once
    # import same fixture again with duplicate_policy="replace"
    # assert new paper exists
    # assert old paper no longer exists
    # assert old media directory is gone
```

Also add a cleanup-focused test that verifies the delete helper removes rows from `review_log`, `content_block`, and `media_asset` before the paper row disappears.

- [ ] **Step 2: Run the backend tests and verify they fail**

Run:

```bash
pytest backend/tests/api/test_import_api.py backend/tests/services/test_paper_lifecycle_service.py -v
```

Expected: replacement flow and cleanup assertions fail because the delete helper and replace path are not implemented yet.

- [ ] **Step 3: Implement the cleanup and replace flow**

In `backend/app/services/paper_lifecycle_service.py`, add a `delete_paper_tree(paper_id: str)` helper that:

- deletes `review_log` rows tied to the paper or its questions
- deletes `content_block` rows for paper-owned questions
- deletes `media_asset` rows for paper-owned questions
- removes `backend/media/{paper_id}` from disk
- deletes the `ExamPaper` row last

Then update `import_service.import_paper(...)` so replacement works like this:

1. detect an existing paper by hash
2. import the new paper normally
3. if `duplicate_policy == "replace"`, delete the old paper tree after the new import succeeds
4. if cleanup fails, keep the new paper and surface a cleanup warning rather than rolling back the new import

Keep `keep_both` as a no-op for duplicates and `ask` as a non-mutating duplicate response.

- [ ] **Step 4: Run the backend tests again**

Run:

```bash
pytest backend/tests/api/test_import_api.py backend/tests/services/test_paper_lifecycle_service.py -v
```

Expected: duplicate replacement passes, and the cleanup assertions pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/import_service.py backend/app/services/paper_lifecycle_service.py backend/app/api/routes/imports.py backend/tests/api/test_import_api.py backend/tests/services/test_paper_lifecycle_service.py
git commit -m "feat: replace duplicate imported papers"
```

### Task 3: Add duplicate import UI to the frontend

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/ImportPage.tsx`
- Create: `frontend/src/__tests__/ImportPage.test.tsx`

- [ ] **Step 1: Write the failing tests**

Add a frontend test that mocks a duplicate response from `importPaper(...)` and checks that the page renders a confirmation state with two actions:

- `替换旧试卷`
- `保留两份`

Add another test that clicks `替换旧试卷` and verifies the page calls the API again with `duplicate_policy: "replace"`.

- [ ] **Step 2: Run the frontend test file and verify it fails**

Run:

```bash
npm run test -- --run src/__tests__/ImportPage.test.tsx
```

Expected: the duplicate confirmation UI and retry behavior fail because the page only supports a single happy-path upload.

- [ ] **Step 3: Implement the frontend flow**

Update `frontend/src/lib/api.ts` so `importPaper` accepts an optional duplicate policy and can return either:

- a normal import result, or
- a duplicate response that includes `duplicate_found`, `existing_paper`, and `duplicate_policy`

Then update `ImportPage.tsx` to:

- keep the last submitted `FormData`
- render a duplicate confirmation state when the backend reports a match
- resubmit with `duplicate_policy="replace"` or `duplicate_policy="keep_both"` depending on the user's choice
- keep the existing success message for non-duplicate imports

Do not add the manual delete button in this task; that stays deferred for later as agreed.

- [ ] **Step 4: Run the frontend tests again**

Run:

```bash
npm run test -- --run src/__tests__/ImportPage.test.tsx
```

Expected: the duplicate UI test passes.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/pages/ImportPage.tsx frontend/src/__tests__/ImportPage.test.tsx
git commit -m "feat: handle duplicate paper imports in the ui"
```

### Task 4: Full regression pass

**Files:**
- All files changed in Tasks 1-3

- [ ] **Step 1: Run the backend API tests**

Run:

```bash
pytest backend/tests/api/test_import_api.py backend/tests/services/test_paper_lifecycle_service.py -v
```

Expected: all import, duplicate, and cleanup tests pass.

- [ ] **Step 2: Run the frontend unit tests**

Run:

```bash
npm run test
```

Expected: the existing review/practice tests plus the new import-page test pass.

- [ ] **Step 3: Run a build check**

Run:

```bash
npm run build
```

Expected: the frontend builds cleanly.

- [ ] **Step 4: Final review**

Verify that the repeated import flow now behaves as:

- first upload creates a paper
- second upload of the same file triggers duplicate detection
- choosing replace removes the old paper tree and keeps the new one
- choosing keep both leaves the old and new papers side by side

## Coverage Check

- Duplicate detection by file fingerprint: Task 1
- Replace old paper with new import: Task 2
- Hard delete of associated data and media files: Task 2
- Frontend duplicate prompt and retry: Task 3
- Regression verification: Task 4

## Deferred Scope

The manual delete button for removing a paper from the paper list stays deferred. It can later reuse the same `delete_paper_tree` helper once the UI work is scheduled.
