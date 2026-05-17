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
      title: "2025 江苏苏州中考数学试卷",
      subject: "数学",
      region: "苏州",
      exam_year: 2025,
      exam_type: "中考真题",
      section_count: 1,
      question_count: 1,
      status: "parsed",
    },
  ]);

  mockedApi.getPaper.mockResolvedValue({
    paper_id: "paper-1",
    title: "2025 江苏苏州中考数学试卷",
    subject: "数学",
    region: "苏州",
    exam_year: 2025,
    exam_type: "中考真题",
    parse_run_id: "run-1",
    sections: [
      {
        id: "section-1",
        title: "选择题",
        section_type: "single_choice",
        order_no: 1,
        questions: [
          {
            id: "question-1",
            question_no: "3",
            question_type: "single_choice",
            stem_text: "stem",
            stem_blocks: [
              { kind: "text", text: "同比增长" },
              { kind: "text", text: "11.5%", source: "ocr" },
              { kind: "text", text: "，数据显示202317000用科学记数法可表示为：", source: "ocr" },
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

test("OCR 文本按原顺序行内显示", async () => {
  render(
    <MemoryRouter>
      <ReviewPage />
    </MemoryRouter>,
  );

  const preview = await screen.findByLabelText("题干预览");
  expect(preview.children).toHaveLength(1);
  expect(preview).toHaveTextContent("同比增长11.5%，数据显示202317000用科学记数法可表示为：");
});
