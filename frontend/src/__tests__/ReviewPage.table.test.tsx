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
      title: "2025 江苏苏州中考真题数学试卷",
      subject: "数学",
      region: "江苏省苏州市",
      exam_year: 2025,
      exam_type: "中考真题",
      section_count: 1,
      question_count: 1,
      status: "parsed",
    },
  ]);

  mockedApi.getPaper.mockResolvedValue({
    paper_id: "paper-1",
    title: "2025 江苏苏州中考真题数学试卷",
    subject: "数学",
    region: "江苏省苏州市",
    exam_year: 2025,
    exam_type: "中考真题",
    parse_run_id: "run-1",
    sections: [
      {
        id: "section-1",
        title: "一、选择题",
        section_type: "single_choice",
        order_no: 1,
        questions: [
          {
            id: "question-7",
            question_no: "7",
            question_type: "single_choice",
            stem_text: "table question",
            stem_blocks: [
              { kind: "text", text: "表格如下：" },
              {
                kind: "table",
                rows: [
                  ["温度 t(℃)", "−10", "0", "10", "30"],
                  ["声音传播的速度 v(m/s)", "324", "330", "336", "348"],
                ],
              },
              { kind: "text", text: "研究发现 v 与 t 满足公式。" },
            ],
            answer_text: "B",
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

test("题干预览可渲染表格块", async () => {
  render(
    <MemoryRouter>
      <ReviewPage />
    </MemoryRouter>,
  );

  const preview = await screen.findByLabelText("题干预览");
  const table = within(preview).getByRole("table");
  expect(table).toBeInTheDocument();
  expect(within(table).getByText("温度 t(℃)")).toBeInTheDocument();
  expect(within(table).getByText("348")).toBeInTheDocument();
});
