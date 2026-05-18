import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  createPracticeSession,
  deletePaper,
  listPapers,
  recordPracticeAttempt,
  type PaperSummary,
  type PracticeQuestion,
  type PracticeSessionInfo,
} from "../lib/api";
import { QuestionPanel } from "../components/QuestionPanel";
import { RichContentBlocks } from "../components/RichContent";

const DEFAULT_COUNTS = {
  single_choice: 8,
  fill_blank: 8,
  short_answer: 11,
} as const;

type PracticeOption = NonNullable<PracticeQuestion["options"]>[number];

function questionStateLabel(question: PracticeQuestion | null) {
  if (!question) {
    return "未开始";
  }

  return [
    `题号 ${question.question_no}`,
    question.question_type,
    question.mastered ? "已掌握" : "未掌握",
    `错 ${question.wrong_count}`,
  ].join(" · ");
}

function normalizeAnswerText(value: string | null | undefined) {
  return (value ?? "").replace(/\s+/g, "").toUpperCase();
}

function isChoiceQuestion(
  question: PracticeQuestion | null,
): question is PracticeQuestion & { options: NonNullable<PracticeQuestion["options"]> } {
  return Boolean(question?.options?.length);
}

function getResultMessage(result: "correct" | "wrong" | "skip") {
  if (result === "skip") {
    return "已跳过，并标记为已掌握";
  }

  if (result === "correct") {
    return "答对，已自动更新掌握状态";
  }

  return "答错，已自动更新错题次数";
}

function isCorrectOption(question: PracticeQuestion, option: PracticeOption) {
  if (option.is_correct) {
    return true;
  }

  return normalizeAnswerText(option.option_label) === normalizeAnswerText(question.answer_text);
}

function formatPaperLabel(paper: PaperSummary) {
  const suffix = paper.paper_id.slice(0, 8);
  return `${paper.title} · ${paper.exam_year} · ${suffix}`;
}

export function PracticePage() {
  const [papers, setPapers] = useState<PaperSummary[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState("");
  const [singleChoiceCount, setSingleChoiceCount] = useState(DEFAULT_COUNTS.single_choice);
  const [fillBlankCount, setFillBlankCount] = useState(DEFAULT_COUNTS.fill_blank);
  const [shortAnswerCount, setShortAnswerCount] = useState(DEFAULT_COUNTS.short_answer);
  const [randomized, setRandomized] = useState(false);
  const [excludeMastered, setExcludeMastered] = useState(false);
  const [session, setSession] = useState<PracticeSessionInfo | null>(null);
  const [sessionQuestions, setSessionQuestions] = useState<PracticeQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [startingSession, setStartingSession] = useState(false);
  const [submittingAttempt, setSubmittingAttempt] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [recentAttemptNotice, setRecentAttemptNotice] = useState<string | null>(null);
  const [freeformAnswer, setFreeformAnswer] = useState("");
  const [selectedChoiceId, setSelectedChoiceId] = useState<string | null>(null);
  const [isQuestionListOpen, setIsQuestionListOpen] = useState(() => {
    if (typeof window === "undefined") {
      return true;
    }

    return !window.matchMedia("(min-width: 960px) and (max-width: 1366px)").matches;
  });

  const currentQuestion = useMemo(() => sessionQuestions[currentIndex] ?? null, [sessionQuestions, currentIndex]);
  const selectedPaper = papers.find((item) => item.paper_id === selectedPaperId) ?? null;
  const hasSession = sessionQuestions.length > 0;
  const isSessionComplete = hasSession && currentIndex >= sessionQuestions.length;
  const selectedChoice = useMemo(() => {
    if (!currentQuestion || !selectedChoiceId) {
      return null;
    }

    return currentQuestion.options?.find((option) => option.id === selectedChoiceId) ?? null;
  }, [currentQuestion, selectedChoiceId]);

  useEffect(() => {
    if (!recentAttemptNotice) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      setRecentAttemptNotice(null);
    }, 1600);

    return () => {
      window.clearTimeout(timer);
    };
  }, [recentAttemptNotice]);

  useEffect(() => {
    setFreeformAnswer("");
    setSelectedChoiceId(null);
  }, [currentQuestion?.question_id]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 960px) and (max-width: 1366px)");

    const syncPracticeAuxState = () => {
      setIsQuestionListOpen(!mediaQuery.matches);
    };

    syncPracticeAuxState();
    mediaQuery.addEventListener("change", syncPracticeAuxState);

    return () => {
      mediaQuery.removeEventListener("change", syncPracticeAuxState);
    };
  }, []);

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

  async function handleStartSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setStartingSession(true);
    setError(null);
    try {
      const response = await createPracticeSession({
        paper_id: selectedPaperId || undefined,
        randomized,
        exclude_mastered: excludeMastered,
        single_choice_count: singleChoiceCount,
        fill_blank_count: fillBlankCount,
        short_answer_count: shortAnswerCount,
      });

      setSession(response.session);
      setSessionQuestions(response.questions);
      setCurrentIndex(0);
      setRecentAttemptNotice(null);
      setNotice(`已生成 ${response.questions.length} 道题`);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "创建练习场景失败");
    } finally {
      setStartingSession(false);
    }
  }

  async function handleDeletePaper() {
    if (!selectedPaperId) {
      setError("请先选择要删除的试卷");
      return;
    }

    const confirmed = window.confirm(`确定删除试卷“${selectedPaper?.title ?? selectedPaperId}”吗？这会同时删除关联数据。`);
    if (!confirmed) {
      return;
    }

    setStartingSession(true);
    setError(null);
    try {
      await deletePaper(selectedPaperId);
      const paperList = await listPapers();
      setPapers(paperList);

      const nextSelectedPaperId = paperList.find((item) => item.paper_id !== selectedPaperId)?.paper_id ?? paperList[0]?.paper_id ?? "";

      setSelectedPaperId(nextSelectedPaperId);
      if (session?.paper_id === selectedPaperId || !nextSelectedPaperId) {
        setSession(null);
        setSessionQuestions([]);
        setCurrentIndex(0);
      }
      setNotice("试卷已删除");
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "删除试卷失败");
    } finally {
      setStartingSession(false);
    }
  }

  async function recordAndAdvance(result: "correct" | "wrong" | "skip", answerPayload: unknown) {
    if (!session || !currentQuestion) {
      return;
    }

    const questionId = currentQuestion.question_id;
    const questionNo = currentQuestion.question_no;

    setSubmittingAttempt(true);
    setError(null);

    try {
      const response = await recordPracticeAttempt({
        question_id: questionId,
        session_id: session.id,
        result,
        answer_payload: answerPayload,
      });

      setSessionQuestions((items) =>
        items.map((item) =>
          item.question_id === questionId
            ? {
                ...item,
                mastered: response.learning_state.mastered,
                wrong_count: response.learning_state.wrong_count,
                last_result: response.learning_state.last_result,
                last_attempt_at: response.learning_state.last_attempt_at,
              }
            : item,
        ),
      );
      setRecentAttemptNotice(`第 ${questionNo} 题：${getResultMessage(result)}`);
      setCurrentIndex((index) => index + 1);
    } catch (attemptError) {
      setError(attemptError instanceof Error ? attemptError.message : "记录作答失败");
    } finally {
      setSubmittingAttempt(false);
      setFreeformAnswer("");
    }
  }

  async function handleChoiceSelect(option: PracticeOption) {
    if (!currentQuestion || submittingAttempt) {
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
      setError("enter an answer or skip");
      return;
    }

    const result: "correct" | "wrong" =
      normalizedInput === normalizeAnswerText(currentQuestion.answer_text) ? "correct" : "wrong";

    await recordAndAdvance(result, {
      answer_text: freeformAnswer,
    });
  }

  async function handleSkip() {
    await recordAndAdvance("skip", null);
  }

  return (
    <div className={`review-grid practice-grid ${isQuestionListOpen ? "question-list-open" : "question-list-collapsed"}`}>
      <aside className="review-nav">
        <QuestionPanel title="练习模式">
          <form className="question-switcher" onSubmit={handleStartSession}>
            <label className="field-group">
              <span className="field-label">试卷</span>
              <select
                className="field-input"
                value={selectedPaperId}
                onChange={(event) => {
                  setSelectedPaperId(event.target.value);
                }}
              >
                <option value="">全部试卷</option>
                {papers.map((paper) => (
                  <option key={paper.paper_id} value={paper.paper_id}>
                    {formatPaperLabel(paper)}
                  </option>
                ))}
              </select>
            </label>

            <div className="practice-toggle-row">
              <button type="button" className="secondary-btn" onClick={() => void handleDeletePaper()} disabled={startingSession}>
                删除当前试卷
              </button>
            </div>

            <div className="question-meta-line">
              <span>{selectedPaper?.subject ?? "全部试卷"}</span>
              <span>{selectedPaper?.exam_year ?? ""}</span>
              <span>{selectedPaper ? `${selectedPaper.question_count} 题` : `${papers.length} 张试卷`}</span>
            </div>
            <div className="muted-line">
              {selectedPaper ? formatPaperLabel(selectedPaper) : "所有试卷"}
            </div>

            <label className="field-group">
              <span className="field-label">单选题数量</span>
              <input
                className="field-input"
                type="number"
                min={0}
                value={singleChoiceCount}
                onChange={(event) => setSingleChoiceCount(Number(event.target.value) || 0)}
              />
            </label>

            <label className="field-group">
              <span className="field-label">填空题数量</span>
              <input
                className="field-input"
                type="number"
                min={0}
                value={fillBlankCount}
                onChange={(event) => setFillBlankCount(Number(event.target.value) || 0)}
              />
            </label>

            <label className="field-group">
              <span className="field-label">解答题数量</span>
              <input
                className="field-input"
                type="number"
                min={0}
                value={shortAnswerCount}
                onChange={(event) => setShortAnswerCount(Number(event.target.value) || 0)}
              />
            </label>

            <label className="field-group">
              <span className="field-label">模式</span>
              <div className="practice-toggle-row">
                <label className="practice-toggle">
                  <input
                    type="checkbox"
                    checked={randomized}
                    onChange={(event) => setRandomized(event.target.checked)}
                  />
                  随机
                </label>
                <label className="practice-toggle">
                  <input
                    type="checkbox"
                    checked={excludeMastered}
                    onChange={(event) => setExcludeMastered(event.target.checked)}
                  />
                  已掌握的不出
                </label>
              </div>
            </label>

            <button type="submit" className="primary-btn" disabled={startingSession || loadingPapers}>
              {startingSession ? "创建中..." : "开始练习"}
            </button>
          </form>
        </QuestionPanel>

        {isQuestionListOpen ? (
          <QuestionPanel title="当前进度">
            {!session ? (
              <div className="empty-state">先创建一个练习场景。</div>
            ) : (
              <div className="result-list">
                <div className="result-item">
                  <strong>{session.status}</strong>
                  <div>题目数量：{sessionQuestions.length}</div>
                  <div>已显示：{isSessionComplete ? sessionQuestions.length : Math.min(currentIndex + 1, sessionQuestions.length)}</div>
                </div>
                <div className="result-item">
                  <div>单选题：{session.selected_counts.single_choice ?? 0}</div>
                  <div>填空题：{session.selected_counts.fill_blank ?? 0}</div>
                  <div>解答题：{session.selected_counts.short_answer ?? 0}</div>
                </div>
                <div className="result-item">
                  <div>可用单选题：{session.available_counts.single_choice ?? 0}</div>
                  <div>可用填空题：{session.available_counts.fill_blank ?? 0}</div>
                  <div>可用解答题：{session.available_counts.short_answer ?? 0}</div>
                </div>
              </div>
            )}
          </QuestionPanel>
        ) : null}

        {isQuestionListOpen && loadingPapers ? (
          <QuestionPanel title="提示">
            <div className="empty-state">试卷加载中...</div>
          </QuestionPanel>
        ) : null}
      </aside>

      <section className="review-main">
        <div className="practice-main-toolbar">
          <div className="practice-main-toolbar-spacer" />
          <button
            type="button"
            className="secondary-btn practice-sidebar-toggle"
            onClick={() => setIsQuestionListOpen((value) => !value)}
            aria-controls="practice-question-list"
            aria-expanded={isQuestionListOpen}
          >
            {isQuestionListOpen ? "收起辅助信息" : "展开辅助信息"}
          </button>
        </div>

        <QuestionPanel title="练习题目">
          {!session ? (
            <div className="empty-state">选择试卷后开始练习，这里会显示题目。</div>
          ) : isSessionComplete ? (
            <div className="result-list">
              <div className="result-item">
                <strong>练习完成</strong>
                <div>本次练习共 {sessionQuestions.length} 题，可重新开始继续练习。</div>
              </div>
            </div>
          ) : currentQuestion ? (
            <div className="practice-question-card">
              <div className="question-meta-line">
                <span>{questionStateLabel(currentQuestion)}</span>
                <span>
                  {Math.min(currentIndex + 1, sessionQuestions.length)} / {sessionQuestions.length}
                </span>
              </div>

              <div className="question-stem-preview">
                <RichContentBlocks
                  blocks={currentQuestion.stem_blocks ?? []}
                  emptyLabel={currentQuestion.stem_text || "暂无题干文本"}
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
                      disabled={submittingAttempt}
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
                    <button
                      type="button"
                      className="secondary-btn"
                      onClick={() => setSelectedChoiceId(null)}
                      disabled={submittingAttempt || !selectedChoice}
                    >
                      取消选择
                    </button>
                    <button
                      type="button"
                      className="primary-btn"
                      onClick={() => void handleChoiceConfirm()}
                      disabled={submittingAttempt || !selectedChoice}
                    >
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
                    <button type="button" className="secondary-btn" onClick={() => void handleSkip()} disabled={submittingAttempt}>
                      跳过
                    </button>
                    <button type="button" className="primary-btn" onClick={() => void handleFreeformSubmit()} disabled={submittingAttempt}>
                      提交答案
                    </button>
                  </div>
                </div>
              )}

              <div className="practice-answer-hint">答案默认隐藏，提交后系统会自动判断并更新掌握状态与错题次数。</div>

              <div className="practice-action-row">
                <button type="button" className="secondary-btn" onClick={() => void handleSkip()} disabled={submittingAttempt}>
                  跳过
                </button>
              </div>
            </div>
          ) : (
            <div className="empty-state">暂无可练习的题目。</div>
          )}
        </QuestionPanel>
      </section>

      <aside className="review-aside" id="practice-question-list">
        <div className="practice-aside-block practice-question-list-block">
          <QuestionPanel title="题目列表">
            {sessionQuestions.length === 0 ? (
              <div className="empty-state">先创建一个练习场景。</div>
            ) : (
              <div className="question-switcher">
                {sessionQuestions.map((question, index) => (
                  <button
                    key={question.question_id}
                    type="button"
                    className={`nav-question ${index === currentIndex ? "active" : ""}`}
                    onClick={() => setCurrentIndex(index)}
                  >
                    {question.question_no}. {question.question_type}
                  </button>
                ))}
              </div>
            )}
          </QuestionPanel>
        </div>

        {isQuestionListOpen ? (
          <div className="practice-aside-block practice-hint-block">
            <QuestionPanel title="提示">
              <div className="result-item">
                <div>单选题使用选项按钮，提交后自动判定。</div>
                <div>答案默认隐藏，提交后再显示结果。</div>
                <div>错题回顾已放到单独页面。</div>
              </div>
            </QuestionPanel>
          </div>
        ) : null}
      </aside>

      {notice ? <div className="status-card status-float">{notice}</div> : null}
      {recentAttemptNotice ? (
        <div className="status-card status-float practice-toast">
          <strong>本题结果</strong>
          <div>{recentAttemptNotice}</div>
        </div>
      ) : null}
      {error ? <div className="status-card status-float error-card">{error}</div> : null}
    </div>
  );
}




