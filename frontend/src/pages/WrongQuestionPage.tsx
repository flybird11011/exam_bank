import { useEffect, useMemo, useState } from "react";

import {
  getPracticeQuestion,
  listPapers,
  listPracticeQuestions,
  recordPracticeAttempt,
  type PaperSummary,
  type PracticeQuestion,
  type PracticeQuestionDetail,
} from "../lib/api";
import { QuestionPanel } from "../components/QuestionPanel";
import { RichContentBlocks } from "../components/RichContent";

type QueryFilters = {
  mastered: string;
  minWrongCount: string;
  paperId: string;
  questionType: string;
};

const INITIAL_QUERY_FILTERS: QueryFilters = {
  mastered: "",
  minWrongCount: "1",
  paperId: "",
  questionType: "",
};

type PracticeOption = NonNullable<PracticeQuestionDetail["question"]["options"]>[number];

function questionStateLabel(question: PracticeQuestion | null) {
  if (!question) {
    return "";
  }

  return [`题号 ${question.question_no}`, question.question_type, question.mastered ? "已掌握" : "未掌握", `错 ${question.wrong_count}`].join(" · ");
}

function normalizeAnswerText(value: string | null | undefined) {
  return (value ?? "").replace(/\s+/g, "").toUpperCase();
}

function isChoiceQuestion(
  question: PracticeQuestionDetail["question"] | null,
): question is PracticeQuestionDetail["question"] & { options: NonNullable<PracticeQuestionDetail["question"]["options"]> } {
  return Boolean(question?.options?.length);
}

function isCorrectOption(question: PracticeQuestionDetail["question"], option: PracticeOption) {
  if (option.is_correct) {
    return true;
  }

  return normalizeAnswerText(option.option_label) === normalizeAnswerText(question.answer_text);
}

export function WrongQuestionPage() {
  const [papers, setPapers] = useState<PaperSummary[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState("");
  const [queryFilters, setQueryFilters] = useState<QueryFilters>(INITIAL_QUERY_FILTERS);
  const [queryItems, setQueryItems] = useState<PracticeQuestion[]>([]);
  const [queryTotal, setQueryTotal] = useState(0);
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<PracticeQuestionDetail | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [queryLoading, setQueryLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [freeformAnswer, setFreeformAnswer] = useState("");
  const [selectedChoiceId, setSelectedChoiceId] = useState<string | null>(null);

  const selectedPaper = useMemo(
    () => papers.find((paper) => paper.paper_id === selectedPaperId) ?? null,
    [papers, selectedPaperId],
  );

  const selectedQuestion = useMemo(
    () => queryItems.find((item) => item.question_id === selectedQuestionId) ?? null,
    [queryItems, selectedQuestionId],
  );

  const currentQuestion = selectedDetail?.question ?? null;
  const selectedChoice = useMemo(() => {
    if (!currentQuestion || !selectedChoiceId) {
      return null;
    }

    return currentQuestion.options?.find((option) => option.id === selectedChoiceId) ?? null;
  }, [currentQuestion, selectedChoiceId]);

  useEffect(() => {
    setFreeformAnswer("");
    setSelectedChoiceId(null);
  }, [currentQuestion?.question_id]);

  useEffect(() => {
    let mounted = true;

    async function loadPapers() {
      try {
        setLoadingPapers(true);
        const paperList = await listPapers();
        if (!mounted) {
          return;
        }

        setPapers(paperList);
        if (paperList[0]) {
          setSelectedPaperId(paperList[0].paper_id);
          setQueryFilters((current) => ({
            ...current,
            paperId: current.paperId || paperList[0].paper_id,
          }));
        }
      } catch (loadError) {
        if (mounted) {
          setError(loadError instanceof Error ? loadError.message : "加载试卷失败");
        }
      } finally {
        if (mounted) {
          setLoadingPapers(false);
        }
      }
    }

    loadPapers();

    return () => {
      mounted = false;
    };
  }, []);

  async function refreshQuestions() {
    setQueryLoading(true);
    setError(null);
    try {
      const response = await listPracticeQuestions({
        mastered: queryFilters.mastered === "" ? undefined : queryFilters.mastered === "true",
        min_wrong_count: queryFilters.minWrongCount === "" ? undefined : Number(queryFilters.minWrongCount),
        paper_id: queryFilters.paperId || selectedPaperId || undefined,
        question_type: queryFilters.questionType || undefined,
      });
      setQueryItems(response.items);
      setQueryTotal(response.total);
      setNotice(`已刷新 ${response.total} 道错题`);

      if (response.items.length > 0) {
        const first = response.items[0];
        await openDetail(first.question_id, 0);
      } else {
        setSelectedQuestionId(null);
        setSelectedDetail(null);
        setShowAnswer(false);
      }
    } catch (queryError) {
      setError(queryError instanceof Error ? queryError.message : "获取错题失败");
    } finally {
      setQueryLoading(false);
    }
  }

  async function openDetail(questionId: string, index: number) {
    setDetailLoading(true);
    setError(null);
    try {
      const detail = await getPracticeQuestion(questionId);
      setSelectedQuestionId(questionId);
      setSelectedIndex(index);
      setSelectedDetail(detail);
      setShowAnswer(false);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : "获取题目详情失败");
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleMarkMastered() {
    if (!selectedQuestionId) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await recordPracticeAttempt({
        question_id: selectedQuestionId,
        result: "skip",
        answer_payload: null,
      });
      setNotice("已标记为已掌握");
      await refreshQuestions();
      const currentIndex = queryItems.findIndex((item) => item.question_id === selectedQuestionId);
      if (currentIndex >= 0) {
        await openDetail(selectedQuestionId, currentIndex);
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "标记已掌握失败");
    } finally {
      setSaving(false);
    }
  }

  async function recordAndAdvance(result: "correct" | "wrong", answerPayload: unknown) {
    if (!selectedQuestionId) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await recordPracticeAttempt({
        question_id: selectedQuestionId,
        result,
        answer_payload: answerPayload,
      });
      setNotice(result === "correct" ? "已记录答对" : "已记录答错");
      await refreshQuestions();
      const currentIndex = queryItems.findIndex((item) => item.question_id === selectedQuestionId);
      if (currentIndex >= 0) {
        await openDetail(selectedQuestionId, currentIndex);
      }
    } catch (attemptError) {
      setError(attemptError instanceof Error ? attemptError.message : "记录练习失败");
    } finally {
      setSaving(false);
      setFreeformAnswer("");
      setSelectedChoiceId(null);
    }
  }

  function handleChoiceSelect(option: PracticeOption) {
    if (!currentQuestion || saving) {
      return;
    }

    setSelectedChoiceId(option.id);
  }

  async function handleChoiceConfirm() {
    if (!currentQuestion || !selectedChoice) {
      return;
    }

    const result: "correct" | "wrong" = isCorrectOption(currentQuestion, selectedChoice) ? "correct" : "wrong";

    await recordAndAdvance(result, {
      selected_option_id: selectedChoice.id,
      selected_option_label: selectedChoice.option_label,
      selected_option_text: selectedChoice.option_text ?? "",
    });
  }

  async function handleFreeformSubmit() {
    if (!currentQuestion) {
      return;
    }

    const normalizedInput = normalizeAnswerText(freeformAnswer);
    if (!normalizedInput) {
      setError("请输入答案后再确认");
      return;
    }

    const result: "correct" | "wrong" =
      normalizedInput === normalizeAnswerText(currentQuestion.answer_text) ? "correct" : "wrong";

    await recordAndAdvance(result, {
      answer_text: freeformAnswer,
    });
  }

  async function handleNextQuestion() {
    if (queryItems.length === 0) {
      return;
    }

    const nextIndex = selectedIndex + 1;
    const nextQuestion = queryItems[nextIndex];
    if (!nextQuestion) {
      setNotice("已经是最后一题");
      return;
    }

    await openDetail(nextQuestion.question_id, nextIndex);
  }

  async function handlePreviousQuestion() {
    if (queryItems.length === 0) {
      return;
    }

    const prevIndex = selectedIndex - 1;
    const prevQuestion = queryItems[prevIndex];
    if (!prevQuestion) {
      setNotice("已经是第一题");
      return;
    }

    await openDetail(prevQuestion.question_id, prevIndex);
  }

  useEffect(() => {
    if (papers.length > 0 && queryItems.length === 0 && !queryLoading) {
      void refreshQuestions();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [papers.length, selectedPaperId]);

  return (
    <div className={`review-grid tablet-grid review-tablet-grid ${isSidebarOpen ? "sidebar-open" : "sidebar-collapsed"}`}>
      <aside className="review-nav">
        <QuestionPanel title="错题回顾">
          <div className="question-switcher">
            <label className="field-group">
              <span className="field-label">试卷</span>
              <select
                className="field-input"
                value={selectedPaperId}
                onChange={(event) => {
                  setSelectedPaperId(event.target.value);
                  setQueryFilters((current) => ({
                    ...current,
                    paperId: event.target.value,
                  }));
                }}
              >
                {papers.map((paper) => (
                  <option key={paper.paper_id} value={paper.paper_id}>
                    {paper.title}
                  </option>
                ))}
              </select>
            </label>

            <div className="question-meta-line">
              <span>{selectedPaper?.subject ?? "待加载"}</span>
              <span>{selectedPaper?.exam_year ?? ""}</span>
              <span>{selectedPaper?.question_count ?? 0} 题</span>
            </div>

            <label className="field-group">
              <span className="field-label">掌握状态</span>
              <select
                className="field-input"
                value={queryFilters.mastered}
                onChange={(event) => setQueryFilters((current) => ({ ...current, mastered: event.target.value }))}
              >
                <option value="">全部</option>
                <option value="false">未掌握</option>
                <option value="true">已掌握</option>
              </select>
            </label>

            <label className="field-group">
              <span className="field-label">最少错题次数</span>
              <input
                className="field-input"
                type="number"
                min={0}
                value={queryFilters.minWrongCount}
                onChange={(event) => setQueryFilters((current) => ({ ...current, minWrongCount: event.target.value }))}
              />
            </label>

            <label className="field-group">
              <span className="field-label">题型</span>
              <select
                className="field-input"
                value={queryFilters.questionType}
                onChange={(event) => setQueryFilters((current) => ({ ...current, questionType: event.target.value }))}
              >
                <option value="">全部</option>
                <option value="single_choice">single_choice</option>
                <option value="fill_blank">fill_blank</option>
                <option value="short_answer">short_answer</option>
              </select>
            </label>

            <button type="button" className="secondary-btn" onClick={refreshQuestions} disabled={queryLoading || loadingPapers}>
              {queryLoading ? "刷新中..." : "刷新错题"}
            </button>
          </div>
        </QuestionPanel>

        <QuestionPanel title="错题列表">
          <div className="muted-line">共 {queryTotal} 题</div>
          <div className="result-list">
            {queryItems.length === 0 ? (
              <div className="empty-state">点击“刷新错题”后显示列表。</div>
            ) : (
              queryItems.map((item, index) => (
                <button
                  key={item.question_id}
                  type="button"
                  className={`result-item practice-query-item ${item.question_id === selectedQuestionId ? "option-row-correct" : ""}`}
                  onClick={() => void openDetail(item.question_id, index)}
                >
                  <strong>
                    {item.question_no}. {item.question_type}
                  </strong>
                  <div>{item.stem_text || "暂无题干"}</div>
                  <div className="muted-line">
                    错 {item.wrong_count} · {item.mastered ? "已掌握" : "未掌握"}
                  </div>
                </button>
              ))
            )}
          </div>
        </QuestionPanel>
      </aside>

      <section className="review-main">
        <div className="practice-main-toolbar">
          <div className="practice-main-toolbar-spacer" />
          <button
            type="button"
            className="secondary-btn practice-sidebar-toggle"
            onClick={() => setIsSidebarOpen((value) => !value)}
            aria-controls="wrong-question-sidebar"
            aria-expanded={isSidebarOpen}
          >
            {isSidebarOpen ? "收起侧栏" : "展开侧栏"}
          </button>
        </div>

        <QuestionPanel title="错题详情">
          {detailLoading ? (
            <div className="empty-state">正在加载详情...</div>
          ) : selectedDetail ? (
            <div className="practice-question-card">
              <div className="question-meta-line">
                <span>{questionStateLabel(selectedQuestion)}</span>
                <span>
                  {selectedIndex + 1} / {Math.max(queryItems.length, 1)}
                </span>
              </div>

              <div className="question-stem-preview">
                <RichContentBlocks
                  blocks={selectedDetail.question.stem_blocks ?? []}
                  emptyLabel={selectedDetail.question.stem_text || "暂无题干"}
                />
              </div>

              {isChoiceQuestion(currentQuestion) ? (
                <div className="option-list">
                  <div className="choice-selection-hint">
                    {selectedChoice ? `已选择：${selectedChoice.option_label}` : "请选择一个选项后再确认。"}
                  </div>
                  {currentQuestion.options.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      className={`result-item practice-option-button ${selectedChoiceId === option.id ? "selected" : ""}`}
                      onClick={() => void handleChoiceSelect(option)}
                      disabled={saving}
                      aria-label={`选项 ${option.option_label}`}
                      aria-pressed={selectedChoiceId === option.id}
                    >
                      <strong>{option.option_label}</strong>
                      <RichContentBlocks
                        blocks={option.option_blocks ?? []}
                        emptyLabel={option.option_text || "暂无选项内容"}
                      />
                    </button>
                  ))}
                  <div className="practice-action-row">
                    <button type="button" className="secondary-btn" onClick={() => setSelectedChoiceId(null)} disabled={saving || !selectedChoice}>
                      取消选择
                    </button>
                    <button type="button" className="primary-btn" onClick={() => void handleChoiceConfirm()} disabled={saving || !selectedChoice}>
                      确认答案
                    </button>
                  </div>
                </div>
              ) : (
                <div className="question-edit-grid">
                  <label className="field-group">
                    <span className="field-label">答案输入</span>
                    <textarea
                      className="field-input field-textarea"
                      rows={4}
                      value={freeformAnswer}
                      onChange={(event) => setFreeformAnswer(event.target.value)}
                      placeholder="答案默认隐藏，提交后会自动比对。"
                    />
                  </label>
                  <div className="practice-action-row">
                    <button type="button" className="primary-btn" onClick={() => void handleFreeformSubmit()} disabled={saving}>
                      确认答案
                    </button>
                  </div>
                </div>
              )}

              <div className="practice-action-row">
                <button type="button" className="secondary-btn" onClick={() => void handlePreviousQuestion()} disabled={saving}>
                  上一题
                </button>
                <button type="button" className="secondary-btn" onClick={() => setShowAnswer((current) => !current)}>
                  {showAnswer ? "隐藏答案" : "显示答案"}
                </button>
                <button type="button" className="secondary-btn" onClick={() => void handleNextQuestion()} disabled={saving}>
                  下一题
                </button>
                <button type="button" className="secondary-btn" onClick={() => void handleMarkMastered()} disabled={saving}>
                  标记已掌握
                </button>
              </div>

              {showAnswer ? (
                <div className="result-list">
                  <div className="result-item">
                    <div>答案：{selectedDetail.question.answer_text || "无"}</div>
                  </div>
                  <div className="result-item">
                    <strong>解析</strong>
                    <RichContentBlocks
                      blocks={selectedDetail.question.analysis_blocks ?? []}
                      emptyLabel={selectedDetail.question.analysis_text || "暂无解析"}
                    />
                  </div>
                </div>
              ) : null}

              <div className="result-item">
                <strong>学习状态</strong>
                <div>掌握：{selectedDetail.learning_state.mastered ? "已掌握" : "未掌握"}</div>
                <div>错题次数：{selectedDetail.learning_state.wrong_count}</div>
                <div>最近结果：{selectedDetail.learning_state.last_result || "无"}</div>
              </div>

              <div className="result-item">
                <strong>最近 {selectedDetail.recent_attempts.length} 次作答</strong>
                {selectedDetail.recent_attempts.map((attempt) => (
                  <div key={attempt.id} className="muted-line">
                    {attempt.result} · {attempt.created_at ?? "unknown"}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-state">点击左侧错题后查看详情。</div>
          )}
        </QuestionPanel>
      </section>

      <aside className="review-aside" id="wrong-question-sidebar">
        <QuestionPanel title="提示">
          <div className="result-item">
            <div>选择题可直接点选选项后确认。</div>
            <div>填空和简答题用文本输入框作答。</div>
            <div>“标记已掌握”会直接更新学习状态。</div>
          </div>
        </QuestionPanel>
      </aside>

      {notice ? <div className="status-card status-float">{notice}</div> : null}
      {error ? <div className="status-card status-float error-card">{error}</div> : null}
    </div>
  );
}
