import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { within } from "@testing-library/dom";
import { expect, test } from "vitest";

import { App } from "../App";

test("显示导航框架", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );

  const nav = screen.getByRole("navigation");
  expect(within(nav).getByText("试卷导入")).toBeInTheDocument();
  expect(within(nav).getByText("题目审核")).toBeInTheDocument();
  expect(within(nav).getByText("练习")).toBeInTheDocument();
  expect(within(nav).getByText("错题回顾")).toBeInTheDocument();
  expect(within(nav).getByText("题库检索")).toBeInTheDocument();
});
