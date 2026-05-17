import { useState } from "react";
import type { FormEvent } from "react";

import { type DuplicatePolicy, importPaper } from "../lib/api";

function cloneFormData(source: FormData): FormData {
  const copied = new FormData();
  source.forEach((value, key) => {
    copied.append(key, value);
  });
  return copied;
}

function isDuplicateImportError(error: unknown): error is Error & { code?: string } {
  if (!error || typeof error !== "object") {
    return false;
  }

  const code = (error as { code?: unknown }).code;
  return typeof code === "string" && code.toUpperCase() === "DUPLICATE_PAPER";
}

export function ImportPage() {
  const [message, setMessage] = useState("上传 Word 文档后，系统会自动解析试卷结构。");
  const [loading, setLoading] = useState(false);
  const [duplicatePrompt, setDuplicatePrompt] = useState<string | null>(null);
  const [pendingFormData, setPendingFormData] = useState<FormData | null>(null);

  async function submitImport(formData: FormData) {
    setLoading(true);
    try {
      const result = await importPaper(formData);
      setMessage(`解析完成：${result.paper.section_count} 个大题，${result.paper.question_count} 道题。`);
      setDuplicatePrompt(null);
      setPendingFormData(null);
    } catch (error) {
      if (isDuplicateImportError(error)) {
        setMessage(error.message || "检测到重复试卷");
        setDuplicatePrompt("检测到重复试卷，请选择继续方式。");
        setPendingFormData(cloneFormData(formData));
      } else {
        setMessage(error instanceof Error ? error.message : "导入失败");
        setDuplicatePrompt(null);
        setPendingFormData(null);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    await submitImport(formData);
  }

  async function handleDuplicateRetry(policy: DuplicatePolicy) {
    if (!pendingFormData) {
      return;
    }

    const retryFormData = cloneFormData(pendingFormData);
    retryFormData.set("duplicate_policy", policy);
    await submitImport(retryFormData);
  }

  return (
    <div className="page-grid">
      <div className="hero-block">
        <p className="eyebrow">试卷导入</p>
        <h3>把 Word 试卷变成结构化题库</h3>
        <p>支持题干、选项、答案、解析、图片、表格与公式的自动提取，并为后续审核保留追踪信息。</p>
      </div>

      <form className="form-card" onSubmit={handleSubmit}>
        <label>
          选择 Word 文件
          <input name="file" type="file" accept=".docx" required />
        </label>
        <label>
          学科
          <input name="subject" defaultValue="数学" required />
        </label>
        <label>
          地区
          <input name="region" defaultValue="江苏省苏州市" required />
        </label>
        <label>
          年份
          <input name="exam_year" type="number" defaultValue={2025} required />
        </label>
        <label>
          考试类型
          <input name="exam_type" defaultValue="中考真题" required />
        </label>

        <button type="submit" className="primary-btn" disabled={loading}>
          {loading ? "解析中..." : "开始解析"}
        </button>
      </form>

      <div className="status-card">
        <p>{message}</p>
        {duplicatePrompt ? (
          <div>
            <p>{duplicatePrompt}</p>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                type="button"
                className="primary-btn"
                disabled={loading}
                onClick={() => void handleDuplicateRetry("replace")}
              >
                替换旧试卷
              </button>
              <button
                type="button"
                className="secondary-btn"
                disabled={loading}
                onClick={() => void handleDuplicateRetry("keep_both")}
              >
                保留两份
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
