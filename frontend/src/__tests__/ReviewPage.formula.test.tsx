import { render, screen } from "@testing-library/react";
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
            question_no: "3",
            question_type: "single_choice",
            stem_text: "stem",
            stem_blocks: [
              { kind: "text", text: "f(x)=" },
              { kind: "text", text: "x^2+1", source: "formula" },
              { kind: "text", text: ", end." },
            ],
            answer_text: "D",
            analysis_text: "analysis",
            confidence: 0.92,
            status: "parsed",
            options: [],
          },
        ],
      },
    ],
  });

  mockedApi.listParseWarnings.mockResolvedValue([]);
  mockedApi.listReviewLogs.mockResolvedValue([]);
  mockedApi.listQuestionTags.mockResolvedValue([]);
});

test("公式块保持行内显示", async () => {
  render(
    <MemoryRouter>
      <ReviewPage />
    </MemoryRouter>,
  );

  const preview = await screen.findByLabelText("题干预览");
  expect(preview.children).toHaveLength(1);
  expect(preview).toHaveTextContent("f(x)=x^2+1, end.");
  expect(preview.querySelector(".inline-content-formula")).toBeTruthy();
  expect(screen.queryByRole("img", { name: /x\^2\+1/ })).not.toBeInTheDocument();
});
