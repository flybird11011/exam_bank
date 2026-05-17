import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { ImportPage } from "../pages/ImportPage";
import * as api from "../lib/api";

vi.mock("../lib/api", () => ({
  importPaper: vi.fn(),
}));

const mockedApi = vi.mocked(api);

function submitImportForm(container: HTMLElement) {
  const fileInput = container.querySelector('input[name="file"]') as HTMLInputElement;
  const form = container.querySelector("form") as HTMLFormElement;
  const file = new File(["dummy"], "paper.docx", {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });

  fireEvent.change(fileInput, { target: { files: [file] } });
  fireEvent.submit(form);
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

test("检测到重复试卷时显示确认，并可用替换策略重试", async () => {
  mockedApi.importPaper
    .mockRejectedValueOnce(Object.assign(new Error("检测到重复试卷"), { code: "DUPLICATE_PAPER" }))
    .mockResolvedValueOnce({
      parse_run_id: "run-1",
      status: "parsed",
      paper: {
        paper_id: "paper-1",
        title: "Paper",
        subject: "math",
        exam_year: 2025,
        section_count: 2,
        question_count: 10,
      },
    });

  const { container } = render(<ImportPage />);
  submitImportForm(container);

  await screen.findByText("检测到重复试卷，请选择继续方式。");
  fireEvent.click(screen.getByRole("button", { name: "替换旧试卷" }));

  await waitFor(() => {
    expect(mockedApi.importPaper).toHaveBeenCalledTimes(2);
  });

  const secondFormData = mockedApi.importPaper.mock.calls[1][0] as FormData;
  expect(secondFormData.get("duplicate_policy")).toBe("replace");
});

test("检测到重复试卷时可用保留两份策略重试", async () => {
  mockedApi.importPaper
    .mockRejectedValueOnce(Object.assign(new Error("检测到重复试卷"), { code: "DUPLICATE_PAPER" }))
    .mockResolvedValueOnce({
      parse_run_id: "run-1",
      status: "parsed",
      paper: {
        paper_id: "paper-1",
        title: "Paper",
        subject: "math",
        exam_year: 2025,
        section_count: 3,
        question_count: 12,
      },
    });

  const { container } = render(<ImportPage />);
  submitImportForm(container);

  await screen.findByText("检测到重复试卷，请选择继续方式。");
  fireEvent.click(screen.getByRole("button", { name: "保留两份" }));

  await waitFor(() => {
    expect(mockedApi.importPaper).toHaveBeenCalledTimes(2);
  });

  const secondFormData = mockedApi.importPaper.mock.calls[1][0] as FormData;
  expect(secondFormData.get("duplicate_policy")).toBe("keep_both");
});
