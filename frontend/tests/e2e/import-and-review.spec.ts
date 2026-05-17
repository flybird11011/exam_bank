import { test, expect } from "@playwright/test";

test("import a sample paper and open the review page", async ({ page }) => {
  await page.route("**/api/papers/import", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        parse_run_id: "run-1",
        status: "parsed",
        paper: {
          paper_id: "paper-1",
          title: "2025苏州中考数学试卷",
          subject: "数学",
          exam_year: 2025,
          section_count: 3,
          question_count: 27,
        },
      }),
    });
  });

  await page.route("**/api/papers", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          paper_id: "paper-1",
          parse_run_id: "run-1",
          title: "2025苏州中考数学试卷",
          subject: "数学",
          region: "江苏省苏州市",
          exam_year: 2025,
          exam_type: "中考真题",
          section_count: 3,
          question_count: 27,
          status: "parsed",
        },
      ]),
    });
  });

  await page.route("**/api/papers/paper-1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        paper_id: "paper-1",
        title: "2025苏州中考数学试卷",
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
                id: "question-1",
                question_no: "1",
                question_type: "single_choice",
                stem_text: "下列实数中，比 2 小的数是（ ）",
                answer_text: "D",
                analysis_text: "比较各选项与 2 的大小关系即可。",
                confidence: 0.92,
                status: "parsed",
                options: [
                  { id: "option-a", option_label: "A", option_text: "5", is_correct: false, order_no: 1 },
                  { id: "option-b", option_label: "B", option_text: "4", is_correct: false, order_no: 2 },
                  { id: "option-c", option_label: "C", option_text: "3", is_correct: false, order_no: 3 },
                  { id: "option-d", option_label: "D", option_text: "1", is_correct: true, order_no: 4 },
                ],
              },
            ],
          },
        ],
      }),
    });
  });

  await page.route("**/api/questions/question-1/tags", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          question_id: "question-1",
          tag_id: "tag-1",
          tag_type: "knowledge_point",
          name: "实数大小比较",
          source: "manual",
          confidence: 1,
        },
      ]),
    });
  });

  await page.route("**/api/review-logs", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "log-1",
          target_type: "question",
          target_id: "question-1",
          action_type: "update",
          before_json: "{}",
          after_json: "{}",
          reviewer: "system",
        },
      ]),
    });
  });

  await page.route("**/api/parse-runs/run-1/warnings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "warning-1",
          warning_code: "QUESTION_BOUNDARY_AMBIGUOUS",
          warning_level: "warning",
          warning_message: "第7题题目边界不清晰",
          warning_meta_json: "{}",
        },
      ]),
    });
  });

  await page.goto("http://127.0.0.1:4173/");
  await expect(page.getByRole("heading", { name: "把 Word 试卷变成结构化题库" })).toBeVisible();

  await page
    .getByLabel("选择 Word 文件")
    .setInputFiles("../backend/tests/fixtures/2025-suzhou-math-exam.docx");
  await page.getByLabel("学科").fill("数学");
  await page.getByLabel("地区").fill("江苏省苏州市");
  await page.getByLabel("年份").fill("2025");
  await page.getByLabel("考试类型").fill("中考真题");
  await page.getByRole("button", { name: "开始解析" }).click();

  await expect(page.getByText("解析完成")).toBeVisible();
  await page.getByRole("button", { name: "题目审核" }).click();
  await expect(page.getByText("题目内容")).toBeVisible();
  await expect(page.getByText("下列实数中，比 2 小的数是（ ）")).toBeVisible();
  await expect(page.getByText("实数大小比较")).toBeVisible();
});
