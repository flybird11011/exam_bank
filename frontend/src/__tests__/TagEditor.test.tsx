import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { TagEditor } from "../components/TagEditor";

test("标签缺失时也能安全渲染", () => {
  render(<TagEditor tags={undefined as never} onAdd={vi.fn()} onRemove={vi.fn()} />);

  expect(screen.getByLabelText("新标签")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "+ 添加标签" })).toBeInTheDocument();
});
