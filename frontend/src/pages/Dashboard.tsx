import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { getPapers } from '../api/papers';
import type { Paper, PaperStatus } from '../types';
import SkeletonCards from '../components/SkeletonCard';

const STATUS_CONFIG: Record<PaperStatus, { label: string; classes: string }> = {
  uploaded: { label: 'Uploaded', classes: 'bg-gray-200 text-gray-800' },
  uploading: { label: 'Uploading', classes: 'bg-gray-200 text-gray-800' },
  processing: { label: 'Processing', classes: 'bg-[#253900]/15 text-[#253900]' },
  needs_review: { label: 'Ready', classes: 'bg-[#08CB00]/20 text-[#253900]' },
  ready: { label: 'Ready', classes: 'bg-[#08CB00]/20 text-[#253900]' },
  failed: { label: 'Failed', classes: 'bg-red-100 text-red-600' },
  archived: { label: 'Archived', classes: 'bg-gray-200 text-gray-500' },
};

function StatusBadge({ status }: { status: PaperStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.uploaded;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${cfg.classes}`}>
      {status === 'processing' && (
        <svg className="w-3 h-3 mr-1 animate-spin text-[#253900]" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {cfg.label}
    </span>
  );
}

function PaperCard({ paper }: { paper: Paper }) {
  const navigate = useNavigate();
  const date = new Date(paper.created_at).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });

  return (
    <div className="bg-white/80 backdrop-blur border border-[#000000]/10 rounded-2xl p-5 hover:shadow-md transition-shadow flex flex-col gap-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h2 className="font-bold text-[#000000] text-base truncate">{paper.title}</h2>
          <p className="text-xs text-[#555555] mt-1">{date}</p>
        </div>
        <StatusBadge status={paper.status} />
      </div>

      <div className="text-sm text-[#555555]">
        {paper.question_count > 0 ? (
          <span className="font-semibold text-[#000000]">{paper.question_count}</span>
        ) : (
          <span className="text-[#555555]/60">—</span>
        )}{' '}
        question{paper.question_count !== 1 ? 's' : ''}
      </div>

      <div className="flex gap-2 mt-auto">
        {(paper.status === 'ready' || paper.status === 'needs_review') ? (
          <>
            <button
              onClick={() => navigate(`/papers/${paper.id}/sets`)}
              className="flex-1 py-2 px-3 bg-[#08CB00] hover:bg-[#07b000] text-[#000000] text-sm font-bold rounded-xl transition-colors"
            >
              Start Test
            </button>
            <Link
              to={`/papers/${paper.id}/review`}
              className="flex-1 py-2 px-3 border border-[#000000]/20 hover:border-[#253900] text-[#000000] text-sm font-semibold rounded-xl transition-colors text-center"
            >
              View Questions
            </Link>
          </>
        ) : paper.status === 'failed' ? (
          <span className="text-sm text-red-500 font-medium">Processing failed</span>
        ) : (
          <span className="text-sm text-[#555555]">
            {paper.status === 'processing' ? 'Processing your paper…' : 'Waiting to process'}
          </span>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchPapers = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await getPapers();
      setPapers(data);
    } catch {
      toast.error('Failed to load papers.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPapers();
  }, []);

  // Auto-poll while any paper is processing
  useEffect(() => {
    const hasProcessing = papers.some(
      (p) => p.status === 'processing' || p.status === 'uploaded' || p.status === 'uploading'
    );
    if (!hasProcessing) return;
    const timer = setInterval(() => fetchPapers(true), 5000);
    return () => clearInterval(timer);
  }, [papers]);

  return (
    <div className="min-h-screen bg-[#EEEEEE] px-4 py-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-black text-[#000000] tracking-tight">My Papers</h1>
            <p className="text-[#555555] mt-1">Upload exam papers and take timed mock tests</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchPapers(true)}
              disabled={refreshing}
              className="p-2.5 border border-[#000000]/20 rounded-xl hover:border-[#253900] transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <svg
                className={`w-4 h-4 text-[#000000] ${refreshing ? 'animate-spin' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#08CB00] hover:bg-[#07b000] text-[#000000] font-bold rounded-xl transition-colors text-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Upload Paper
            </Link>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <SkeletonCards count={3} />
        ) : papers.length === 0 ? (
          <div className="text-center py-24">
            <div className="w-20 h-20 mx-auto mb-5 bg-[#000000]/5 rounded-3xl flex items-center justify-center">
              <svg className="w-10 h-10 text-[#555555]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-[#000000]">No papers yet</h2>
            <p className="text-[#555555] mt-2 mb-6">Upload your first exam paper to get started</p>
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 px-5 py-3 bg-[#08CB00] text-[#000000] font-bold rounded-xl hover:bg-[#07b000] transition-colors"
            >
              Upload Paper
            </Link>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {papers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
