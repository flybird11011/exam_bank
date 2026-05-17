import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { WrongQuestionPage } from "../pages/WrongQuestionPage";
import * as api from "../lib/api";

vi.mock("../lib/api", () => ({
  getPracticeQuestion: vi.fn(),
  listPapers: vi.fn(),
  listPracticeQuestions: vi.fn(),
  recordPracticeAttempt: vi.fn(),
}));

const mockedApi = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();

  mockedApi.listPapers.mockResolvedValue([
    {
      paper_id: "paper-1",
      parse_run_id: "run-1",
      title: "2025 Practice Paper",
      subject: "math",
      region: "Suzhou",
      exam_year: 2025,
      exam_type: "exam",
      section_count: 1,
      question_count: 2,
      status: "parsed",
    },
  ]);

  mockedApi.listPracticeQuestions.mockResolvedValue({
    total: 1,
    items: [
      {
        question_id: "q-3",
        paper_id: "paper-1",
        question_no: "3",
        order_no: 3,
        question_type: "short_answer",
        stem_text: "Question 3",
        stem_blocks: [{ kind: "text", text: "Question 3" }],
        answer_text: "12",
        analysis_text: "Analysis 3",
        analysis_blocks: [{ kind: "text", text: "Analysis 3" }],
        mastered: false,
        wrong_count: 2,
        last_result: "wrong",
        last_attempt_at: "2026-05-17T00:00:00.000Z",
      },
    ],
  });

  mockedApi.getPracticeQuestion.mockResolvedValue({
    question: {
      question_id: "q-3",
      paper_id: "paper-1",
      question_no: "3",
      order_no: 3,
      question_type: "short_answer",
      stem_text: "Question 3",
      stem_blocks: [
        { kind: "text", text: "Question 3 " },
        { kind: "image", url: "/media/detail.png", original_file_name: "detail.png" },
      ],
      answer_text: "12",
      analysis_text: "Analysis 3",
      analysis_blocks: [{ kind: "text", text: "Analysis 3" }],
      options: [],
    },
    learning_state: {
      mastered: false,
      wrong_count: 2,
      last_result: "wrong",
      last_attempt_at: "2026-05-17T00:00:00.000Z",
    },
    recent_attempts: [
      {
        id: "attempt-1",
        question_id: "q-3",
        session_id: "session-1",
        result: "wrong",
        answer_payload: {},
        created_at: "2026-05-17T00:00:00.000Z",
      },
    ],
  });
});

afterEach(() => {
  cleanup();
});

test("错题回顾默认隐藏答案和解析", async () => {
  render(<WrongQuestionPage />);

  await screen.findByText("错题回顾");
  fireEvent.click(screen.getByRole("button", { name: "刷新错题" }));

  await screen.findByText("Question 3");
  fireEvent.click(screen.getByText("Question 3").closest("button") as HTMLElement);

  await waitFor(() => {
    expect(mockedApi.getPracticeQuestion).toHaveBeenCalledWith("q-3");
  });

  expect(screen.getByRole("button", { name: "显示答案" })).toBeInTheDocument();
  expect(screen.queryByText("答案：")).not.toBeInTheDocument();
  expect(screen.queryByText("解析")).not.toBeInTheDocument();
});

test("错题回顾可打开详情并显示答案", async () => {
  render(<WrongQuestionPage />);

  await screen.findByText("错题回顾");
  fireEvent.click(screen.getByRole("button", { name: "刷新错题" }));

  await screen.findByText("Question 3");
  fireEvent.click(screen.getByText("Question 3").closest("button") as HTMLElement);

  await waitFor(() => {
    expect(mockedApi.getPracticeQuestion).toHaveBeenCalledWith("q-3");
  });

  expect(screen.getByRole("img", { name: "detail.png" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "显示答案" }));
  expect(screen.getByText("答案：12")).toBeInTheDocument();
  expect(screen.getByText("解析")).toBeInTheDocument();
  expect(screen.getByText("Analysis 3")).toBeInTheDocument();
});
