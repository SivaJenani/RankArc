import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { getHistory } from '../api/attempts';
import type { AttemptHistory } from '../types';

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function ScoreBadge({ percentage }: { percentage: number }) {
  const color =
    percentage >= 80 ? 'bg-accent/20 text-deeptext border border-accent/50' :
    percentage >= 50 ? 'bg-yellow-400/20 text-yellow-800 border border-yellow-500/40' :
    'bg-red-400/20 text-red-700 border border-red-500/40';
  return (
    <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-bold ${color}`}>
      {percentage}%
    </span>
  );
}

export default function History() {
  const [history, setHistory] = useState<AttemptHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHistory()
      .then(setHistory)
      .catch(() => toast.error('Failed to load history.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-page px-4 py-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-black text-fg tracking-tight">Test History</h1>
          <p className="text-muted mt-1 font-medium">All your past mock test attempts</p>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-card/60 border border-fg/5 rounded-2xl h-16 animate-pulse" />
            ))}
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-24 bg-card/70 border border-fg/10 rounded-3xl p-8">
            <div className="w-20 h-20 mx-auto mb-5 bg-nav rounded-3xl flex items-center justify-center border border-deeptext">
              <svg className="w-10 h-10 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-fg">No attempts yet</h2>
            <p className="text-muted mt-2 mb-6">Take a mock test to see your history here</p>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-5 py-3 bg-accent text-onaccent font-black rounded-xl hover:bg-accenth transition-colors shadow-md"
            >
              Go to Dashboard
            </Link>
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden sm:block bg-card/80 backdrop-blur border border-fg/10 rounded-2xl overflow-hidden shadow-sm">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-fg/10 bg-nav/5 text-left">
                    <th className="px-5 py-3.5 text-xs font-bold text-deeptext uppercase tracking-wide">Paper</th>
                    <th className="px-5 py-3.5 text-xs font-bold text-deeptext uppercase tracking-wide">Score</th>
                    <th className="px-5 py-3.5 text-xs font-bold text-deeptext uppercase tracking-wide">Result</th>
                    <th className="px-5 py-3.5 text-xs font-bold text-deeptext uppercase tracking-wide">Time Taken</th>
                    <th className="px-5 py-3.5 text-xs font-bold text-deeptext uppercase tracking-wide">Date</th>
                    <th className="px-5 py-3.5 text-xs font-bold text-deeptext uppercase tracking-wide">Status</th>
                    <th className="px-5 py-3.5 text-xs font-bold text-deeptext uppercase tracking-wide"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-fg/5">
                  {history.map((item) => {
                    const pct = Math.round(item.score ?? 0);
                    const correct = Math.round((pct / 100) * item.total_questions);
                    const timeTaken = item.submitted_at && item.started_at
                      ? Math.floor((new Date(item.submitted_at).getTime() - new Date(item.started_at).getTime()) / 1000)
                      : 0;

                    return (
                      <tr key={item.id} className="hover:bg-accent/5 transition-colors">
                        <td className="px-5 py-4">
                          <p className="font-semibold text-fg text-sm truncate max-w-[200px]">
                            {item.paper_title}
                          </p>
                        </td>
                        <td className="px-5 py-4">
                          <span className="font-bold text-fg text-sm">
                            {correct} / {item.total_questions}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <ScoreBadge percentage={pct} />
                        </td>
                        <td className="px-5 py-4">
                          <span className="text-sm text-muted">
                            {timeTaken > 0 ? formatDuration(timeTaken) : '—'}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <span className="text-sm text-muted">
                            {item.submitted_at ? formatDate(item.submitted_at) : formatDate(item.started_at)}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                            item.status === 'completed'
                              ? 'bg-accent/20 text-deeptext border border-accent/40'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-right">
                          {item.status === 'completed' && (
                            <Link
                              to={`/results/${item.id}`}
                              className="text-sm font-black text-deeptext hover:text-accent transition-colors"
                            >
                              View →
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="sm:hidden space-y-3">
              {history.map((item) => {
                const pct = Math.round(item.score ?? 0);
                const correct = Math.round((pct / 100) * item.total_questions);
                const timeTaken = item.submitted_at && item.started_at
                  ? Math.floor((new Date(item.submitted_at).getTime() - new Date(item.started_at).getTime()) / 1000)
                  : 0;
                return (
                  <div key={item.id} className="bg-card/80 backdrop-blur border border-fg/10 rounded-2xl p-4 shadow-sm">
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <p className="font-bold text-fg text-sm flex-1">{item.paper_title}</p>
                      <ScoreBadge percentage={pct} />
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted">
                      <span><strong className="text-fg">{correct}/{item.total_questions}</strong> correct</span>
                      {timeTaken > 0 && <span>{formatDuration(timeTaken)}</span>}
                      <span>{item.submitted_at ? formatDate(item.submitted_at) : formatDate(item.started_at)}</span>
                    </div>
                    {item.status === 'completed' && (
                      <Link
                        to={`/results/${item.id}`}
                        className="inline-block mt-3 text-sm font-black text-deeptext hover:text-accent"
                      >
                        View Result →
                      </Link>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
