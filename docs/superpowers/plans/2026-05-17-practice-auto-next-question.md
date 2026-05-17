# Practice Auto-Next Question Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make practice mode advance to the next question automatically after answer, wrong, or skip actions, while keeping the final question on the completion state.

**Architecture:** Centralize question advancement in a small helper inside `PracticePage` so every answer path uses the same logic. Keep API calls and session state updates unchanged, and only adjust the client-side navigation flow plus tests that describe the new behavior.

**Tech Stack:** React 19, TypeScript, Vitest, React Testing Library.

---

### Task 1: Add a shared next-question helper

**Files:**
- Modify: `frontend/src/pages/PracticePage.tsx`

- [ ] **Step 1: Refactor the current answer path to use one helper for advancing**

```tsx
function goToNextQuestion() {
  setCurrentIndex((index) => index + 1);
}

async function handleAttempt(result: "correct" | "wrong" | "skip") {
  if (!session || !currentQuestion) {
    return;
  }

  setStartingSession(true);
  setError(null);
  try {
    const response = await recordPracticeAttempt({
      question_id: currentQuestion.question_id,
      session_id: session.id,
      result,
      answer_payload: null,
    });

    setSessionQuestions((items) =>
      items.map((item) =>
        item.question_id === currentQuestion.question_id
          ? {
              ...item,
              mastered: response.learning_state.mastered,
              wrong_count: response.learning_state.wrong_count,
              last_result: response.learning_state.last_result,
              last_attempt_at: response.learning_state.last_attempt_at,
            }
          : item,
      ),
    );
    goToNextQuestion();
    setNotice(
      result === "skip"
        ? "已跳过并标记为已掌握"
        : result === "correct"
          ? "已记录答对"
          : "已记录答错",
    );
  } catch (attemptError) {
    setError(attemptError instanceof Error ? attemptError.message : "记录练习失败");
  } finally {
    setStartingSession(false);
  }
}
```

- [ ] **Step 2: Keep the completion state unchanged when the index reaches the end**

```tsx
const isSessionComplete = hasSession && currentIndex >= sessionQuestions.length;
```

- [ ] **Step 3: Re-run the practice flow manually in code path terms**

Verify that `correct`, `wrong`, and `skip` all call the same advancement helper and that the existing completion state still renders when the current index moves past the last item.

### Task 2: Cover the auto-advance behavior in tests

**Files:**
- Modify: `frontend/src/__tests__/PracticePage.test.tsx`

- [ ] **Step 1: Add a test for the correct-answer path**

```tsx
fireEvent.click(screen.getByRole("button", { name: "答对" }));
await screen.findByText("Question 2");
```

- [ ] **Step 2: Add a test for the skip path**

```tsx
fireEvent.click(screen.getByRole("button", { name: "跳过" }));
await screen.findByText("Question 2");
```

- [ ] **Step 3: Add a test for the final-question boundary**

```tsx
fireEvent.click(screen.getByRole("button", { name: "答对" }));
fireEvent.click(screen.getByRole("button", { name: "答对" }));
await screen.findByText("练习完成");
```

- [ ] **Step 4: Run the practice-related tests through the standard test runner**

Run: `npm test`
Expected: PASS

### Task 3: Verify the full frontend suite

**Files:**
- No additional file changes expected

- [ ] **Step 1: Run the full test suite**

Run: `npm test`
Expected: PASS

- [ ] **Step 2: Run the production build**

Run: `npm run build`
Expected: PASS with the existing dependency warnings only
