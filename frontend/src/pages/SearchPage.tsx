import { useState } from "react";
import type { FormEvent } from "react";

import { searchQuestions } from "../lib/api";

export function SearchPage() {
  const [query, setQuery] = useState({ subject: "数学", exam_year: "2025" });
  const [result, setResult] = useState<{ total: number; items: Array<Record<string, unknown>> }>({
    total: 0,
    items: [],
  });

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await searchQuestions({
      subject: query.subject,
      exam_year: Number(query.exam_year),
    });
    setResult(response);
  }

  return (
    <div className="page-grid">
      <div className="hero-block">
        <p className="eyebrow">题库检索</p>
        <h3>按学科、年份和标签快速筛题</h3>
      </div>

      <form className="form-card" onSubmit={handleSearch}>
        <label>
          学科
          <input value={query.subject} onChange={(e) => setQuery((q) => ({ ...q, subject: e.target.value }))} />
        </label>
        <label>
          年份
          <input
            value={query.exam_year}
            onChange={(e) => setQuery((q) => ({ ...q, exam_year: e.target.value }))}
          />
        </label>
        <button type="submit" className="primary-btn">
          开始检索
        </button>
      </form>

      <div className="status-card search-results-card">
        <div className="search-results-summary">结果数量：{result.total}</div>
        <div className="search-results-scroll">
          <div className="result-list">
            {result.items.map((item) => (
              <div key={String(item.question_id)} className="result-item">
                {String(item.question_no)}. {String(item.stem_text)}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
