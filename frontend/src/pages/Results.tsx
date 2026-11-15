import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { getResult } from '../api/attempts';
import { startAttempt } from '../api/attempts';
import { useTestStore } from '../store/testStore';
import type { AttemptResult, ResultQuestion } from '../types';

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function AnswerCard({ item, index }: { item: ResultQuestion; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const selectedOpt = item.options.find((o) => o.id === item.selected_option_id);
  const correctOpt = item.options.find((o) => o.id === item.correct_option_id);
  const isSkipped = item.selected_option_id === null;

  const borderColor = isSkipped
    ? 'border-[#000000]/10'
    : item.is_correct
    ? 'border-[#08CB00]'
    : 'border-red-400';

  const bgColor = isSkipped
    ? 'bg-white/80'
    : item.is_correct
    ? 'bg-[#08CB00]/10'
    : 'bg-red-500/10';

  return (
    <div className={`rounded-2xl border-2 ${borderColor} ${bgColor} overflow-hidden shadow-sm transition-all`}>
      {/* Header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start gap-3 p-4 text-left hover:opacity-90 transition-opacity"
      >
        <span className="shrink-0 w-7 h-7 bg-[#000000] text-[#08CB00] rounded-lg text-xs font-black flex items-center justify-center border border-[#253900]">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-[#000000] font-semibold text-sm leading-relaxed line-clamp-2">
            {item.text}
          </p>
          <div className="flex items-center gap-3 mt-2">
            {isSkipped ? (
              <span className="text-xs text-[#555555] font-semibold">— Not answered</span>
            ) : item.is_correct ? (
              <span className="text-xs text-[#253900] font-bold flex items-center gap-1">
                <svg className="w-3.5 h-3.5 text-[#08CB00]" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Correct
              </span>
            ) : (
              <span className="text-xs text-red-600 font-bold flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
                Incorrect
              </span>
            )}
            {item.time_spent > 0 && (
              <span className="text-xs text-[#555555]">{formatDuration(item.time_spent)}</span>
            )}
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-[#555555] shrink-0 mt-1 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-[#000000]/10 pt-3">
          {/* Question Diagram / Image if present */}
          {item.image_url && (
            <div className="mb-3 p-2 bg-white rounded-xl border border-[#000000]/10 max-w-md shadow-sm">
              <img
                src={item.image_url}
                alt={`Question ${item.number || ''} diagram`}
                className="max-h-60 w-auto object-contain rounded-lg"
                loading="lazy"
              />
            </div>
          )}

          {/* Options */}
          <div className="space-y-2">
            {item.options.map((opt, i) => {
              const isSelected = opt.id === item.selected_option_id;
              const isCorrect = opt.id === item.correct_option_id;
              return (
                <div
                  key={opt.id}
                  className={`flex items-center gap-2.5 p-3 rounded-xl border ${
                    isCorrect
                      ? 'border-[#08CB00] bg-[#08CB00]/20'
                      : isSelected && !isCorrect
                      ? 'border-red-400 bg-red-100'
                      : 'border-[#000000]/10 bg-white/70'
                  }`}
                >
                  <span className={`shrink-0 w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center ${
                    isCorrect ? 'bg-[#08CB00] text-[#000000]' : isSelected ? 'bg-red-500 text-white' : 'bg-black/10 text-[#555555]'
                  }`}>
                    {opt.label || String.fromCharCode(65 + i)}
                  </span>
                  <span className="text-sm text-[#000000] font-medium flex-1">{opt.text}</span>
                  {isCorrect && (
                    <span className="text-xs text-[#253900] font-bold">✓ Correct</span>
                  )}
                  {isSelected && !isCorrect && (
                    <span className="text-xs text-red-600 font-bold">✗ Your answer</span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Summary */}
          {!isSkipped && !item.is_correct && (
            <div className="text-sm text-[#555555] bg-white/70 rounded-xl p-3 border border-[#000000]/5">
              <span className="font-semibold text-[#000000]">Your answer: </span>
              {selectedOpt?.text ?? '—'}
              <br />
              <span className="font-semibold text-[#000000]">Correct answer: </span>
              {correctOpt?.text ?? '—'}
            </div>
          )}

          {/* Explanation */}
          {item.explanation && (
            <div className="text-sm text-[#253900] bg-[#08CB00]/10 border border-[#08CB00]/30 rounded-xl p-3">
              <p className="font-bold text-[#000000] mb-1 text-xs uppercase tracking-wide">Explanation</p>
              <p className="leading-relaxed">{item.explanation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Results() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const navigate = useNavigate();
  const { initTest } = useTestStore();
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [retaking, setRetaking] = useState(false);
  const numId = Number(attemptId);

  useEffect(() => {
    getResult(numId)
      .then(setResult)
      .catch(() => toast.error('Failed to load results.'))
      .finally(() => setLoading(false));
  }, [numId]);

  const handleRetake = async () => {
    if (!result) return;
    setRetaking(true);
    try {
      const { attempt_id, questions, duration_seconds } = await startAttempt(result.attempt.paper_id);
      initTest(attempt_id, questions, duration_seconds || 10800);
      navigate(`/test/${attempt_id}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to start new attempt.');
      setRetaking(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#EEEEEE] px-4 py-10">
        <div className="max-w-3xl mx-auto space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white/60 border border-[#000000]/5 rounded-2xl h-24 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="min-h-screen bg-[#EEEEEE] flex items-center justify-center">
        <p className="text-[#555555] font-semibold">Result not found.</p>
      </div>
    );
  }

  const { attempt, answers } = result;
  const correct = answers.filter((a) => a.is_correct === true).length;
  const wrong = answers.filter((a) => a.is_correct === false).length;
  const skipped = answers.filter((a) => a.selected_option_id === null).length;
  const percentage = attempt.total_questions > 0
    ? Math.round((correct / attempt.total_questions) * 100)
    : 0;
  const timeTaken = attempt.submitted_at && attempt.started_at
    ? Math.floor((new Date(attempt.submitted_at).getTime() - new Date(attempt.started_at).getTime()) / 1000)
    : 0;

  return (
    <div className="min-h-screen bg-[#EEEEEE] px-4 py-8">
      <div className="max-w-3xl mx-auto">
        {/* Score card */}
        <div className="bg-[#000000] text-[#EEEEEE] border border-[#253900] rounded-3xl p-6 md:p-8 mb-8 shadow-2xl">
          <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
            <div>
              <p className="text-[#08CB00] text-xs font-black uppercase tracking-widest mb-1">
                Test Complete
              </p>
              <h1 className="text-4xl md:text-5xl font-black tracking-tight text-white">
                {correct} <span className="text-[#08CB00]">/</span> {attempt.total_questions}
              </h1>
              <p className="text-[#EEEEEE]/70 mt-1 font-medium">questions correct</p>
            </div>
            <div className="text-right">
              <div className="text-5xl md:text-6xl font-black text-[#08CB00]">{percentage}%</div>
              <p className="text-[#EEEEEE]/70 text-sm mt-1">{formatDuration(timeTaken)} taken</p>
            </div>
          </div>

          <div className="flex gap-3 flex-wrap">
            {[
              { label: 'Correct', value: correct, color: 'bg-[#253900] text-[#08CB00] border border-[#08CB00]/40' },
              { label: 'Incorrect', value: wrong, color: 'bg-red-950/60 text-red-400 border border-red-800/40' },
              { label: 'Skipped', value: skipped, color: 'bg-white/10 text-white/70 border border-white/10' },
            ].map((stat) => (
              <div key={stat.label} className={`flex-1 min-w-[90px] rounded-2xl p-3 text-center ${stat.color}`}>
                <div className="text-2xl font-black">{stat.value}</div>
                <div className="text-xs font-bold uppercase tracking-wider mt-0.5">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 mb-8 flex-wrap">
          <button
            onClick={handleRetake}
            disabled={retaking}
            className="flex items-center gap-2 px-5 py-3 bg-[#08CB00] hover:bg-[#07b000] text-[#000000] font-black rounded-xl transition-all shadow-md disabled:opacity-50"
          >
            {retaking ? 'Starting…' : '↺ Retake Test'}
          </button>
          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-5 py-3 bg-white border border-[#000000]/20 hover:border-[#253900] text-[#000000] font-bold rounded-xl transition-colors shadow-sm"
          >
            ← Dashboard
          </Link>
          <Link
            to="/history"
            className="flex items-center gap-2 px-5 py-3 bg-white border border-[#000000]/20 hover:border-[#253900] text-[#000000] font-semibold rounded-xl transition-colors shadow-sm"
          >
            History
          </Link>
        </div>

        {/* Per-question breakdown */}
        <h2 className="text-xl font-black text-[#000000] mb-4 tracking-tight">Question Breakdown</h2>
        <div className="space-y-3">
          {answers.map((item, i) => (
            <AnswerCard key={item.question_id} item={item} index={i} />
          ))}
        </div>
      </div>
    </div>
  );
}
