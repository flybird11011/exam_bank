import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import * as api from "../lib/api";
import { ReviewPage } from "../pages/ReviewPage";

vi.mock("../lib/api", () => ({
  addQuestionTag: vi.fn(),
  deletePaper: vi.fn(),
  getPaper: vi.fn(),
  listPapers: vi.fn(),
  listParseWarnings: vi.fn(),
  listQuestionTags: vi.fn(),
  listReviewLogs: vi.fn(),
  removeQuestionTag: vi.fn(),
  updateQuestion: vi.fn(),
}));

const mockedApi = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();

  mockedApi.listPapers.mockResolvedValue([
    {
      paper_id: "paper-1",
      parse_run_id: "run-1",
      title: "Practice Paper",
      subject: "数学",
      region: "苏州",
      exam_year: 2025,
      exam_type: "exam",
      section_count: 1,
      question_count: 2,
      status: "parsed",
    },
  ]);

  mockedApi.listParseWarnings.mockResolvedValue([]);
  mockedApi.listQuestionTags.mockResolvedValue([]);
  mockedApi.listReviewLogs.mockResolvedValue([]);
  mockedApi.deletePaper.mockResolvedValue({
    paper_id: "paper-1",
    deleted: true,
    warnings: [],
  });
  mockedApi.updateQuestion.mockResolvedValue({
    question_type: "single_choice",
    stem_text: "修改后的题干",
    answer_text: "B",
    analysis_text: "修改后的解析",
    status: "parsed",
    options: [
      { id: "option-a", option_label: "A", option_text: "10", option_blocks: [], is_correct: false, order_no: 1 },
      { id: "option-b", option_label: "B", option_text: "4", option_blocks: [], is_correct: true, order_no: 2 },
      { id: "option-c", option_label: "C", option_text: "3", option_blocks: [], is_correct: false, order_no: 3 },
      { id: "option-d", option_label: "D", option_text: "1", option_blocks: [], is_correct: false, order_no: 4 },
    ],
  });
  mockedApi.getPaper.mockResolvedValue({
    paper_id: "paper-1",
    title: "Practice Paper",
    subject: "数学",
    region: "苏州",
    exam_year: 2025,
    exam_type: "exam",
    parse_run_id: "run-1",
    sections: [
      {
        id: "section-1",
        title: "第一部分",
        section_type: "single_choice",
        order_no: 1,
        questions: [
          {
            id: "question-1",
            question_no: "1",
            question_type: "single_choice",
            stem_text: "原始题干",
            stem_blocks: [
              { kind: "text", text: "原始题干前半段" },
              { kind: "image", url: "/media/paper-1/question-1/stem-image.png", original_file_name: "stem-image.wmf" },
              { kind: "text", text: "原始题干后半段" },
            ],
            answer_text: "D",
            analysis_text: "原始解析",
            analysis_blocks: [
              { kind: "text", text: "解析图示" },
              { kind: "image", url: "/media/paper-1/question-1/analysis-image.png", original_file_name: "analysis-image.png" },
              { kind: "text", text: "a×b" },
            ],
            confidence: 0.92,
            status: "parsed",
            options: [
              { id: "option-a", option_label: "A", option_text: "5", option_blocks: [], is_correct: false, order_no: 1 },
              { id: "option-b", option_label: "B", option_text: "4", option_blocks: [], is_correct: false, order_no: 2 },
              { id: "option-c", option_label: "C", option_text: "3", option_blocks: [], is_correct: false, order_no: 3 },
              { id: "option-d", option_label: "D", option_text: "1", option_blocks: [], is_correct: true, order_no: 4 },
            ],
          },
        ],
      },
    ],
  });
});

afterEach(() => {
  cleanup();
});

test("supports editing a question and marking the correct answer", async () => {
  render(
    <MemoryRouter>
      <ReviewPage />
    </MemoryRouter>,
  );

  await screen.findByDisplayValue("原始题干");
  expect(screen.queryByText("已修改")).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("题干"), { target: { value: "修改后的题干" } });
  fireEvent.change(screen.getByLabelText("解析"), { target: { value: "修改后的解析" } });
  fireEvent.change(screen.getByLabelText("题型"), { target: { value: "single_choice" } });
  fireEvent.change(screen.getByLabelText("选项 A"), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: "设为正确答案 B" }));

  expect(screen.getByText("正确")).toBeInTheDocument();
  expect(screen.getByText("已修改")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "恢复原文" }));

  expect(screen.queryByText("已修改")).not.toBeInTheDocument();
  expect(screen.getByDisplayValue("原始题干")).toBeInTheDocument();
  expect(screen.getByDisplayValue("D")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("题干"), { target: { value: "修改后的题干" } });
  fireEvent.change(screen.getByLabelText("解析"), { target: { value: "修改后的解析" } });
  fireEvent.change(screen.getByLabelText("题型"), { target: { value: "single_choice" } });
  fireEvent.change(screen.getByLabelText("选项 A"), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: "设为正确答案 B" }));
  fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

  await waitFor(() => {
    expect(mockedApi.updateQuestion).toHaveBeenCalledWith("question-1", {
      stem_text: "修改后的题干",
      answer_text: "B",
      analysis_text: "修改后的解析",
      question_type: "single_choice",
      options: [
        { option_label: "A", option_text: "10", is_correct: false },
        { option_label: "B", option_text: "4", is_correct: true },
        { option_label: "C", option_text: "3", is_correct: false },
        { option_label: "D", option_text: "1", is_correct: false },
      ],
    });
  });

  await waitFor(() => {
    expect(mockedApi.listReviewLogs).toHaveBeenCalledTimes(2);
  });
});

test("renders stem preview text and image blocks", async () => {
  render(
    <MemoryRouter>
      <ReviewPage />
    </MemoryRouter>,
  );

  await screen.findByText("原始题干前半段");

  const preview = screen.getByLabelText("题干预览");
  expect(preview.children).toHaveLength(3);
  expect(preview.children[0]).toHaveTextContent("原始题干前半段");
  expect(screen.getByRole("img", { name: "stem-image.wmf" })).toBeInTheDocument();
  expect(preview.children[2]).toHaveTextContent("原始题干后半段");
});

test("renders analysis preview blocks", async () => {
  render(
    <MemoryRouter>
      <ReviewPage />
    </MemoryRouter>,
  );

  await screen.findByText("原始题干前半段");
  const answerLine = screen.getByText("答案：D");
  const analysisPanel = answerLine.closest(".panel");
  expect(analysisPanel).not.toBeNull();

  const scoped = within(analysisPanel as HTMLElement);
  expect(scoped.getByRole("img", { name: "analysis-image.png" })).toBeInTheDocument();
  expect(scoped.getByText("a×b")).toBeInTheDocument();
});

test("can delete an entire paper and refresh the list", async () => {
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
  mockedApi.listPapers.mockResolvedValueOnce([
    {
      paper_id: "paper-1",
      parse_run_id: "run-1",
      title: "Practice Paper",
      subject: "数学",
      region: "苏州",
      exam_year: 2025,
      exam_type: "exam",
      section_count: 1,
      question_count: 2,
      status: "parsed",
    },
  ]);
  mockedApi.listPapers.mockResolvedValueOnce([]);

  render(
    <MemoryRouter>
      <ReviewPage />
    </MemoryRouter>,
  );

  await screen.findByText("第一部分");
  fireEvent.click(screen.getByRole("button", { name: "删除试卷" }));

  await waitFor(() => {
    expect(mockedApi.deletePaper).toHaveBeenCalledWith("paper-1");
  });

  await waitFor(() => {
    expect(screen.getByText("没有可显示的题目。")).toBeInTheDocument();
  });

  confirmSpy.mockRestore();
});
