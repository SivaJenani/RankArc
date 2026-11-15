import { create } from 'zustand';
import type { Question } from '../types';

interface TestState {
  questions: Question[];
  answers: Record<number, number | null>; // questionId -> selectedOptionId
  timeSpent: Record<number, number>; // questionId -> seconds
  currentIndex: number;
  timeLeft: number; // seconds remaining
  attemptId: number | null;
  isSubmitting: boolean;
}

interface TestActions {
  initTest: (attemptId: number, questions: Question[], durationSeconds: number) => void;
  setAnswer: (questionId: number, optionId: number | null) => void;
  setCurrentIndex: (index: number) => void;
  tickTimer: () => void;
  addTimeSpent: (questionId: number, seconds: number) => void;
  setSubmitting: (val: boolean) => void;
  resetTest: () => void;
}

const initialState: TestState = {
  questions: [],
  answers: {},
  timeSpent: {},
  currentIndex: 0,
  timeLeft: 0,
  attemptId: null,
  isSubmitting: false,
};

export const useTestStore = create<TestState & TestActions>((set) => ({
  ...initialState,

  initTest: (attemptId, questions, durationSeconds) => {
    const answers: Record<number, number | null> = {};
    questions.forEach((q) => {
      answers[q.id] = null;
    });
    const state = { attemptId, questions, answers, timeSpent: {}, currentIndex: 0, timeLeft: durationSeconds, isSubmitting: false };
    set(state);
    // Persist to sessionStorage for refresh resilience
    sessionStorage.setItem('rankly_test', JSON.stringify(state));
  },

  setAnswer: (questionId, optionId) =>
    set((state) => {
      const updated = { ...state.answers, [questionId]: optionId };
      return { answers: updated };
    }),

  setCurrentIndex: (index) => set({ currentIndex: index }),

  tickTimer: () =>
    set((state) => {
      const newTime = Math.max(0, state.timeLeft - 1);
      return { timeLeft: newTime };
    }),

  addTimeSpent: (questionId, seconds) =>
    set((state) => ({
      timeSpent: {
        ...state.timeSpent,
        [questionId]: (state.timeSpent[questionId] || 0) + seconds,
      },
    })),

  setSubmitting: (val) => set({ isSubmitting: val }),

  resetTest: () => {
    sessionStorage.removeItem('rankly_test');
    set(initialState);
  },
}));
