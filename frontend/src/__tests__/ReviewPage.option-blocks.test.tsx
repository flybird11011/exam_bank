import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";

import { ReviewPage } from "../pages/ReviewPage";
import * as api from "../lib/api";

vi.mock("../lib/api", () => ({
  addQuestionTag: vi.fn(),
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
      title: "paper",
      subject: "math",
      region: "suzhou",
      exam_year: 2025,
      exam_type: "exam",
      section_count: 1,
      question_count: 1,
      status: "parsed",
    },
  ]);

  mockedApi.getPaper.mockResolvedValue({
    paper_id: "paper-1",
    title: "paper",
    subject: "math",
    region: "suzhou",
    exam_year: 2025,
    exam_type: "exam",
    parse_run_id: "run-1",
    sections: [
      {
        id: "section-1",
        title: "section",
        section_type: "single_choice",
        order_no: 1,
        questions: [
          {
            id: "question-1",
            question_no: "8",
            question_type: "single_choice",
            stem_text: "stem",
            stem_blocks: [],
            answer_text: "A",
            analysis_text: "",
            confidence: 0.92,
            status: "parsed",
            options: [
              {
                id: "option-a",
                option_label: "A",
                option_text: "A'D // BE",
                option_blocks: [
                  { kind: "text", text: "A'" },
                  { kind: "text", text: "D", source: "formula" },
                  { kind: "text", text: " // " },
                  { kind: "text", text: "BE", source: "formula" },
                ],
                is_correct: false,
                order_no: 1,
              },
            ],
          },
        ],
      },
    ],
  });

  mockedApi.listParseWarnings.mockResolvedValue([]);
  mockedApi.listReviewLogs.mockResolvedValue([]);
  mockedApi.listQuestionTags.mockResolvedValue([]);
});

test("选项块按原顺序行内显示", async () => {
  render(
    <MemoryRouter>
      <ReviewPage />
    </MemoryRouter>,
  );

  const optionPreview = await screen.findByText("A'");
  expect(optionPreview.closest(".option-preview")).toHaveTextContent("A'D // BE");
  expect(optionPreview.closest(".option-preview")?.querySelectorAll(".inline-content-formula")).toHaveLength(2);
});

test("表格里的字母标签不会作为选项预览内容", async () => {
  mockedApi.getPaper.mockResolvedValueOnce({
    paper_id: "paper-1",
    title: "paper",
    subject: "math",
    region: "suzhou",
    exam_year: 2025,
    exam_type: "exam",
    parse_run_id: "run-1",
    sections: [
      {
        id: "section-1",
        title: "section",
        section_type: "single_choice",
        order_no: 1,
        questions: [
          {
            id: "question-1",
            question_no: "4",
            question_type: "single_choice",
            stem_text: "stem",
            stem_blocks: [],
            answer_text: "B",
            analysis_text: "",
            confidence: 0.92,
            status: "parsed",
            options: [
              {
                id: "option-a",
                option_label: "A",
                option_text: "亭台在水中的“倒影”",
                option_blocks: [{ kind: "text", text: "A" }],
                is_correct: false,
                order_no: 1,
              },
            ],
          },
        ],
      },
    ],
  });

  render(
    <MemoryRouter>
      <ReviewPage />
    </MemoryRouter>,
  );

  const preview = await screen.findByText("亭台在水中的“倒影”");
  const optionPreview = preview.closest(".option-preview");
  expect(optionPreview).toHaveTextContent("亭台在水中的“倒影”");
  expect(within(optionPreview as HTMLElement).queryByText(/^A$/)).not.toBeInTheDocument();
});
