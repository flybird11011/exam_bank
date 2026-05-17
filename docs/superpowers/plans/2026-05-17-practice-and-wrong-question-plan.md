# 练习与错题查询 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为现有 Word 题库增加“按试卷练习、按题型配额出题、跳过即掌握、错题查询”的闭环能力。

**Architecture:** 以题目级学习状态表作为唯一状态源，配合作答历史表保存每次练习事件。后端负责生成练习会话、更新掌握状态、按条件查询错题；前端新增独立练习页和错题查询页，直接消费这套接口与状态数据。  
本次实现不修改导入与审阅主流程，只在现有题库数据之上增加练习层。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite, React 19, TypeScript, Vite, React Router, Vitest, Pytest

---

### Task 1: Add learning-state data model and migration

**Files:**
- Modify: `backend/app/db/models.py`
- Create: `backend/migrations/versions/20260517_0001_practice_state.py`
- Modify: `backend/app/db/base.py` if the migration or model import wiring requires it
- Test: `backend/tests/db/test_metadata.py`

- [ ] **Step 1: Write the failing test**

Add a metadata test that asserts the new ORM tables exist in `Base.metadata`:

```python
def test_practice_tables_exist_in_metadata():
    table_names = set(Base.metadata.tables)
    assert "question_learning_state" in table_names
    assert "question_practice_attempt" in table_names
    assert "practice_session" in table_names
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest backend/tests/db/test_metadata.py -q
```

Expected: FAIL because the new tables do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add three SQLAlchemy models:

```python
class QuestionLearningState(Base):
    __tablename__ = "question_learning_state"

    question_id: Mapped[str] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"), primary_key=True)
    mastered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_result: Mapped[str | None] = mapped_column(String(20))
    last_attempt_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class QuestionPracticeAttempt(Base):
    __tablename__ = "question_practice_attempt"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("practice_session.id", ondelete="SET NULL"))
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    answer_payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class PracticeSession(Base):
    __tablename__ = "practice_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("exam_paper.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="paper")
    randomized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exclude_mastered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    single_choice_count: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    fill_blank_count: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    short_answer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=11)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
```

Add the Alembic migration with the corresponding `CREATE TABLE` / `DROP TABLE` operations and foreign keys.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest backend/tests/db/test_metadata.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py backend/migrations/versions/20260517_0001_practice_state.py backend/tests/db/test_metadata.py
git commit -m "feat: add practice state tables"
```

---

### Task 2: Implement practice session and wrong-question backend APIs

**Files:**
- Create: `backend/app/services/practice_service.py`
- Create: `backend/app/api/routes/practice.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/__init__.py` if imports are exposed there
- Test: `backend/tests/api/test_practice_api.py`

- [ ] **Step 1: Write the failing test**

Add tests that describe the new backend contract:

```python
def test_create_practice_session_uses_default_counts():
    response = client.post("/api/practice/sessions", json={"paper_id": paper_id})
    body = response.json()
    assert body["single_choice_count"] == 8
    assert body["fill_blank_count"] == 8
    assert body["short_answer_count"] == 11


def test_submit_wrong_answer_increments_wrong_count_and_clears_mastered():
    response = client.post("/api/practice/attempts", json={"question_id": question_id, "result": "wrong"})
    assert response.json()["wrong_count"] == 1
    assert response.json()["mastered"] is False


def test_submit_skip_marks_mastered():
    response = client.post("/api/practice/attempts", json={"question_id": question_id, "result": "skip"})
    assert response.json()["mastered"] is True


def test_wrong_question_query_filters_by_mastered_and_wrong_count():
    response = client.get("/api/practice/questions", params={"mastered": "false", "min_wrong_count": 2})
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest backend/tests/api/test_practice_api.py -q
```

Expected: FAIL because the route and service do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement `practice_service.py` with these responsibilities:

```python
def create_practice_session(paper_id: str, randomized: bool, exclude_mastered: bool, counts: dict[str, int]) -> dict: ...
def record_practice_attempt(question_id: str, result: str, answer_payload: dict | None = None, session_id: str | None = None) -> dict: ...
def list_practice_questions(filters: dict[str, object]) -> list[dict]: ...
```

Recommended behavior:
- Build one ordered question list from the selected paper
- Group by `single_choice`, `fill_blank`, `short_answer`
- Filter out mastered questions when requested
- Randomize after filtering
- Update `question_learning_state` on each attempt:
  - `correct` -> `mastered = true`
  - `skip` -> `mastered = true`
  - `wrong` -> `mastered = false`, `wrong_count += 1`

Implement `practice.py` with these endpoints:

```python
POST /api/practice/sessions
POST /api/practice/attempts
GET /api/practice/questions
GET /api/practice/questions/{question_id}
```

Mount the router in `backend/app/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest backend/tests/api/test_practice_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/practice_service.py backend/app/api/routes/practice.py backend/app/main.py backend/tests/api/test_practice_api.py
git commit -m "feat: add practice session APIs"
```

---

### Task 3: Add frontend API bindings and practice page

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/pages/PracticePage.tsx`
- Create: `frontend/src/__tests__/PracticePage.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: Write the failing test**

Add a page test that renders the defaults and verifies the three quota inputs:

```tsx
test("practice page shows default quotas and controls", async () => {
  render(<PracticePage />);
  expect(screen.getByLabelText("单选题")).toHaveValue(8);
  expect(screen.getByLabelText("填空题")).toHaveValue(8);
  expect(screen.getByLabelText("解答题")).toHaveValue(11);
  expect(screen.getByRole("checkbox", { name: "随机出题" })).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: "排除已掌握" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- PracticePage.test.tsx
```

Expected: FAIL because the page and bindings do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add API types for practice session and wrong-question records in `frontend/src/lib/api.ts`, then implement `PracticePage` with:

```tsx
type PracticeQuota = {
  single_choice_count: number;
  fill_blank_count: number;
  short_answer_count: number;
};
```

Page behavior:
- Choose a paper
- Edit quotas, defaulting to `8 / 8 / 11`
- Toggle randomized and exclude-mastered
- Start session
- Show current question and navigation
- Show buttons for `正确 / 错误 / 跳过`

Register the route in `frontend/src/App.tsx` and add a nav entry in the existing layout flow.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm test -- PracticePage.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/pages/PracticePage.tsx frontend/src/__tests__/PracticePage.test.tsx frontend/src/App.tsx frontend/src/styles/global.css
git commit -m "feat: add practice page"
```

---

### Task 4: Add wrong-question query page

**Files:**
- Create: `frontend/src/pages/WrongQuestionPage.tsx`
- Create: `frontend/src/__tests__/WrongQuestionPage.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: Write the failing test**

Add a page test that verifies the default filters and result summary:

```tsx
test("wrong-question page filters by mastered and wrong count", async () => {
  render(<WrongQuestionPage />);
  expect(screen.getByLabelText("只看未掌握")).toBeInTheDocument();
  expect(screen.getByLabelText("最少做错次数")).toHaveValue(1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- WrongQuestionPage.test.tsx
```

Expected: FAIL because the page does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement a filterable list backed by `GET /api/practice/questions`:

- `mastered=false`
- `min_wrong_count`
- optional `paper_id`
- optional `question_type`

Show:
- question number
- question type
- mastered badge
- wrong count
- recent result

Register the route and navigation entry alongside the practice page.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm test -- WrongQuestionPage.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/WrongQuestionPage.tsx frontend/src/__tests__/WrongQuestionPage.test.tsx frontend/src/App.tsx frontend/src/lib/api.ts frontend/src/styles/global.css
git commit -m "feat: add wrong-question query page"
```

---

### Task 5: Add integration coverage and verify full flow

**Files:**
- Modify: `backend/tests/api/test_import_api.py` if practice state needs imported questions as fixtures
- Modify: `backend/tests/api/test_review_api.py` if review UI interactions need to preserve state
- Create: `backend/tests/e2e/test_practice_flow.py`
- Create: `frontend/tests/e2e/practice-and-wrong-question.spec.ts`

- [ ] **Step 1: Write the failing test**

Add an end-to-end flow that covers:

```python
def test_practice_flow_updates_learning_state():
    # import paper
    # create practice session
    # answer one wrong, one skip
    # query wrong questions
    # assert mastered/wrong_count values
```

Add a browser test that covers:
- opening the practice page
- starting a session
- skipping one question
- opening wrong-question page
- filtering by wrong count

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest backend/tests/e2e/test_practice_flow.py -q
cd frontend
npm run e2e -- practice-and-wrong-question.spec.ts
```

Expected: FAIL before the full flow exists.

- [ ] **Step 3: Write minimal implementation**

Fix any small integration gaps exposed by the e2e tests:

- API response shape mismatches
- missing list fields in the frontend types
- route registration omissions
- styling or layout regressions

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest backend/tests/e2e/test_practice_flow.py -q
cd frontend
npm run e2e -- practice-and-wrong-question.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/e2e/test_practice_flow.py frontend/tests/e2e/practice-and-wrong-question.spec.ts
git commit -m "test: cover practice and wrong-question flow"
```

---

### Self-check

- [ ] `question_learning_state` and `question_practice_attempt` are used as the single source of truth for mastery and history
- [ ] The plan covers default quotas `8 / 8 / 11`
- [ ] The plan covers randomization and exclusion of mastered questions
- [ ] The plan covers skip-as-mastered and wrong-count accumulation
- [ ] The plan covers the wrong-question query page and its two key filters
- [ ] Every new endpoint, page, and table has a task
- [ ] No placeholder steps remain

