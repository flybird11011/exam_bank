import { useEffect, useMemo, useState } from "react";

import {
  addQuestionTag,
  deletePaper,
  getPaper,
  listPapers,
  listParseWarnings,
  listQuestionTags,
  listReviewLogs,
  removeQuestionTag,
  updateQuestion,
  type PaperDetail,
  type PaperQuestion,
  type PaperSummary,
  type ParseWarning,
  type QuestionTag,
  type ReviewLog,
  type StemBlock,
} from "../lib/api";
import { QuestionPanel } from "../components/QuestionPanel";
import { RichContentBlocks } from "../components/RichContent";
import { TagEditor } from "../components/TagEditor";

function flattenQuestions(paper: PaperDetail | null): PaperQuestion[] {
  if (!paper) {
    return [];
  }

  return paper.sections.flatMap((section) => section.questions);
}

type QuestionDraft = {
  question_type: string;
  stem_text: string;
  answer_text: string;
  analysis_text: string;
  options: Array<{
    option_label: string;
    option_text: string;
    is_correct: boolean;
  }>;
};

function createDraft(question: PaperQuestion | null): QuestionDraft {
  return {
    question_type: question?.question_type ?? "unknown",
    stem_text: question?.stem_text ?? "",
    answer_text: question?.answer_text ?? "",
    analysis_text: question?.analysis_text ?? "",
    options: (question?.options ?? []).map((option) => ({
      option_label: option.option_label,
      option_text: option.option_text ?? "",
      is_correct: Boolean(option.is_correct),
    })),
  };
}

function getStemBlocks(question: PaperQuestion | null): StemBlock[] {
  if (!question) {
    return [];
  }

  if (question.stem_blocks?.length) {
    return question.stem_blocks;
  }

  if (question.stem_text) {
    return [{ kind: "text", text: question.stem_text }];
  }

  return [];
}

function getAnalysisBlocks(question: PaperQuestion | null): StemBlock[] {
  if (!question) {
    return [];
  }

  if (question.analysis_blocks?.length) {
    return question.analysis_blocks;
  }

  if (question.analysis_text) {
    return [{ kind: "text", text: question.analysis_text }];
  }

  return [];
}

function getOptionBlocks(question: PaperQuestion | null, optionLabel: string): StemBlock[] {
  const option = question?.options?.find((item) => item.option_label === optionLabel);
  return option?.option_blocks ?? [];
}

function updateQuestionInPaper(
  paper: PaperDetail,
  questionId: string,
  updater: (question: PaperQuestion) => PaperQuestion,
): PaperDetail {
  return {
    ...paper,
    sections: paper.sections.map((section) => ({
      ...section,
      questions: section.questions.map((question) => (question.id === questionId ? updater(question) : question)),
    })),
  };
}

export function ReviewPage() {
  const srOnlyStyle = {
    position: "absolute",
    width: 1,
    height: 1,
    padding: 0,
    margin: -1,
    overflow: "hidden",
    clip: "rect(0, 0, 0, 0)",
    whiteSpace: "nowrap",
    border: 0,
  } as const;

  const [papers, setPapers] = useState<PaperSummary[]>([]);
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);
  const [draftQuestion, setDraftQuestion] = useState<QuestionDraft>(createDraft(null));
  const [questionTags, setQuestionTags] = useState<QuestionTag[]>([]);
  const [warnings, setWarnings] = useState<ParseWarning[]>([]);
  const [reviewLogs, setReviewLogs] = useState<ReviewLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const questions = useMemo(() => flattenQuestions(paper), [paper]);
  const selectedQuestion = useMemo(
    () => questions.find((question) => question.id === selectedQuestionId) ?? questions[0] ?? null,
    [questions, selectedQuestionId],
  );
  const selectedSectionLabel = useMemo(() => {
    if (!paper || !selectedQuestion) {
      return "";
    }

    for (const section of paper.sections) {
      if (section.questions.some((question) => question.id === selectedQuestion.id)) {
        return section.title;
      }
    }

    return "";
  }, [paper, selectedQuestion]);
  const originalDraft = useMemo(() => createDraft(selectedQuestion), [selectedQuestion]);
  const questionIsModified = useMemo(
    () => JSON.stringify(draftQuestion) !== JSON.stringify(originalDraft),
    [draftQuestion, originalDraft],
  );

  useEffect(() => {
    setDraftQuestion(createDraft(selectedQuestion));
  }, [selectedQuestion]);

  useEffect(() => {
    let mounted = true;

    async function loadPapers() {
      try {
        setLoading(true);
        const paperList = await listPapers();
        if (!mounted) {
          return;
        }

        setPapers(paperList);
        setSelectedPaperId(paperList[0]?.paper_id ?? null);
      } catch (loadError) {
        if (mounted) {
          setError(loadError instanceof Error ? loadError.message : "加载试卷失败");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadPapers();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedPaperId) {
      setPaper(null);
      setSelectedQuestionId(null);
      setQuestionTags([]);
      setWarnings([]);
      return;
    }

    let mounted = true;

    async function loadPaperDetail() {
      try {
        setError(null);
        const detail = await getPaper(selectedPaperId);
        if (!mounted) {
          return;
        }

        setPaper(detail);
        const firstQuestion = detail.sections[0]?.questions[0] ?? null;
        setSelectedQuestionId(firstQuestion?.id ?? null);

        if (detail.parse_run_id) {
          const parseWarnings = await listParseWarnings(detail.parse_run_id);
          if (mounted) {
            setWarnings(parseWarnings);
          }
        } else {
          setWarnings([]);
        }
      } catch (loadError) {
        if (mounted) {
          setError(loadError instanceof Error ? loadError.message : "加载试卷详情失败");
        }
      }
    }

    loadPaperDetail();

    return () => {
      mounted = false;
    };
  }, [selectedPaperId]);

  useEffect(() => {
    let mounted = true;

    async function loadLogs() {
      try {
        const logs = await listReviewLogs();
        if (mounted) {
          setReviewLogs(logs);
        }
      } catch {
        if (mounted) {
          setReviewLogs([]);
        }
      }
    }

    loadLogs();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedQuestion) {
      setQuestionTags([]);
      return;
    }

    let mounted = true;

    async function loadTags() {
      try {
        const tags = await listQuestionTags(selectedQuestion.id);
        if (mounted) {
          setQuestionTags(Array.isArray(tags) ? tags : []);
        }
      } catch (loadError) {
        if (mounted) {
          setError(loadError instanceof Error ? loadError.message : "加载标签失败");
        }
      }
    }

    loadTags();

    return () => {
      mounted = false;
    };
  }, [selectedQuestion?.id]);

  async function refreshLogs() {
    try {
      setReviewLogs(await listReviewLogs());
    } catch {
      setReviewLogs([]);
    }
  }

  function handleRestoreOriginal() {
    setDraftQuestion(createDraft(selectedQuestion));
  }

  function handleMarkCorrectAnswer(optionLabel: string) {
    setDraftQuestion((current) => ({
      ...current,
      answer_text: optionLabel,
      options: current.options.map((option) => ({
        ...option,
        is_correct: option.option_label === optionLabel,
      })),
    }));
  }

  async function handleAddTag(payload: { tag_type: string; name: string }) {
    if (!selectedQuestion) {
      return;
    }

    setSaving(true);
    try {
      await addQuestionTag(selectedQuestion.id, {
        tag_type: payload.tag_type,
        name: payload.name,
        source: "manual",
        confidence: 1,
      });
      const refreshedTags = await listQuestionTags(selectedQuestion.id);
      setQuestionTags(Array.isArray(refreshedTags) ? refreshedTags : []);
      await refreshLogs();
    } finally {
      setSaving(false);
    }
  }

  async function handleRemoveTag(tag: QuestionTag) {
    if (!selectedQuestion) {
      return;
    }

    setSaving(true);
    try {
      await removeQuestionTag(selectedQuestion.id, tag.tag_id, tag.source);
      const refreshedTags = await listQuestionTags(selectedQuestion.id);
      setQuestionTags(Array.isArray(refreshedTags) ? refreshedTags : []);
      await refreshLogs();
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveQuestion() {
    if (!selectedQuestion) {
      return;
    }

    setSaving(true);
    try {
      const updated = await updateQuestion(selectedQuestion.id, {
        question_type: draftQuestion.question_type,
        stem_text: draftQuestion.stem_text,
        answer_text: draftQuestion.answer_text,
        analysis_text: draftQuestion.analysis_text,
        options: draftQuestion.options,
      });

      setPaper((current) =>
        current
          ? updateQuestionInPaper(current, selectedQuestion.id, (question) => ({
              ...question,
              question_type: String(updated.question_type ?? question.question_type),
              stem_text: String(updated.stem_text ?? question.stem_text ?? ""),
              answer_text: String(updated.answer_text ?? question.answer_text ?? ""),
              analysis_text: String(updated.analysis_text ?? question.analysis_text ?? ""),
              status: String(updated.status ?? question.status),
              options:
                updated.options?.map((option) => ({
                  id: option.id,
                  option_label: option.option_label,
                  option_text: option.option_text,
                  option_blocks:
                    option.option_blocks ??
                    question.options?.find((item) => item.option_label === option.option_label)?.option_blocks ??
                    [],
                  is_correct: option.is_correct,
                  order_no: option.order_no,
                })) ?? question.options,
            }))
          : current,
      );
      await refreshLogs();
    } finally {
      setSaving(false);
    }
  }

  async function handleConfirmQuestion() {
    if (!selectedQuestion) {
      return;
    }

    setSaving(true);
    try {
      const updated = await updateQuestion(selectedQuestion.id, { status: "confirmed" });
      setPaper((current) =>
        current
          ? updateQuestionInPaper(current, selectedQuestion.id, (question) => ({
              ...question,
              status: String(updated.status),
              options: question.options?.map((option) => ({
                ...option,
                option_blocks: option.option_blocks ?? [],
              })),
            }))
          : current,
      );
      await refreshLogs();
    } finally {
      setSaving(false);
    }
  }

  async function handleDeletePaper() {
    if (!selectedPaper) {
      return;
    }

    const confirmed = window.confirm(
      `确定要删除试卷「${selectedPaper.title}」吗？删除后会同时清除该试卷及其关联数据，且无法恢复。`,
    );
    if (!confirmed) {
      return;
    }

    setSaving(true);
    try {
      await deletePaper(selectedPaper.paper_id);
      const refreshedPapers = await listPapers();
      setPapers(refreshedPapers);
      setPaper(null);
      setSelectedQuestionId(null);
      setQuestionTags([]);
      setWarnings([]);
      setError(null);
      setSelectedPaperId(refreshedPapers[0]?.paper_id ?? null);
      await refreshLogs();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "删除试卷失败");
    } finally {
      setSaving(false);
    }
  }

  const selectedPaper = papers.find((item) => item.paper_id === selectedPaperId) ?? null;
  const recentLogs = selectedQuestion
    ? reviewLogs.filter((log) => log.target_id === selectedQuestion.id).slice(0, 5)
    : reviewLogs.slice(0, 5);
  const stemBlocks = getStemBlocks(selectedQuestion);
  const analysisBlocks = getAnalysisBlocks(selectedQuestion);

  return (
    <div className="review-grid">
      <aside className="review-nav">
        <div className="section-card">
          <div className="panel-title">试卷目录</div>
          <div className="paper-switcher">
            {papers.length === 0 ? (
              <div className="empty-state">暂无试卷，请先导入 Word 文档。</div>
            ) : (
              papers.map((item) => (
                <button
                  key={item.paper_id}
                  className={`nav-question ${item.paper_id === selectedPaperId ? "active" : ""}`}
                  type="button"
                  onClick={() => setSelectedPaperId(item.paper_id)}
                >
                  {item.title}
                </button>
              ))
            )}
          </div>
        </div>

        <div className="section-card">
          <div className="panel-title">题目列表</div>
          <div className="question-switcher">
            {questions.length === 0 ? (
              <div className="empty-state">选中试卷后这里会显示题目。</div>
            ) : (
              questions.map((question) => (
                <button
                  key={question.id}
                  className={`nav-question ${question.id === selectedQuestion?.id ? "active" : ""}`}
                  type="button"
                  onClick={() => setSelectedQuestionId(question.id)}
                >
                  {question.question_no}. {question.question_type}
                </button>
              ))
            )}
          </div>
        </div>
      </aside>

      <section className="review-main">
        <QuestionPanel title="题目内容">
          {selectedQuestion ? (
            <>
              <div className="question-meta-line">
                <span>{selectedSectionLabel}</span>
                <span>{selectedQuestion.question_type}</span>
                <span>{selectedQuestion.status}</span>
                {questionIsModified ? <span className="dirty-badge">已修改</span> : null}
              </div>

              <div className="question-stem-preview" aria-label="题干预览">
                <RichContentBlocks blocks={stemBlocks} emptyLabel="当前题干没有可显示的内容。" />
              </div>

              <div className="question-edit-grid">
                <label className="field-group">
                  <label htmlFor="review-stem" style={srOnlyStyle}>
                    题干
                  </label>
                  <span className="field-label">题干</span>
                  <textarea
                    id="review-stem"
                    className="field-input field-textarea"
                    rows={6}
                    value={draftQuestion.stem_text}
                    onChange={(event) =>
                      setDraftQuestion((current) => ({
                        ...current,
                        stem_text: event.target.value,
                      }))
                    }
                  />
                </label>

                <label className="field-group">
                  <label htmlFor="review-type" style={srOnlyStyle}>
                    题型
                  </label>
                  <span className="field-label">题型</span>
                  <select
                    id="review-type"
                    className="field-input"
                    value={draftQuestion.question_type}
                    onChange={(event) =>
                      setDraftQuestion((current) => ({
                        ...current,
                        question_type: event.target.value,
                      }))
                    }
                  >
                    <option value="unknown">unknown</option>
                    <option value="single_choice">single_choice</option>
                    <option value="multiple_choice">multiple_choice</option>
                    <option value="fill_blank">fill_blank</option>
                    <option value="short_answer">short_answer</option>
                    <option value="proof">proof</option>
                    <option value="computation">computation</option>
                    <option value="open_ended">open_ended</option>
                  </select>
                </label>

                <label className="field-group">
                  <span className="field-label">答案</span>
                  <input
                    aria-label="答案"
                    className="field-input"
                    value={draftQuestion.answer_text || selectedQuestion?.answer_text || ""}
                    onChange={(event) =>
                      setDraftQuestion((current) => ({
                        ...current,
                        answer_text: event.target.value,
                      }))
                    }
                  />
                </label>
              </div>

              {draftQuestion.options.map((option, index) => (
                <div
                  key={option.option_label}
                  className={`option-row option-row-${option.option_label.toLowerCase()} ${
                    option.is_correct ? "option-row-correct" : ""
                  }`}
                >
                  <label className="field-group option-editor">
                    <span className="field-label">{`选项 ${option.option_label}`}</span>
                    <input
                      aria-label={`选项 ${option.option_label}`}
                      className="field-input"
                      value={option.option_text}
                      onChange={(event) =>
                        setDraftQuestion((current) => ({
                          ...current,
                          options: current.options.map((item, optionIndex) =>
                            optionIndex === index ? { ...item, option_text: event.target.value } : item,
                          ),
                        }))
                      }
                    />
                  </label>
                  <button
                    type="button"
                    className="secondary-btn option-mark-btn"
                    onClick={() => handleMarkCorrectAnswer(option.option_label)}
                  >
                    设为正确答案 {option.option_label}
                  </button>
                  {option.is_correct ? <span className="correct-badge">正确</span> : null}
                  <div className="option-preview">
                    <RichContentBlocks
                      blocks={getOptionBlocks(selectedQuestion, option.option_label)}
                      emptyLabel={`选项 ${option.option_label} 暂无可显示内容。`}
                    />
                  </div>
                </div>
              ))}

              <div className="editor-actions">
                <button
                  type="button"
                  className="secondary-btn compact-btn"
                  onClick={handleRestoreOriginal}
                  disabled={!questionIsModified || saving}
                >
                  恢复原文
                </button>
                <button type="button" className="primary-btn compact-btn" onClick={handleSaveQuestion} disabled={saving}>
                  {saving ? "保存中..." : "保存修改"}
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">没有可显示的题目。</div>
          )}
        </QuestionPanel>

        <QuestionPanel title="答案与解析">
          {selectedQuestion ? (
            <div className="analysis-preview">
              <p>答案：{draftQuestion.answer_text || selectedQuestion?.answer_text || "未解析"}</p>
              <div className="question-stem-preview" aria-label="解析预览">
                <RichContentBlocks blocks={analysisBlocks} emptyLabel="当前解析没有可显示的内容。" />
              </div>
            </div>
          ) : (
            <div className="empty-state">选中题目后可查看答案与解析。</div>
          )}

          {selectedQuestion ? (
            <label className="field-group">
              <label htmlFor="review-analysis" style={srOnlyStyle}>
                解析
              </label>
              <span className="field-label">解析</span>
              <textarea
                id="review-analysis"
                className="field-input field-textarea"
                rows={8}
                value={draftQuestion.analysis_text || selectedQuestion?.analysis_text || ""}
                onChange={(event) =>
                  setDraftQuestion((current) => ({
                    ...current,
                    analysis_text: event.target.value,
                  }))
                }
              />
            </label>
          ) : (
            <div className="empty-state">选择题目后可编辑解析文本。</div>
          )}
        </QuestionPanel>
      </section>

      <aside className="review-aside">
        <QuestionPanel title="元信息">
          {selectedPaper && selectedQuestion ? (
            <ul className="meta-list">
              <li>试卷：{selectedPaper.title}</li>
              <li>科目：{selectedPaper.subject}</li>
              <li>年份：{selectedPaper.exam_year}</li>
              <li>状态：{selectedQuestion.status}</li>
              <li>置信度：{selectedQuestion.confidence ?? "未设置"}</li>
              <li>题型：{selectedQuestion.question_type}</li>
              <li>
                <button type="button" className="primary-btn compact-btn" onClick={handleConfirmQuestion} disabled={saving}>
                  {saving ? "保存中..." : "确认题目"}
                </button>
              </li>
              <li>
                <button type="button" className="secondary-btn compact-btn" onClick={() => void handleDeletePaper()} disabled={saving}>
                  删除试卷
                </button>
              </li>
            </ul>
          ) : (
            <div className="empty-state">等待试卷载入。</div>
          )}
        </QuestionPanel>

        <QuestionPanel title="标签">
          {selectedQuestion ? (
            <TagEditor tags={questionTags} onAdd={handleAddTag} onRemove={handleRemoveTag} />
          ) : (
            <div className="empty-state">选择题目后可编辑标签。</div>
          )}
        </QuestionPanel>

        <QuestionPanel title="解析警告">
          {warnings.length === 0 ? (
            <div className="empty-state">当前试卷没有解析警告。</div>
          ) : (
            <div className="result-list">
              {warnings.map((warning) => (
                <div key={warning.id} className="result-item">
                  <strong>{warning.warning_code}</strong>
                  <div>{warning.warning_message}</div>
                  <div className="muted-line">{warning.warning_level}</div>
                </div>
              ))}
            </div>
          )}
        </QuestionPanel>

        <QuestionPanel title="审核日志">
          {recentLogs.length === 0 ? (
            <div className="empty-state">当前没有审核日志。</div>
          ) : (
            <div className="result-list">
              {recentLogs.map((log) => (
                <div key={log.id} className="result-item">
                  <strong>{log.action_type}</strong>
                  <div>{log.reviewer ?? "system"}</div>
                </div>
              ))}
            </div>
          )}
        </QuestionPanel>
      </aside>

      {loading ? <div className="status-card status-float">正在加载试卷...</div> : null}
      {error ? <div className="status-card status-float error-card">{error}</div> : null}
    </div>
  );
}

