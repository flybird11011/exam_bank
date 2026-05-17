import type { ReactNode } from "react";

type QuestionPanelProps = {
  title: string;
  children: ReactNode;
};

export function QuestionPanel({ title, children }: QuestionPanelProps) {
  return (
    <section className="panel">
      <div className="panel-title">{title}</div>
      <div className="panel-body">{children}</div>
    </section>
  );
}
