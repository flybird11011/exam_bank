import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { PracticePage } from "../pages/PracticePage";
import * as api from "../lib/api";

vi.mock("../lib/api", () => ({
  createPracticeSession: vi.fn(),
  deletePaper: vi.fn(),
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

  mockedApi.deletePaper.mockResolvedValue({
    paper_id: "paper-1",
    deleted: true,
    warnings: [],
  });

  mockedApi.createPracticeSession.mockResolvedValue({
    session: {
      id: "session-1",
      paper_id: "paper-1",
      mode: "paper",
      randomized: false,
      exclude_mastered: true,
      single_choice_count: 2,
      fill_blank_count: 0,
      short_answer_count: 0,
      status: "running",
      created_at: "2026-05-17T00:00:00.000Z",
      question_ids: ["q-1", "q-2"],
      selected_counts: {
        single_choice: 2,
        fill_blank: 0,
        short_answer: 0,
      },
      available_counts: {
        single_choice: 2,
        fill_blank: 0,
        short_answer: 0,
      },
    },
    questions: [
      {
        question_id: "q-1",
        paper_id: "paper-1",
        question_no: "1",
        order_no: 1,
        question_type: "single_choice",
        stem_text: "Question 1",
        stem_blocks: [
          { kind: "text", text: "Question 1 " },
          { kind: "image", url: "/media/stem.png", original_file_name: "stem.png" },
        ],
        answer_text: "A",
        analysis_text: "Analysis 1",
        analysis_blocks: [
          { kind: "text", text: "Analysis 1 " },
          { kind: "table", rows: [["a", "b"], ["1", "2"]] },
        ],
        options: [
          {
            id: "q-1-a",
            option_label: "A",
            option_text: "Option A",
            option_blocks: [{ kind: "text", text: "Option A" }],
            is_correct: true,
            order_no: 1,
          },
          {
            id: "q-1-b",
            option_label: "B",
            option_text: "Option B",
            option_blocks: [{ kind: "text", text: "Option B" }],
            is_correct: false,
            order_no: 2,
          },
        ],
        mastered: false,
        wrong_count: 0,
        last_result: null,
        last_attempt_at: null,
      },
      {
        question_id: "q-2",
        paper_id: "paper-1",
        question_no: "2",
        order_no: 2,
        question_type: "single_choice",
        stem_text: "Question 2",
        stem_blocks: [{ kind: "text", text: "Question 2" }],
        answer_text: "B",
        analysis_text: "Analysis 2",
        analysis_blocks: [{ kind: "text", text: "Analysis 2" }],
        options: [
          {
            id: "q-2-a",
            option_label: "A",
            option_text: "Option A2",
            option_blocks: [{ kind: "text", text: "Option A2" }],
            is_correct: false,
            order_no: 1,
          },
          {
            id: "q-2-b",
            option_label: "B",
            option_text: "Option B2",
            option_blocks: [{ kind: "text", text: "Option B2" }],
            is_correct: true,
            order_no: 2,
          },
        ],
        mastered: false,
        wrong_count: 0,
        last_result: null,
        last_attempt_at: null,
      },
    ],
  });

  mockedApi.recordPracticeAttempt.mockImplementation(async ({ result }) => ({
    learning_state: {
      mastered: result !== "wrong",
      wrong_count: result === "wrong" ? 1 : 0,
      last_result: result,
      last_attempt_at: "2026-05-17T00:00:00.000Z",
    },
  }));
});

afterEach(() => {
  cleanup();
});

test("榛樿鍏ㄩ儴璇曞嵎鏃朵篃鍙互寮€濮嬬粌涔?", async () => {
  render(<PracticePage />);

  await screen.findByText("缁冧範妯″紡");
  fireEvent.click(screen.getByRole("button", { name: "Start Practice" }));

  await waitFor(() => {
    expect(mockedApi.createPracticeSession).toHaveBeenCalledWith({
      paper_id: undefined,
      randomized: false,
      exclude_mastered: false,
      single_choice_count: 8,
      fill_blank_count: 8,
      short_answer_count: 11,
    });
  });

  await screen.findByText("Question 1");
  expect(screen.getByRole("img", { name: "stem.png" })).toBeInTheDocument();
  expect(screen.queryByText("Analysis 1")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "纭绛旀" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "鍙栨秷閫夋嫨" })).toBeInTheDocument();
});

test("鍗曢€夐鍏堥€変腑鍐嶇‘璁ゅ悗鎵嶄細鑷姩鍒ゅ畾骞惰繘鍏ヤ笅涓€棰?", async () => {
  render(<PracticePage />);

  await screen.findByText("缁冧範妯″紡");
  fireEvent.click(screen.getByRole("button", { name: "Start Practice" }));

  await screen.findByText("Question 1");
  const optionA = screen.getByRole("button", { name: /閫夐」 A/ });
  fireEvent.click(optionA);
  expect(optionA).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("Selected: A")).toBeInTheDocument();
  expect(mockedApi.recordPracticeAttempt).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "纭绛旀" }));

  await waitFor(() => {
    expect(mockedApi.recordPracticeAttempt).toHaveBeenCalledWith({
      question_id: "q-1",
      result: "correct",
      session_id: "session-1",
      answer_payload: {
        selected_option_id: "q-1-a",
        selected_option_label: "A",
        selected_option_text: "Option A",
      },
    });
  });

  await screen.findByText("Question 2");
});

test("閫夋嫨閿欒閫夐」鍚庣‘璁や篃浼氳嚜鍔ㄨ褰曞苟鍒囨崲鍒颁笅涓€棰?", async () => {
  render(<PracticePage />);

  await screen.findByText("缁冧範妯″紡");
  fireEvent.click(screen.getByRole("button", { name: "Start Practice" }));

  await screen.findByText("Question 1");
  fireEvent.click(screen.getByRole("button", { name: /閫夐」 B/ }));
  fireEvent.click(screen.getByRole("button", { name: "纭绛旀" }));

  await waitFor(() => {
    expect(mockedApi.recordPracticeAttempt).toHaveBeenCalledWith({
      question_id: "q-1",
      result: "wrong",
      session_id: "session-1",
      answer_payload: {
        selected_option_id: "q-1-b",
        selected_option_label: "B",
        selected_option_text: "Option B",
      },
    });
  });

  await screen.findByText("Question 2");
});

test("缁冧範椤典笉鍐嶅寘鍚鍐呴敊棰樻煡璇㈤潰鏉?", async () => {
  render(<PracticePage />);

  await screen.findByText("缁冧範妯″紡");
  expect(screen.queryByText("閿欓鍥為【")).not.toBeInTheDocument();
  expect(screen.queryByText("鍒锋柊閿欓")).not.toBeInTheDocument();
  expect(screen.queryByText("閿欓鍒楄〃")).not.toBeInTheDocument();
});

test("can delete a selected paper from the practice page", async () => {
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
  mockedApi.listPapers.mockResolvedValueOnce([
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
  mockedApi.listPapers.mockResolvedValueOnce([]);

  render(<PracticePage />);

  await screen.findByText("缁冧範妯″紡");
  fireEvent.change(screen.getByLabelText("璇曞嵎"), { target: { value: "paper-1" } });
  fireEvent.click(screen.getByRole("button", { name: "删除当前试卷" }));

  await waitFor(() => {
    expect(mockedApi.deletePaper).toHaveBeenCalledWith("paper-1");
  });

  await waitFor(() => {
    expect(screen.getByText("试卷已删除")).toBeInTheDocument();
  });

  confirmSpy.mockRestore();
});



