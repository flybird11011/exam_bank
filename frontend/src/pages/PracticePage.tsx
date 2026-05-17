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
    return "skipped and marked mastered";
  }

  return [
    `棰樺彿 ${question.question_no}`,
    question.question_type,
    question.mastered ? "mastered" : "unmastered",
    `閿?${question.wrong_count}`,
  ].join(" 路 ");
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
    return "skipped and marked mastered";
  }

  if (result === "correct") {
    return "skipped and marked mastered";
  }
    return "skipped and marked mastered";
}

function isCorrectOption(question: PracticeQuestion, option: PracticeOption) {
  if (option.is_correct) {
    return true;
  }

  return normalizeAnswerText(option.option_label) === normalizeAnswerText(question.answer_text);
}

function formatPaperLabel(paper: PaperSummary) {
  const suffix = paper.paper_id.slice(0, 8);
  return `${paper.title} 路 ${paper.exam_year} 路 ${suffix}`;
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
          setError(loadError instanceof Error ? loadError.message : "鍔犺浇璇曞嵎澶辫触");
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
      setNotice(`generated ${response.questions.length} questions`);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "create practice session failed");
    } finally {
      setStartingSession(false);
    }
  }

  async function handleDeletePaper() {
    if (!selectedPaperId) {
      setError("请先选择要删除的试卷");
      return;
    }

    const confirmed = window.confirm(
      `Delete paper "${selectedPaper?.title ?? selectedPaperId}"? This will remove the paper and related data.`,
    );
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
      setError(deleteError instanceof Error ? deleteError.message : "delete paper failed");
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
      setRecentAttemptNotice(`绗?${questionNo} 棰橈細${getResultMessage(result)}`);
      setCurrentIndex((index) => index + 1);
    } catch (attemptError) {
      setError(attemptError instanceof Error ? attemptError.message : "record attempt failed");
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
    <div className="review-grid">
      <aside className="review-nav">
        <QuestionPanel title="缁冧範妯″紡">
          <form className="question-switcher" onSubmit={handleStartSession}>
            <label className="field-group">
              <span className="field-label">璇曞嵎</span>
              <select
                className="field-input"
                value={selectedPaperId}
                onChange={(event) => {
                  setSelectedPaperId(event.target.value);
                }}
              >
                <option value="">鍏ㄩ儴璇曞嵎</option>
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
              <span>{selectedPaper?.subject ?? "all papers"}</span>
              <span>{selectedPaper?.exam_year ?? ""}</span>
              <span>{selectedPaper ? `${selectedPaper.question_count} questions` : `${papers.length} papers`}</span>
            </div>
            <div className="muted-line">
              {selectedPaper ? formatPaperLabel(selectedPaper) : "All papers"}
            </div>

            <label className="field-group">
              <span className="field-label">single choice count</span>
              <input
                className="field-input"
                type="number"
                min={0}
                value={singleChoiceCount}
                onChange={(event) => setSingleChoiceCount(Number(event.target.value) || 0)}
              />
            </label>

            <label className="field-group">
              <span className="field-label">濉┖鏁伴噺</span>
              <input
                className="field-input"
                type="number"
                min={0}
                value={fillBlankCount}
                onChange={(event) => setFillBlankCount(Number(event.target.value) || 0)}
              />
            </label>

            <label className="field-group">
              <span className="field-label">short answer count</span>
              <input
                className="field-input"
                type="number"
                min={0}
                value={shortAnswerCount}
                onChange={(event) => setShortAnswerCount(Number(event.target.value) || 0)}
              />
            </label>

            <label className="field-group">
              <span className="field-label">妯″紡</span>
              <div className="practice-toggle-row">
                <label className="practice-toggle">
                  <input
                    type="checkbox"
                    checked={randomized}
                    onChange={(event) => setRandomized(event.target.checked)}
                  />
                  闅忔満
                </label>
                <label className="practice-toggle">
                  <input
                    type="checkbox"
                    checked={excludeMastered}
                    onChange={(event) => setExcludeMastered(event.target.checked)}
                  />
                  宸叉帉鎻＄殑涓嶅嚭
                </label>
              </div>
            </label>

            <button type="submit" className="primary-btn" disabled={startingSession || loadingPapers}>
              {startingSession ? "creating..." : "Start Practice"}
            </button>
          </form>
        </QuestionPanel>

        <QuestionPanel title="褰撳墠杩涘害">
          {!session ? (
            <div className="empty-state">Create a practice session first.</div>
          ) : (
            <div className="result-list">
              <div className="result-item">
                <strong>{session.status}</strong>
                <div>棰樼洰鏁帮細{sessionQuestions.length}</div>
                <div>shown: {isSessionComplete ? sessionQuestions.length : Math.min(currentIndex + 1, sessionQuestions.length)}</div>
              </div>
              <div className="result-item">
                <div>single choice: {session.selected_counts.single_choice ?? 0}</div>
                <div>fill blank: {session.selected_counts.fill_blank ?? 0}</div>
                <div>short answer: {session.selected_counts.short_answer ?? 0}</div>
              </div>
              <div className="result-item">
                <div>available single choice: {session.available_counts.single_choice ?? 0}</div>
                <div>available fill blank: {session.available_counts.fill_blank ?? 0}</div>
                <div>available short answer: {session.available_counts.short_answer ?? 0}</div>
              </div>
            </div>
          )}
        </QuestionPanel>

        {loadingPapers ? (
          <QuestionPanel title="鎻愮ず">
            <div className="empty-state">璇曞嵎鍔犺浇涓?..</div>
          </QuestionPanel>
        ) : null}
      </aside>

      <section className="review-main">
        <QuestionPanel title="缁冧範棰樼洰">
          {!session ? (
            <div className="empty-state">Select a paper and start practice to see questions here.</div>
          ) : isSessionComplete ? (
            <div className="result-list">
              <div className="result-item">
                <strong>缁冧範瀹屾垚</strong>
                <div>This session has {sessionQuestions.length} questions. Generate another session to continue.</div>
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
                  emptyLabel={currentQuestion.stem_text || "鏆傛棤棰樺共鏂囨湰"}
                />
              </div>

              {isChoiceQuestion(currentQuestion) ? (
                <div className="option-list">
                  <div className="choice-selection-hint">
                    {selectedChoice ? `Selected: ${selectedChoice.option_label}` : "Choose an option, then confirm."}
                  </div>
                  {currentQuestion.options.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      className={`result-item practice-option-button ${selectedChoiceId === option.id ? "selected" : ""}`}
                      onClick={() => void handleChoiceSelect(option)}
                      disabled={submittingAttempt}
                      aria-label={`閫夐」 ${option.option_label}`}
                      aria-pressed={selectedChoiceId === option.id}
                    >
                      <strong>{option.option_label}</strong>
                      <RichContentBlocks
                        blocks={option.option_blocks ?? []}
                        emptyLabel={option.option_text || "鏆傛棤閫夐」鍐呭"}
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
                      鍙栨秷閫夋嫨
                    </button>
                    <button
                      type="button"
                      className="primary-btn"
                      onClick={() => void handleChoiceConfirm()}
                      disabled={submittingAttempt || !selectedChoice}
                    >
                      纭绛旀
                    </button>
                  </div>
                </div>
              ) : (
                <div className="question-edit-grid">
                  <label className="field-group">
                    <span className="field-label">answer input</span>
                    <textarea
                      className="field-input field-textarea"
                      rows={4}
                      value={freeformAnswer}
                      onChange={(event) => setFreeformAnswer(event.target.value)}
                      placeholder="Answers are hidden by default and compared after submit."
                    />
                  </label>
                  <div className="practice-action-row">
                    <button type="button" className="secondary-btn" onClick={() => void handleSkip()} disabled={submittingAttempt}>
                      璺宠繃
                    </button>
                    <button type="button" className="primary-btn" onClick={() => void handleFreeformSubmit()} disabled={submittingAttempt}>
                      鎻愪氦绛旀
                    </button>
                  </div>
                </div>
              )}

              <div className="practice-answer-hint">Answers stay hidden until you submit, and mastery / wrong count update automatically.</div>

              <div className="practice-action-row">
                <button type="button" className="secondary-btn" onClick={() => void handleSkip()} disabled={submittingAttempt}>
                  璺宠繃
                </button>
              </div>
            </div>
          ) : (
            <div className="empty-state">No practice questions available.</div>
          )}
        </QuestionPanel>
      </section>

      <aside className="review-aside">
        <QuestionPanel title="棰樼洰鍒楄〃">
          {sessionQuestions.length === 0 ? (
            <div className="empty-state">Create a practice session first.</div>
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

        <QuestionPanel title="鎻愮ず">
          <div className="result-item">
            <div>Single-choice questions use direct option buttons and auto-judge after submit.</div>
            <div>Answers stay hidden by default and update after submission.</div>
            <div>Wrong-question review has moved to its own page.</div>
          </div>
        </QuestionPanel>
      </aside>

      {notice ? <div className="status-card status-float">{notice}</div> : null}
      {recentAttemptNotice ? (
        <div className="status-card status-float practice-toast">
          <strong>鏈缁撴灉</strong>
          <div>{recentAttemptNotice}</div>
        </div>
      ) : null}
      {error ? <div className="status-card status-float error-card">{error}</div> : null}
    </div>
  );
}




