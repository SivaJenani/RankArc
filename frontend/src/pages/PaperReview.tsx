import AnswerKeyUpload from '../components/AnswerKeyUpload';
import { DEMO_MODE } from '../api/demo';
import PrivateImage from '../components/PrivateImage';
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { getPaperQuestions, updateQuestion } from '../api/papers';
import { startAttempt } from '../api/attempts';
import { useTestStore } from '../store/testStore';
import type { Question } from '../types';

interface EditState {
  text: string;
  options: { id: number; text: string; label: string }[];
  correct_option_id: number | null;
}

function QuestionEditor({
  question,
  index,
  paperId,
  onUpdated,
}: {
  question: Question;
  index: number;
  paperId: number;
  onUpdated: (q: Question) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [edit, setEdit] = useState<EditState>({
    text: question.text,
    options: question.options.map((o) => ({ id: o.id, text: o.text, label: o.label })),
    correct_option_id: question.correct_option_id,
  });

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateQuestion(paperId, question.id, {
        text: edit.text,
        options: edit.options.map((o) => ({ id: o.id, text: o.text, label: o.label })),
        correct_option_id: edit.correct_option_id,
      });
      setEdit({ text: updated.text, options: updated.options.map(o => ({id:o.id,text:o.text,label:o.label})), correct_option_id: updated.correct_option_id });
      onUpdated(updated);
      setEditing(false);
      toast.success('Question updated!');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save question.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEdit({
      text: question.text,
      options: question.options.map((o) => ({ id: o.id, text: o.text, label: o.label })),
      correct_option_id: question.correct_option_id,
    });
    setEditing(false);
  };

  return (
    <div className="bg-card/80 backdrop-blur border border-fg/10 rounded-2xl p-5 space-y-4 shadow-sm">
      {/* Question header */}
      <div className="flex items-start justify-between gap-3">
        <span className="shrink-0 w-7 h-7 bg-accent text-onaccent rounded-lg text-xs font-bold flex items-center justify-center">
          {index + 1}
        </span>

        {editing ? (
          <textarea
            value={edit.text}
            onChange={(e) => setEdit((s) => ({ ...s, text: e.target.value }))}
            className="flex-1 min-w-0 px-3 py-2 rounded-xl border border-accent bg-card text-fg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent min-h-[80px] resize-y"
          />
        ) : (
          <p className="flex-1 text-fg font-medium text-sm leading-relaxed">{question.text}</p>
        )}

        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="shrink-0 p-1.5 rounded-lg hover:bg-accent/20 text-muted hover:text-onaccent transition-colors"
            title="Edit question"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
        )}
      </div>

      {/* Question Diagram / Image if present */}
      {question.image_url && (
        <div className="mb-4 ml-10 p-3 bg-card rounded-2xl border-2 border-fg/10 max-w-2xl shadow-sm">
          <div>
            <PrivateImage
              src={question.image_url}
              alt={`Question ${question.number} diagram`}
              className="w-full h-auto max-w-full object-contain rounded-lg hover:opacity-95 transition-opacity"
              loading="lazy"
            />
          </div>
        </div>
      )}

      {/* Options */}
      <div className="grid gap-2 ml-10">
        {(editing ? edit.options : question.options).map((opt, oi) => {
          const isCorrect = editing
            ? opt.id === edit.correct_option_id
            : opt.id === question.correct_option_id;

          return (
            <div
              key={opt.id}
              className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                isCorrect
                  ? 'border-accent bg-accent/15'
                  : 'border-fg/10 bg-card/60'
              }`}
            >
              <span className={`shrink-0 w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center ${
                isCorrect ? 'bg-accent text-onaccent' : 'bg-nav/10 text-muted'
              }`}>
                {opt.label || String.fromCharCode(65 + oi)}
              </span>

              {editing ? (
                <input
                  value={opt.text}
                  onChange={(e) =>
                    setEdit((s) => ({
                      ...s,
                      options: s.options.map((o) =>
                        o.id === opt.id ? { ...o, text: e.target.value } : o
                      ),
                    }))
                  }
                  className="flex-1 min-w-0 w-full text-sm bg-transparent border-none focus:outline-none text-fg font-medium"
                />
              ) : (
                <span className="flex-1 text-sm text-fg font-medium">{opt.text}</span>
              )}

              {editing && (
                <button
                  onClick={() => setEdit((s) => ({ ...s, correct_option_id: opt.id }))}
                  className={`shrink-0 text-xs px-2 py-1 rounded-lg font-semibold transition-colors ${
                    isCorrect
                      ? 'bg-accent text-onaccent'
                      : 'bg-nav/10 text-muted hover:bg-accent/20 hover:text-onaccent'
                  }`}
                >
                  {isCorrect ? '✓ Correct' : 'Mark correct'}
                </button>
              )}

              {!editing && isCorrect && (
                <svg className="w-4 h-4 text-accent shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </div>
          );
        })}
      </div>

      {/* Edit actions */}
      {editing && (
        <div className="flex gap-2 ml-10">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-accent text-onaccent text-sm font-bold rounded-xl hover:bg-accenth transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button
            onClick={handleCancel}
            className="px-4 py-2 border border-fg/20 text-fg text-sm font-semibold rounded-xl !bg-transparent hover:border-deeptext transition-colors"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

export default function PaperReview() {
  const { id } = useParams<{ id: string }>();
  const paperId = Number(id);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selectedShift, setSelectedShift] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const { initTest } = useTestStore();
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    const fetch = async () => {
      try {
        const qs = await getPaperQuestions(paperId);
        setQuestions(qs);
      } catch {
        toast.error('Failed to load questions.');
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [paperId]);

  const handleStartTest = async () => {
    // Go through the set picker so user can choose which paper set to attempt
    navigate(`/papers/${paperId}/sets`);
  };

  const handleUpdated = (updated: Question) => {
    setQuestions((qs) => qs.map((q) => (q.id === updated.id ? updated : q)));
  };

  const distinctShifts = Array.from(
    new Set(questions.map((q) => q.paper_set).filter(Boolean))
  ) as string[];

  const displayedQuestions = selectedShift === 'all'
    ? questions
    : questions.filter((q) => q.paper_set === selectedShift);

  return (
    <div className="min-h-screen bg-page px-4 py-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-black text-fg tracking-tight">Review Paper</h1>
            <p className="text-muted mt-1">
              {loading ? 'Loading questions…' : `${questions.length} questions across ${distinctShifts.length || 1} shift${distinctShifts.length > 1 ? 's' : ''} — review and edit before starting`}
            </p>
          </div>
          {!loading && questions.length > 0 && (
            <button
              onClick={handleStartTest}
              disabled={starting}
              className="inline-flex items-center gap-2 px-5 py-3 bg-accent hover:bg-accenth text-onaccent font-bold rounded-xl transition-colors disabled:opacity-50"
            >
              Choose Shift to Test →
            </button>
          )}
        </div>

        {!loading && questions.length > 0 && !DEMO_MODE && <AnswerKeyUpload key={paperId} paperId={paperId} />}

        {/* Shift Filter Tabs if multi-shift */}
        {distinctShifts.length > 1 && (
          <div className="flex items-center gap-2 overflow-x-auto pb-4 mb-6">
            <button
              onClick={() => setSelectedShift('all')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                selectedShift === 'all'
                  ? 'bg-nav text-accent'
                  : 'bg-card border border-fg/10 text-muted hover:border-accent'
              }`}
            >
              All Shifts ({questions.length})
            </button>
            {distinctShifts.map((shift, i) => {
              const count = questions.filter((q) => q.paper_set === shift).length;
              return (
                <button
                  key={shift}
                  onClick={() => setSelectedShift(shift)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                    selectedShift === shift
                      ? 'bg-nav text-accent'
                      : 'bg-card border border-fg/10 text-muted hover:border-accent'
                  }`}
                >
                  Shift {i + 1} ({count})
                </button>
              );
            })}
          </div>
        )}

        {/* Questions */}
        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="bg-card/50 rounded-2xl p-5 animate-pulse space-y-3">
                <div className="h-4 bg-nav/10 rounded w-3/4" />
                <div className="space-y-2 ml-10">
                  {[1, 2, 3, 4].map((j) => (
                    <div key={j} className="h-10 bg-nav/10 rounded-xl" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : displayedQuestions.length === 0 ? (
          <div className="text-center py-16 text-muted">No questions found for this shift.</div>
        ) : (
          <div className="space-y-4">
            {displayedQuestions.map((q, i) => (
              <QuestionEditor
                key={q.id}
                question={q}
                index={i}
                paperId={paperId}
                onUpdated={handleUpdated}
              />
            ))}
          </div>
        )}

        {/* Footer start button */}
        {!loading && questions.length > 0 && (
          <div className="mt-8 flex justify-center">
            <button
              onClick={handleStartTest}
              disabled={starting}
              className="inline-flex items-center gap-2 px-8 py-4 bg-accent hover:bg-accenth text-onaccent font-bold text-lg rounded-xl transition-colors disabled:opacity-50"
            >
              {starting ? 'Starting…' : 'Start Test →'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
