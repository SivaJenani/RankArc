import client from './client';
import type { Paper, PaperMeta, Question, QuestionUpdate } from '../types';

/** Map backend QuestionRead/OptionRead shape to our frontend Question shape */
function mapQuestion(raw: any): Question {
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

export interface PaperStatusResponse {
  status: string;
  progress: number;
  step: string;
}

export const getPapers = async (): Promise<Paper[]> => {
  const { data } = await client.get<Paper[]>('/api/papers/');
  return data;
};

export const uploadPaper = async (
  file: File,
  title: string,
  onProgress?: (percent: number, loaded: number, total: number) => void
): Promise<Paper> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);
  const { data } = await client.post<Paper>('/api/papers/upload', formData, {
    onUploadProgress: (progressEvent) => {
      const total = progressEvent.total || file.size;
      const loaded = progressEvent.loaded;
      if (total > 0) {
        const percent = Math.min(100, Math.round((loaded * 100) / total));
        onProgress?.(percent, loaded, total);
      }
    },
  });
  return data;
};

export const getPaperStatus = async (paperId: number): Promise<PaperStatusResponse> => {
  const { data } = await client.get<PaperStatusResponse>(`/api/papers/${paperId}/status`);
  return data;
};

export const getPaperMeta = async (paperId: number): Promise<PaperMeta> => {
  const { data } = await client.get<PaperMeta>(`/api/papers/${paperId}/meta`);
  return data;
};

export const getPaperQuestions = async (paperId: number, paperSet?: string): Promise<Question[]> => {
  const params = paperSet ? { paper_set: paperSet } : {};
  const { data } = await client.get<any[]>(`/api/papers/${paperId}/questions`, { params });
  return data.map(mapQuestion);
};

export const updateQuestion = async (
  paperId: number,
  questionId: number,
  updateData: QuestionUpdate
): Promise<Question> => {
  // Map frontend shape back to backend shape
  const payload: any = {};
  if (updateData.text !== undefined) payload.question_text = updateData.text;
  if (updateData.image_url !== undefined) payload.image_url = updateData.image_url;
  if (updateData.explanation !== undefined) payload.explanation = updateData.explanation;
  if (updateData.correct_option_id !== undefined) payload.correct_option_id = updateData.correct_option_id;
  if (updateData.options !== undefined) {
    payload.options = updateData.options.map((o) => ({
      id: o.id,
      option_text: o.text,
      label: o.label ?? '',
      is_correct: o.id === updateData.correct_option_id,
    }));
  }
  const { data } = await client.put<any>(`/api/papers/${paperId}/questions/${questionId}`, payload);
  return mapQuestion(data);
};
