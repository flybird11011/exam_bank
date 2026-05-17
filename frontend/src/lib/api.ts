export type ImportPaperResponse = {
  parse_run_id: string;
  status: string;
  paper: {
    paper_id: string;
    title: string;
    subject: string;
    exam_year: number;
    section_count: number;
    question_count: number;
  };
};

export type DuplicatePolicy = "replace" | "keep_both";

type ApiErrorPayload = {
  code?: string;
  error_code?: string;
  detail?: unknown;
  message?: string;
  duplicate_found?: boolean;
};

export class ImportDuplicateError extends Error {
  code = "DUPLICATE_PAPER";

  constructor(message = "妫€娴嬪埌閲嶅璇曞嵎") {
    super(message);
    this.name = "ImportDuplicateError";
  }
}

export type StemBlock = {
  kind: string;
  text?: string | null;
  rows?: string[][];
  url?: string | null;
  asset_ref?: string | null;
  media_asset_id?: string | null;
  file_name?: string | null;
  original_file_name?: string | null;
  source?: string | null;
};

export type PaperSummary = {
  paper_id: string;
  parse_run_id: string | null;
  title: string;
  subject: string;
  region: string | null;
  exam_year: number;
  exam_type: string | null;
  section_count: number;
  question_count: number;
  status: string;
};

export type PaperQuestion = {
  id: string;
  question_no: string;
  question_type: string;
  stem_text: string | null;
  stem_blocks?: StemBlock[];
  answer_text: string | null;
  analysis_text: string | null;
  analysis_blocks?: StemBlock[];
  confidence: number | null;
  status: string;
  options?: Array<{
    id: string;
    option_label: string;
    option_text: string | null;
    option_blocks?: StemBlock[];
    is_correct: boolean;
    order_no: number;
  }>;
};

export type PaperSection = {
  id: string;
  title: string;
  section_type: string;
  order_no: number;
  questions: PaperQuestion[];
};

export type PaperDetail = {
  paper_id: string;
  title?: string;
  subject?: string;
  region?: string | null;
  exam_year?: number;
  exam_type?: string | null;
  parse_run_id?: string | null;
  sections: PaperSection[];
};

export type DeletePaperResponse = {
  paper_id: string;
  deleted: boolean;
  warnings: string[];
};

export type QuestionTag = {
  question_id: string;
  tag_id: string;
  tag_type: string;
  name: string;
  source: string;
  confidence: number | null;
};

export type ReviewLog = {
  id: string;
  target_type: string;
  target_id: string;
  action_type: string;
  before_json: string;
  after_json: string;
  reviewer: string | null;
};

export type ParseWarning = {
  id: string;
  warning_code: string;
  warning_level: string;
  warning_message: string;
  warning_meta_json: string;
};

export type PracticeLearningState = {
  mastered: boolean;
  wrong_count: number;
  last_result: string | null;
  last_attempt_at: string | null;
};

export type PracticeQuestion = {
  question_id: string;
  paper_id: string;
  question_no: string;
  order_no: number;
  question_type: string;
  stem_text: string | null;
  stem_blocks?: StemBlock[];
  answer_text: string | null;
  analysis_text: string | null;
  analysis_blocks?: StemBlock[];
  options?: Array<{
    id: string;
    option_label: string;
    option_text: string | null;
    option_blocks?: StemBlock[];
    is_correct: boolean;
    order_no: number;
  }>;
  mastered: boolean;
  wrong_count: number;
  last_result: string | null;
  last_attempt_at: string | null;
};

export type PracticeSessionInfo = {
  id: string;
  paper_id: string | null;
  mode: string;
  randomized: boolean;
  exclude_mastered: boolean;
  single_choice_count: number;
  fill_blank_count: number;
  short_answer_count: number;
  status: string;
  created_at: string | null;
  question_ids: string[];
  selected_counts: Record<string, number>;
  available_counts: Record<string, number>;
};

export type PracticeSessionResponse = {
  session: PracticeSessionInfo;
  questions: PracticeQuestion[];
};

export type PracticeAttemptResponse = {
  learning_state: PracticeLearningState;
};

export type PracticeQuestionListResponse = {
  total: number;
  items: PracticeQuestion[];
};

export type PracticeQuestionDetail = {
  question: {
    question_id: string;
    paper_id: string;
    question_no: string;
    order_no: number;
    question_type: string;
    stem_text: string | null;
    stem_blocks?: StemBlock[];
    answer_text: string | null;
    analysis_text: string | null;
    analysis_blocks?: StemBlock[];
    options?: Array<{
      id: string;
      option_label: string;
      option_text: string | null;
      option_blocks?: StemBlock[];
      is_correct: boolean;
      order_no: number;
    }>;
  };
  learning_state: PracticeLearningState;
  recent_attempts: Array<{
    id: string;
    question_id: string;
    session_id: string | null;
    result: string;
    answer_payload: unknown;
    created_at: string | null;
  }>;
};

function parseErrorPayload(payload: unknown): ApiErrorPayload {
  if (!payload || typeof payload !== "object") {
    return {};
  }
  return payload as ApiErrorPayload;
}

function isDuplicatePayload(payload: ApiErrorPayload): boolean {
  const code = payload.code ?? payload.error_code;
  if (typeof code === "string" && code.toUpperCase() === "DUPLICATE_PAPER") {
    return true;
  }

  return payload.duplicate_found === true;
}

function extractErrorMessage(payload: ApiErrorPayload, fallback: string): string {
  if (typeof payload.message === "string" && payload.message.trim()) {
    return payload.message;
  }
  if (payload.detail && typeof payload.detail === "object") {
    const nested = payload.detail as ApiErrorPayload;
    if (typeof nested.message === "string" && nested.message.trim()) {
      return nested.message;
    }
  }
  if (typeof payload.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }
  return fallback;
}

export async function importPaper(formData: FormData, duplicatePolicy?: DuplicatePolicy): Promise<ImportPaperResponse> {
  if (duplicatePolicy) {
    formData.set("duplicate_policy", duplicatePolicy);
  }

  const response = await fetch("/api/papers/import", {
    method: "POST",
    body: formData,
  });

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const errorPayload = parseErrorPayload(payload);
    const fallback = response.status === 409 ? "妫€娴嬪埌閲嶅璇曞嵎" : "瀵煎叆澶辫触";
    const message = extractErrorMessage(errorPayload, fallback);
    if (response.status === 409 || isDuplicatePayload(errorPayload)) {
      throw new ImportDuplicateError(message);
    }
    throw new Error(message);
  }

  return payload as ImportPaperResponse;
}

export async function listPapers(): Promise<PaperSummary[]> {
  const response = await fetch("/api/papers");
  if (!response.ok) {
    throw new Error("鑾峰彇璇曞嵎鍒楄〃澶辫触");
  }
  return response.json();
}

export async function getPaper(paperId: string): Promise<PaperDetail> {
  const response = await fetch(`/api/papers/${paperId}`);
  if (!response.ok) {
    throw new Error("鑾峰彇璇曞嵎璇︽儏澶辫触");
  }
  return response.json();
}

export async function deletePaper(paperId: string): Promise<DeletePaperResponse> {
  const response = await fetch(`/api/papers/${paperId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message =
      payload && typeof payload === "object" && typeof (payload as { detail?: unknown }).detail === "string"
        ? String((payload as { detail?: unknown }).detail)
        : "删除试卷失败";
    throw new Error(message);
  }

  return response.json();
}

export async function searchQuestions(params: Record<string, string | number | undefined>) {
  const url = new URL("/api/questions/search", window.location.origin);

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error("搜索失败");
  }
  return response.json();
}

export async function updateQuestion(questionId: string, payload: Record<string, unknown>) {
  const response = await fetch(`/api/questions/${questionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("鏇存柊澶辫触");
  }

  return response.json();
}

export async function listQuestionTags(questionId: string): Promise<QuestionTag[]> {
  const response = await fetch(`/api/questions/${questionId}/tags`);
  if (!response.ok) {
    throw new Error("鑾峰彇鏍囩澶辫触");
  }
  return response.json();
}

export async function addQuestionTag(
  questionId: string,
  payload: { tag_type: string; name: string; source?: string; confidence?: number },
): Promise<QuestionTag> {
  const response = await fetch(`/api/questions/${questionId}/tags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("娣诲姞鏍囩澶辫触");
  }
  return response.json();
}

export async function removeQuestionTag(questionId: string, tagId: string, source?: string) {
  const url = new URL(`/api/questions/${questionId}/tags/${tagId}`, window.location.origin);
  if (source) {
    url.searchParams.set("source", source);
  }
  const response = await fetch(url.toString(), { method: "DELETE" });
  if (!response.ok) {
    throw new Error("鍒犻櫎鏍囩澶辫触");
  }
  return response.json();
}

export async function listReviewLogs(): Promise<ReviewLog[]> {
  const response = await fetch("/api/review-logs");
  if (!response.ok) {
    throw new Error("鑾峰彇瀹℃牳鏃ュ織澶辫触");
  }
  return response.json();
}

export async function listParseWarnings(parseRunId: string): Promise<ParseWarning[]> {
  const response = await fetch(`/api/parse-runs/${parseRunId}/warnings`);
  if (!response.ok) {
    throw new Error("鑾峰彇瑙ｆ瀽璀﹀憡澶辫触");
  }
  return response.json();
}

export async function listPracticeQuestions(params: {
  mastered?: boolean;
  min_wrong_count?: number;
  paper_id?: string;
  question_type?: string;
} = {}): Promise<PracticeQuestionListResponse> {
  const url = new URL("/api/practice/questions", window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error("鑾峰彇缁冧範棰樼洰澶辫触");
  }
  return response.json();
}

export async function createPracticeSession(payload: {
  paper_id?: string;
  randomized?: boolean;
  exclude_mastered?: boolean;
  single_choice_count?: number;
  fill_blank_count?: number;
  short_answer_count?: number;
}): Promise<PracticeSessionResponse> {
  const response = await fetch("/api/practice/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("鍒涘缓缁冧範鍦烘櫙澶辫触");
  }
  return response.json();
}

export async function recordPracticeAttempt(payload: {
  question_id: string;
  result: string;
  session_id?: string | null;
  answer_payload?: unknown;
}): Promise<PracticeAttemptResponse> {
  const response = await fetch("/api/practice/attempts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("璁板綍缁冧範澶辫触");
  }
  return response.json();
}

export async function getPracticeQuestion(questionId: string): Promise<PracticeQuestionDetail> {
  const response = await fetch(`/api/practice/questions/${questionId}`);
  if (!response.ok) {
    throw new Error("获取练习题详情失败");
  }
  return response.json();
}

