export interface User {
  id: number;
  email: string;
  name: string;
  created_at: string;
}

export type PaperStatus = 'uploaded' | 'uploading' | 'processing' | 'needs_review' | 'ready' | 'failed' | 'archived';

export interface Option {
  id: number;
  text: string;      // mapped from option_text in API
  label: string;     // 'A' | 'B' | 'C' | 'D'
  image_url?: string | null;
  is_correct?: boolean;
}

export interface Question {
  id: number;
  paper_id?: number;
  number: number;    // mapped from question_number
  text: string;      // mapped from question_text
  image_url?: string | null;
  paper_set?: string | null;
  options: Option[];
  correct_option_id: number | null;
  explanation?: string | null;
  question_type?: string;
}

export interface QuestionUpdate {
  text?: string;
  image_url?: string | null;
  options?: { id: number; text: string; label?: string }[];
  correct_option_id?: number | null;
  explanation?: string;
}

export interface Paper {
  id: number;
  title: string;
  status: PaperStatus;
  question_count: number;
  created_at: string;
  filename?: string;
  duration_seconds?: number;
}

// ---- Paper metadata returned after processing ----
export interface PaperCategory {
  name: string;
  q_start: number;
  q_end: number;
  count: number;
}

export interface PaperSetInfo {
  label: string;
  q_count: number;
}

export interface PaperMeta {
  paper_id: number;
  title: string;
  exam_title: string;
  categories: PaperCategory[];
  paper_sets: PaperSetInfo[];
  duration_minutes: number | null;
  warnings?: string[];
  extraction_method?: string;
  unkeyed_questions?: number;
}

/** Payload sent to submit endpoint */
export interface AnswerPayload {
  question_id: number;
  selected_option_id: number | null;
  time_spent_seconds: number;
}

/** Kept for backward compat in attempts.ts */
export type Answer = AnswerPayload;

export interface AttemptRead {
  id: number;
  paper_id: number;
  started_at: string;
  submitted_at: string | null;
  score: number | null;
  total_questions: number;
  status: string;
}

export interface ResultQuestion {
  question_id: number;
  number?: number;
  text: string;      // question_text from backend
  image_url?: string | null;
  options: Option[];
  correct_option_id: number | null;
  selected_option_id: number | null;
  is_correct: boolean | null;
  explanation?: string | null;
  time_spent: number;
}

export interface AttemptResult {
  attempt: AttemptRead;
  answers: ResultQuestion[];
}

export interface AttemptHistory {
  id: number;
  paper_id: number;
  paper_title: string;
  score: number | null;
  total_questions: number;
  started_at: string;
  submitted_at: string | null;
  status: string;
}

export interface StartAttemptResponse {
  attempt_id: number;
  paper_id: number;
  total_questions: number;
  started_at: string;
  questions: Question[];
  duration_seconds?: number;
}
