import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { getPaperMeta } from '../api/papers';
import { startAttempt } from '../api/attempts';
import { useTestStore } from '../store/testStore';
import type { PaperMeta } from '../types';

function formatDuration(minutes: number): string {
  if (minutes >= 60) {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m > 0 ? `${h}h ${m}m (${minutes} mins)` : `${h} Hour (${minutes} mins)`;
  }
  return `${minutes} minutes`;
}

export default function PaperSetPicker() {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  const { initTest } = useTestStore();

  const [meta, setMeta] = useState<PaperMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);

  const numId = Number(paperId);

  useEffect(() => {
    if (!numId) return;
    getPaperMeta(numId)
      .then(setMeta)
      .catch(() => toast.error('Failed to load paper info.'))
      .finally(() => setLoading(false));
  }, [numId]);

  const handleStartSet = async (setLabel: string) => {
    setStarting(setLabel);
    try {
      const { attempt_id, questions, duration_seconds } = await startAttempt(numId, setLabel);
      initTest(attempt_id, questions, duration_seconds || questions.length * 60);
      navigate(`/test/${attempt_id}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to start test.');
      setStarting(null);
    }
  };

  const handleReview = () => navigate(`/papers/${numId}/review`);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#EEEEEE] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-[#08CB00]/20 flex items-center justify-center animate-pulse">
            <svg className="w-8 h-8 text-[#253900]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p className="text-[#000000] font-bold">Analyzing exam paper and shifts…</p>
        </div>
      </div>
    );
  }

  if (!meta) {
    return (
      <div className="min-h-screen bg-[#EEEEEE] flex items-center justify-center">
        <div className="text-center bg-white p-8 rounded-3xl border border-[#000000]/10 max-w-sm">
          <p className="text-[#000000] font-bold">Could not load paper info.</p>
          <button
            onClick={() => navigate('/upload')}
            className="mt-4 px-4 py-2 bg-[#08CB00] text-[#000000] font-bold rounded-xl text-sm"
          >
            Back to Upload
          </button>
        </div>
      </div>
    );
  }

  const paperSetsCount = meta.paper_sets?.length || 1;
  const categories = meta.categories || [];

  return (
    <div className="min-h-screen bg-[#EEEEEE] text-[#000000] px-4 py-10 font-sans">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Paper title & banner */}
        <div className="bg-[#000000] text-[#EEEEEE] rounded-3xl p-6 md:p-8 border-2 border-[#253900] shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-[#08CB00]/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#253900] border border-[#08CB00]/40 text-[#08CB00] text-xs font-black uppercase tracking-wider">
                <span className="w-2 h-2 rounded-full bg-[#08CB00] animate-ping" />
                Exam Paper Identified
              </div>
              <h1 className="text-2xl md:text-3xl font-black text-[#EEEEEE] tracking-tight">
                {meta.exam_title || meta.title}
              </h1>
              <p className="text-sm text-[#EEEEEE]/70 font-medium">
                Multiple paper shifts detected in uploaded document.
              </p>
            </div>

            {/* Stats badges */}
            <div className="flex flex-wrap items-center gap-3">
              {meta.duration_minutes && (
                <div className="bg-[#253900]/80 border border-[#08CB00]/40 rounded-2xl px-4 py-3 flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-[#08CB00] flex items-center justify-center shrink-0">
                    <svg className="w-5 h-5 text-[#000000]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#08CB00] font-black uppercase tracking-wider">Exam Duration</p>
                    <p className="text-sm font-black text-white">{formatDuration(meta.duration_minutes)}</p>
                  </div>
                </div>
              )}

              <div className="bg-[#253900]/80 border border-[#08CB00]/40 rounded-2xl px-4 py-3 flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#08CB00] flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-[#000000]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-[10px] text-[#08CB00] font-black uppercase tracking-wider">Available Shifts</p>
                  <p className="text-sm font-black text-white">{paperSetsCount} Paper Sets</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 1. Category Topics & Distribution Summary Table */}
        {categories.length > 0 && (
          <div className="bg-white rounded-3xl p-6 md:p-8 border border-[#000000]/10 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-black text-[#000000] tracking-tight flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#08CB00]" />
                  1. Topic Categories & Question Distribution
                </h2>
                <p className="text-xs text-[#555555] mt-0.5">
                  Summarized section-wise structure across all papers in this document.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-[#000000]/10">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-[#000000] text-[#EEEEEE]">
                    <th className="py-3.5 px-4 font-black text-xs uppercase tracking-wider">Category Title</th>
                    <th className="py-3.5 px-4 font-black text-xs uppercase tracking-wider text-center">Question Numbers</th>
                    <th className="py-3.5 px-4 font-black text-xs uppercase tracking-wider text-center">Per Paper</th>
                    <th className="py-3.5 px-4 font-black text-xs uppercase tracking-wider text-right text-[#08CB00]">
                      Total ({paperSetsCount} Papers)
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#000000]/5 font-medium">
                  {categories.map((cat, idx) => (
                    <tr key={idx} className="hover:bg-[#08CB00]/5 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-[#000000] flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-[#253900]/10 text-[#253900] text-xs font-black flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        {cat.name}
                      </td>
                      <td className="py-3.5 px-4 text-center font-semibold text-[#555555]">
                        {cat.q_start}–{cat.q_end}
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold text-[#000000]">
                        {cat.count}
                      </td>
                      <td className="py-3.5 px-4 text-right font-black text-[#253900]">
                        {cat.count * paperSetsCount}
                      </td>
                    </tr>
                  ))}
                  {/* Total Row */}
                  <tr className="bg-[#253900] text-white font-black text-sm">
                    <td className="py-4 px-4 text-[#08CB00] font-black uppercase tracking-wider">
                      Total
                    </td>
                    <td className="py-4 px-4 text-center text-white">
                      1–{categories.reduce((acc, c) => acc + c.count, 0)}
                    </td>
                    <td className="py-4 px-4 text-center text-white font-black">
                      {categories.reduce((acc, c) => acc + c.count, 0)}
                    </td>
                    <td className="py-4 px-4 text-right text-[#08CB00] font-black text-base">
                      {categories.reduce((acc, c) => acc + c.count, 0) * paperSetsCount}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 2. Exam Papers Identified & Shift Selection */}
        <div className="bg-white rounded-3xl p-6 md:p-8 border border-[#000000]/10 shadow-lg space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-2 border-b border-[#000000]/10">
            <div>
              <h2 className="text-lg font-black text-[#000000] tracking-tight flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#08CB00]" />
                2. Exam Papers Identified ({paperSetsCount} Shifts)
              </h2>
              <p className="text-sm font-bold text-[#253900] mt-1">
                Which exam shift would you like to take as your mock test?
              </p>
            </div>
            {meta.duration_minutes && (
              <span className="text-xs font-bold text-[#555555] bg-[#EEEEEE] px-3 py-1.5 rounded-xl border border-[#000000]/10">
                ⏱ {meta.duration_minutes} Mins Countdown Per Attempt
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            {meta.paper_sets.map((ps, i) => (
              <div
                key={i}
                className="flex flex-col justify-between p-5 rounded-2xl border-2 border-[#000000]/10 bg-[#EEEEEE]/50 hover:border-[#08CB00] hover:bg-[#08CB00]/5 transition-all shadow-sm group"
              >
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-[#000000] text-[#08CB00] font-black flex items-center justify-center text-sm shadow-md shrink-0">
                      {i + 1}
                    </div>
                    <div>
                      <p className="font-black text-[#000000] text-base leading-snug group-hover:text-[#253900]">
                        {ps.label}
                      </p>
                      <p className="text-xs font-semibold text-[#555555] mt-0.5">
                        {ps.q_count || 100} Questions · 4 Sections
                      </p>
                    </div>
                  </div>
                  <span className="text-[11px] font-black text-[#253900] bg-[#08CB00]/20 px-2.5 py-1 rounded-full border border-[#08CB00]/40 shrink-0">
                    Shift {i + 1}
                  </span>
                </div>

                <div className="pt-2 border-t border-[#000000]/5 flex items-center justify-between">
                  <span className="text-xs text-[#555555] font-semibold">
                    {meta.duration_minutes ? `⏱ ${meta.duration_minutes} min test` : 'Untimed'}
                  </span>
                  <button
                    onClick={() => handleStartSet(ps.label)}
                    disabled={starting !== null}
                    className="px-5 py-2.5 bg-[#08CB00] hover:bg-[#07b000] text-[#000000] font-black text-sm rounded-xl transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-wait flex items-center gap-2"
                  >
                    {starting === ps.label ? (
                      <>
                        <svg className="w-4 h-4 animate-spin text-[#000000]" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Loading Shift…
                      </>
                    ) : (
                      <>
                        Take Mock Test
                        <span className="text-lg leading-none">→</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom utility navigation */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
          <button
            onClick={handleReview}
            className="px-5 py-3 border-2 border-[#000000]/20 hover:border-[#253900] text-[#000000] font-bold rounded-2xl transition-colors text-sm bg-white shadow-sm"
          >
            Review All Questions in Paper
          </button>
          <button
            onClick={() => navigate('/upload')}
            className="px-5 py-3 border border-[#000000]/15 hover:border-[#000000]/30 text-[#555555] font-semibold rounded-2xl transition-colors text-sm bg-white shadow-sm"
          >
            Upload Another Paper
          </button>
        </div>

      </div>
    </div>
  );
}
