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

function questionStateLabel(question: PracticeQuestion | null) {
  if (!question) {
    return "";
  }

  return [`题号 ${question.question_no}`, question.question_type, question.mastered ? "已掌握" : "未掌握", `错 ${question.wrong_count}`].join(" · ");
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

  const selectedPaper = useMemo(
    () => papers.find((paper) => paper.paper_id === selectedPaperId) ?? null,
    [papers, selectedPaperId],
  );

  const selectedQuestion = useMemo(
    () => queryItems.find((item) => item.question_id === selectedQuestionId) ?? null,
    [queryItems, selectedQuestionId],
  );

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
        setSelectedQuestionId(first.question_id);
        setSelectedIndex(0);
        setSelectedDetail(null);
        setShowAnswer(false);
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

  async function handleAttempt(result: "correct" | "wrong" | "skip") {
    if (!selectedQuestionId) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await recordPracticeAttempt({
        question_id: selectedQuestionId,
        result,
        answer_payload: null,
      });
      setNotice(result === "skip" ? "已跳过并记为已掌握" : result === "correct" ? "已记录答对" : "已记录答错");
      await refreshQuestions();
      const currentIndex = queryItems.findIndex((item) => item.question_id === selectedQuestionId);
      if (currentIndex >= 0) {
        await openDetail(selectedQuestionId, currentIndex);
      }
    } catch (attemptError) {
      setError(attemptError instanceof Error ? attemptError.message : "记录练习失败");
    } finally {
      setSaving(false);
    }
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
    <div className="review-grid">
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

              {selectedDetail.question.options?.length ? (
                <div className="option-list">
                  {selectedDetail.question.options.map((option) => (
                    <div key={option.id} className="result-item">
                      <strong>{option.option_label}</strong>
                      <RichContentBlocks
                        blocks={option.option_blocks ?? []}
                        emptyLabel={option.option_text || "暂无选项内容"}
                      />
                    </div>
                  ))}
                </div>
              ) : null}

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
                <button type="button" className="secondary-btn" onClick={() => void handleAttempt("wrong")} disabled={saving}>
                  答错
                </button>
                <button type="button" className="secondary-btn" onClick={() => void handleAttempt("skip")} disabled={saving}>
                  跳过
                </button>
                <button type="button" className="primary-btn" onClick={() => void handleAttempt("correct")} disabled={saving}>
                  答对
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

      <aside className="review-aside">
        <QuestionPanel title="提示">
          <div className="result-item">
            <div>答案和解析默认隐藏。</div>
            <div>“跳过”会按已掌握处理。</div>
            <div>可以用“下一题”连续回顾。</div>
          </div>
        </QuestionPanel>
      </aside>

      {notice ? <div className="status-card status-float">{notice}</div> : null}
      {error ? <div className="status-card status-float error-card">{error}</div> : null}
    </div>
  );
}
