import { test, expect } from "@playwright/test";

test("search imported questions by subject and year", async ({ page }) => {
  await page.route("**/api/questions/search?*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 1,
        items: [
          {
            question_id: "q-1",
            question_no: "1",
            stem_text: "下列实数中，比 2 小的数是（ ）",
          },
        ],
      }),
    });
  });

  await page.goto("http://127.0.0.1:4173/");
  await page.getByRole("button", { name: "题库检索" }).click();
  await page.getByLabel("学科").fill("数学");
  await page.getByLabel("年份").fill("2025");
  await page.getByRole("button", { name: "开始检索" }).click();

  await expect(page.getByText("结果数量")).toBeVisible();
});
