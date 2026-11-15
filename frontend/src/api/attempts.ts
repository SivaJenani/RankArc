import client from './client';
import type { AttemptResult, AttemptHistory, StartAttemptResponse, AnswerPayload } from '../types';

function mapQuestion(raw: any) {
  return {
    id: raw.id,
    number: raw.question_number ?? raw.number,
    text: raw.question_text ?? raw.text,
    image_url: raw.image_url ?? null,
    paper_set: raw.paper_set ?? null,
    question_type: raw.question_type,
    correct_option_id: raw.correct_option_id ?? null,
    explanation: raw.explanation ?? null,
    options: (raw.options ?? []).map((o: any) => ({
      id: o.id,
      label: o.label,
      text: o.option_text ?? o.text,
      image_url: o.image_url ?? null,
      is_correct: o.is_correct,
    })),
  };
}

function mapResultQuestion(raw: any) {
  return {
    question_id: raw.question_id,
    number: raw.question_number ?? raw.number,
    text: raw.question_text ?? raw.text,
    image_url: raw.image_url ?? null,
    options: (raw.options ?? []).map((o: any) => ({
      id: o.id,
      label: o.label,
      text: o.option_text ?? o.text,
      image_url: o.image_url ?? null,
      is_correct: o.is_correct,
    })),
    correct_option_id: raw.correct_option_id ?? null,
    selected_option_id: raw.selected_option_id ?? null,
    is_correct: raw.is_correct ?? null,
    explanation: raw.explanation ?? null,
    time_spent: raw.time_spent ?? 0,
  };
}

export const startAttempt = async (paperId: number, paperSet?: string): Promise<StartAttemptResponse> => {
  const params = paperSet ? { paper_set: paperSet } : {};
  const { data } = await client.post<any>(`/api/attempts/start/${paperId}`, null, { params });
  return {
    attempt_id: data.attempt_id,
    paper_id: data.paper_id,
    total_questions: data.total_questions,
    started_at: data.started_at,
    questions: (data.questions ?? []).map(mapQuestion),
    duration_seconds: data.duration_seconds ?? data.total_questions * 60,
  };
};

export const submitAttempt = async (
  attemptId: number,
  answers: AnswerPayload[]
): Promise<{ id: number; status: string }> => {
  const { data } = await client.post(`/api/attempts/${attemptId}/submit`, { answers });
  return data;
};

export const getResult = async (attemptId: number): Promise<AttemptResult> => {
  const { data } = await client.get<any>(`/api/attempts/${attemptId}/result`);
  return {
    attempt: data.attempt,
    answers: (data.answers ?? []).map(mapResultQuestion),
  };
};

export const getHistory = async (): Promise<AttemptHistory[]> => {
  const { data } = await client.get<AttemptHistory[]>('/api/attempts/history');
  return data;
};
