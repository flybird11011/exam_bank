# 错题回顾页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有练习能力之上新增一个独立的错题回顾页，支持按未掌握/错题次数筛选，默认隐藏答案与解析，且能复用题干、选项和解析的富文本块渲染。

**Architecture:** 前端新增独立的 `WrongQuestionPage` 作为错题回顾入口，页面只消费现有练习后端的查询与详情接口。题干、选项、答案、解析的块渲染统一复用 `RichContentBlocks`，通过局部状态控制答案和解析的默认折叠展开。现有 `PracticePage` 保持出题/作答职责，不再承担错题回顾主流程。

**Tech Stack:** React 19, TypeScript, Vite, React Router, Vitest, Testing Library

---

### Task 1: Add a failing test for the wrong-question review page

**Files:**
- Create: `frontend/src/__tests__/WrongQuestionPage.test.tsx`
- Create: `frontend/src/pages/WrongQuestionPage.tsx`
- Modify: `frontend/src/lib/api.ts` if the page needs richer response types

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test, vi, beforeEach } from "vitest";

test("wrong-question page hides answer and analysis by default", async () => {
  render(<WrongQuestionPage />);
  expect(screen.getByRole("button", { name: "显示答案" })).toBeInTheDocument();
  expect(screen.queryByText("答案：")).not.toBeInTheDocument();
  expect(screen.queryByText("解析：")).not.toBeInTheDocument();
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

Create `WrongQuestionPage` with:

```tsx
export function WrongQuestionPage() {
  return (
    <div />
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm test -- WrongQuestionPage.test.tsx
```

Expected: PASS after the page renders the hidden-answer control.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/WrongQuestionPage.tsx frontend/src/__tests__/WrongQuestionPage.test.tsx
git commit -m "feat: add wrong question review page shell"
```

---

### Task 2: Reuse rich block rendering in the new page

**Files:**
- Modify: `frontend/src/pages/WrongQuestionPage.tsx`
- Modify: `frontend/src/components/RichContent.tsx` only if new block kinds or helper props are needed
- Modify: `frontend/src/lib/api.ts` if the detail type needs richer fields

- [ ] **Step 1: Write the failing test**

Extend the wrong-question page test so the detail area renders:

```tsx
expect(screen.getByText("Question 3")).toBeInTheDocument();
expect(screen.getByRole("img", { name: "detail.png" })).toBeInTheDocument();
expect(screen.getByText("显示答案")).toBeInTheDocument();
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- WrongQuestionPage.test.tsx
```

Expected: FAIL until the page loads question detail and renders blocks.

- [ ] **Step 3: Write minimal implementation**

Use `GET /api/practice/questions` for the list and `GET /api/practice/questions/{question_id}` for detail. Render:

- question stem via `RichContentBlocks`
- options via `RichContentBlocks` when present
- answer and analysis only after clicking `显示答案`
- recent attempts below the fold

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm test -- WrongQuestionPage.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/WrongQuestionPage.tsx frontend/src/components/RichContent.tsx frontend/src/lib/api.ts frontend/src/__tests__/WrongQuestionPage.test.tsx
git commit -m "feat: render wrong question review details"
```

---

### Task 3: Wire routing and navigation

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: Write the failing test**

Update the app navigation test to expect a `错题回顾` entry.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- App.test.tsx
```

- [ ] **Step 3: Write minimal implementation**

Add a route:

```tsx
<Route path="/wrong-questions" element={<WrongQuestionPage />} />
```

Add nav item:

```ts
{ label: "错题回顾", path: "/wrong-questions" }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm test -- App.test.tsx WrongQuestionPage.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout.tsx frontend/src/styles/global.css frontend/src/__tests__/App.test.tsx frontend/src/pages/WrongQuestionPage.tsx
git commit -m "feat: wire wrong question review navigation"
```

---

### Task 4: Verify full frontend build and test pass

**Files:**
- All frontend files touched above

- [ ] **Step 1: Run the full frontend test suite**

Run:

```bash
cd frontend
npm test
```

- [ ] **Step 2: Run the frontend production build**

Run:

```bash
cd frontend
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend
git commit -m "feat: add wrong question review page"
```

