import { useEffect, useRef, useState, Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useTestStore, TEST_STORAGE_KEY } from '../store/testStore';
import { submitAttempt } from '../api/attempts';
import Timer from '../components/Timer';
import QuestionPalette from '../components/QuestionPalette';

// ─── Error Boundary (class component) ───────────────────────────────────────
class TestErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: string }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: '' };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('TestScreen error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-page flex items-center justify-center px-4">
          <div className="text-center max-w-md bg-card/90 p-8 rounded-2xl border border-fg/10 shadow-lg">
            <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-2xl flex items-center justify-center">
              <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-xl font-black text-fg mb-2">Something went wrong</h2>
            <p className="text-muted text-sm mb-4">{this.state.error}</p>
            <p className="text-muted text-sm mb-6">
              Your progress may be saved. Please go back to the dashboard.
            </p>
            <a
              href={location.pathname.startsWith('/demo') ? '/demo/dashboard' : '/dashboard'}
              className="inline-block px-6 py-3 bg-accent text-onaccent font-bold rounded-xl hover:bg-accenth transition-colors"
            >
              Go to Dashboard
            </a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── Main TestScreen ──────────────────────────────────────────────────────────
function TestScreenInner() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const navigate = useNavigate();
  const {
    questions, answers, currentIndex, timeLeft, isSubmitting,
    setAnswer, setCurrentIndex, tickTimer, addTimeSpent, setSubmitting, resetTest,
  } = useTestStore();

  const [showConfirm, setShowConfirm] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [zoomImage, setZoomImage] = useState<string | null>(null);
  const questionStartRef = useRef<number>(Date.now());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoSubmittedRef = useRef(false);

  const numId = Number(attemptId);

  // Restore from sessionStorage if store is empty (page refresh)
  useEffect(() => {
    if (questions.length === 0) {
      const saved = sessionStorage.getItem(TEST_STORAGE_KEY);
      if (saved) {
        try {
          const state = JSON.parse(saved);
          if (state.attemptId === numId) {
            useTestStore.setState({
              questions: state.questions,
              answers: state.answers,
              currentIndex: state.currentIndex,
              timeLeft: state.timeLeft,
              attemptId: state.attemptId,
            });
          }
        } catch {
          // ignore
        }
      }
    }
  }, [numId, questions.length]);

  // Timer countdown
  useEffect(() => {
    if (questions.length === 0) return;
    timerRef.current = setInterval(() => {
      tickTimer();
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [questions.length, tickTimer]);

  // Auto-submit when time hits 0
  useEffect(() => {
    if (timeLeft === 0 && questions.length > 0 && !autoSubmittedRef.current && !isSubmitting) {
      autoSubmittedRef.current = true;
      if (timerRef.current) clearInterval(timerRef.current);
      toast('Time is up! Submitting your test…', { icon: '⏰' });
      handleSubmit(true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft]);

  // Track time spent per question
  useEffect(() => {
    questionStartRef.current = Date.now();
    return () => {
      const spent = Math.floor((Date.now() - questionStartRef.current) / 1000);
      if (questions[currentIndex]) {
        addTimeSpent(questions[currentIndex].id, spent);
      }
    };
  }, [currentIndex, questions, addTimeSpent]);

  const handleOptionSelect = (optionId: number) => {
    if (isSubmitting) return;
    const qId = questions[currentIndex]?.id;
    if (qId) setAnswer(qId, optionId);
  };

  const handleSubmit = async (auto = false) => {
    if (isSubmitting) return;
    setSubmitting(true);
    if (timerRef.current) clearInterval(timerRef.current);

    const { answers: storeAnswers, timeSpent } = useTestStore.getState();

    const payload = questions.map((q) => ({
      question_id: q.id,
      selected_option_id: storeAnswers[q.id] ?? null,
      time_spent_seconds: timeSpent[q.id] ?? 0,
    }));

    try {
      await submitAttempt(numId, payload as any);
      resetTest();
      navigate(`/results/${numId}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Submit failed. Please try again.');
      setSubmitting(false);
      if (!auto) autoSubmittedRef.current = false;
    }
  };

  if (questions.length === 0) {
    return (
      <div className="min-h-screen bg-page flex items-center justify-center px-4">
        <div className="text-center bg-card/90 p-8 rounded-2xl border border-fg/10 shadow-lg">
          <div className="w-16 h-16 mx-auto mb-4 bg-accent/15 rounded-2xl flex items-center justify-center">
            <svg className="w-8 h-8 text-deeptext" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h2 className="text-xl font-black text-fg mb-2">No test loaded</h2>
          <p className="text-muted text-sm mb-6">Start a test from the paper review page.</p>
          <a href={location.pathname.startsWith('/demo') ? '/demo/dashboard' : '/dashboard'}
            className="inline-block px-5 py-2.5 bg-accent text-onaccent font-bold rounded-xl hover:bg-accenth transition-colors">
            Go to Dashboard
          </a>
        </div>
      </div>
    );
  }

  const currentQuestion = questions[currentIndex];
  const selectedOptionId = answers[currentQuestion?.id] ?? null;
  const answeredCount = Object.values(answers).filter((v) => v !== null).length;

  return (
    <div className="min-h-screen bg-page flex flex-col">
      {/* Top bar */}
      <div className="sticky top-0 z-40 bg-nav border-b border-deeptext">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-invfg font-bold text-sm">
              Q {currentIndex + 1} / {questions.length}
            </span>
            <span className="hidden sm:block text-subtle text-xs">
              {answeredCount} answered · {questions.length - answeredCount} remaining
            </span>
          </div>

          <Timer timeLeft={timeLeft} />

          <div className="flex items-center gap-2">
            {/* Mobile palette toggle */}
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="lg:hidden p-2 rounded-lg bg-deep text-accent hover:bg-deep/80 transition-colors"
              title="Question palette"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h7" />
              </svg>
            </button>

            <button
              onClick={() => setShowConfirm(true)}
              disabled={isSubmitting}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-bold rounded-lg transition-colors disabled:opacity-50"
            >
              Submit
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-1 max-w-7xl mx-auto w-full px-4 py-6 gap-6">
        {/* Question area */}
        <div className="flex-1 min-w-0">
          <div className="bg-card/80 backdrop-blur border border-fg/10 rounded-2xl p-6 mb-4 shadow-sm">
            {/* Question header */}
            <div className="flex items-start gap-3 mb-5">
              <span className="shrink-0 w-8 h-8 bg-accent text-onaccent rounded-lg text-sm font-bold flex items-center justify-center">
                {currentIndex + 1}
              </span>
              <p className="text-fg font-medium leading-relaxed flex-1">
                {currentQuestion.text}
              </p>
            </div>

            {/* Question Diagram / Image if present */}
            {currentQuestion.image_url && (
              <div className="mb-6 ml-11 flex flex-col items-start">
                <div 
                  onClick={() => setZoomImage(currentQuestion.image_url ?? null)}
                  className="group relative cursor-zoom-in p-4 bg-card rounded-2xl border-2 border-fg/10 hover:border-accent shadow-sm max-w-3xl transition-all"
                >
                  <img
                    src={currentQuestion.image_url}
                    alt={`Question ${currentIndex + 1} diagram`}
                    className="max-h-96 w-auto max-w-full object-contain rounded-lg"
                    loading="lazy"
                  />
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-nav/80 text-white text-xs px-2.5 py-1 rounded-lg flex items-center gap-1 shadow-md">
                    <svg className="w-3.5 h-3.5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                    </svg>
                    Click to enlarge
                  </div>
                </div>
              </div>
            )}

            {/* Options */}
            <div className="space-y-3 ml-11">
              {currentQuestion.options.map((opt, i) => {
                const isSelected = selectedOptionId === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => handleOptionSelect(opt.id)}
                    disabled={isSubmitting}
                    className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 text-left transition-all ${
                      isSelected
                        ? 'border-accent bg-accent/15'
                        : 'border-fg/15 hover:border-accent/40 bg-card/70'
                    }`}
                  >
                    <span className={`shrink-0 w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center transition-colors ${
                      isSelected ? 'bg-accent text-onaccent' : 'bg-nav/10 text-muted'
                    }`}>
                      {opt.label || String.fromCharCode(65 + i)}
                    </span>
                    <span className="text-sm text-fg font-medium flex-1">{opt.text}</span>
                    {isSelected && (
                      <svg className="w-4 h-4 text-accent shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between gap-3">
            <button
              onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
              disabled={currentIndex === 0 || isSubmitting}
              className="flex items-center gap-2 px-4 py-2.5 border border-fg/20 text-fg text-sm font-semibold rounded-xl hover:border-deeptext transition-colors disabled:opacity-30 disabled:cursor-not-allowed bg-card/60"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Previous
            </button>

            <button
              onClick={() => {
                setAnswer(currentQuestion.id, null);
                setCurrentIndex(Math.min(questions.length - 1, currentIndex + 1));
              }}
              disabled={isSubmitting}
              className="px-4 py-2.5 border border-fg/20 text-muted text-sm font-semibold rounded-xl hover:border-deeptext hover:text-fg transition-colors disabled:opacity-30 bg-card/60"
            >
              Skip
            </button>

            {currentIndex < questions.length - 1 ? (
              <button
                onClick={() => setCurrentIndex(currentIndex + 1)}
                disabled={isSubmitting}
                className="flex items-center gap-2 px-4 py-2.5 bg-accent hover:bg-accenth text-onaccent text-sm font-bold rounded-xl transition-colors disabled:opacity-50"
              >
                Next
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            ) : (
              <button
                onClick={() => setShowConfirm(true)}
                disabled={isSubmitting}
                className="flex items-center gap-2 px-4 py-2.5 bg-accent hover:bg-accenth text-onaccent text-sm font-bold rounded-xl transition-colors disabled:opacity-50"
              >
                Finish
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Desktop Sidebar Palette */}
        <div className="hidden lg:block w-72 shrink-0">
          <div className="sticky top-20">
            <QuestionPalette
              total={questions.length}
              questionIds={questions.map((q) => q.id)}
              answers={answers}
              currentIndex={currentIndex}
              onJump={setCurrentIndex}
            />
            <div className="mt-4">
              <button
                onClick={() => setShowConfirm(true)}
                disabled={isSubmitting}
                className="w-full py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl transition-colors disabled:opacity-50 shadow-sm"
              >
                {isSubmitting ? 'Submitting…' : 'Submit Test'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Sidebar Drawer */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setSidebarOpen(false)} />
          <div className="absolute right-0 top-0 bottom-0 w-72 bg-page shadow-2xl p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-fg">Question Palette</h3>
              <button onClick={() => setSidebarOpen(false)} className="p-1 rounded-lg hover:bg-nav/10">
                <svg className="w-5 h-5 text-fg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <QuestionPalette
              total={questions.length}
              questionIds={questions.map((q) => q.id)}
              answers={answers}
              currentIndex={currentIndex}
              onJump={(i: number) => { setCurrentIndex(i); setSidebarOpen(false); }}
            />
            <button
              onClick={() => { setSidebarOpen(false); setShowConfirm(true); }}
              disabled={isSubmitting}
              className="w-full mt-4 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl transition-colors disabled:opacity-50"
            >
              Submit Test
            </button>
          </div>
        </div>
      )}

      {/* Confirm dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowConfirm(false)} />
          <div className="relative bg-card rounded-2xl p-6 max-w-sm w-full shadow-2xl border border-fg/10">
            <h2 className="text-xl font-black text-fg mb-2">Submit Test?</h2>
            <p className="text-muted text-sm mb-1">
              Answered: <strong className="text-fg">{answeredCount}</strong> / {questions.length}
            </p>
            {questions.length - answeredCount > 0 && (
              <p className="text-amber-600 text-sm mb-4 font-medium">
                ⚠️ {questions.length - answeredCount} question{questions.length - answeredCount !== 1 ? 's' : ''} unanswered
              </p>
            )}
            <p className="text-muted text-sm mb-6">You cannot change answers after submitting.</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 py-2.5 border border-fg/20 text-fg font-semibold rounded-xl hover:border-deeptext transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowConfirm(false); handleSubmit(); }}
                disabled={isSubmitting}
                className="flex-1 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Submitting…' : 'Yes, Submit'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lightbox zoom modal */}
      {zoomImage && (
        <div 
          onClick={() => setZoomImage(null)}
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4 cursor-zoom-out animate-fadeIn"
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className="relative max-w-5xl max-h-[92vh] bg-card rounded-3xl p-6 shadow-2xl flex flex-col items-center"
          >
            <button
              onClick={() => setZoomImage(null)}
              className="absolute -top-3 -right-3 w-9 h-9 rounded-full bg-nav text-accent font-bold flex items-center justify-center hover:bg-deep transition-colors shadow-xl border-2 border-white"
            >
              ✕
            </button>
            <img
              src={zoomImage}
              alt="Diagram preview"
              className="max-h-[82vh] w-auto max-w-full object-contain rounded-xl"
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default function TestScreen() {
  return (
    <TestErrorBoundary>
      <TestScreenInner />
    </TestErrorBoundary>
  );
}
