import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import UploadZone from '../components/UploadZone';
import { uploadPaper, getPaperStatus } from '../api/papers';

const STUCK_TIMEOUT_MS = 45_000; // 45s without progress = stuck

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loadedBytes, setLoadedBytes] = useState(0);
  const [totalBytes, setTotalBytes] = useState(0);

  const [paperId, setPaperId] = useState<number | null>(null);
  const [pollingStatus, setPollingStatus] = useState<string | null>(null);
  const [processingProgress, setProcessingProgress] = useState(10);
  const [processingStep, setProcessingStep] = useState('Initializing paper parser…');
  const [stuckError, setStuckError] = useState<string | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastProgressRef = useRef<number>(0);
  const lastProgressTimeRef = useRef<number>(Date.now());
  const navigate = useNavigate();

  const resetToUploadForm = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    setPaperId(null);
    setPollingStatus(null);
    setProcessingProgress(10);
    setProcessingStep('Initializing paper parser…');
    setStuckError(null);
    setUploadProgress(0);
    setFile(null);
    setTitle('');
  }, []);

  // Poll for status after upload
  useEffect(() => {
    if (!paperId) return;

    lastProgressRef.current = 0;
    lastProgressTimeRef.current = Date.now();
    setStuckError(null);

    intervalRef.current = setInterval(async () => {
      try {
        const res = await getPaperStatus(paperId);
        setPollingStatus(res.status);

        const newProgress = typeof res.progress === 'number' ? res.progress : 0;

        // Track progress changes to detect stuck state
        if (newProgress > lastProgressRef.current) {
          lastProgressRef.current = newProgress;
          lastProgressTimeRef.current = Date.now();
        } else if (Date.now() - lastProgressTimeRef.current > STUCK_TIMEOUT_MS) {
          // No progress for 45s — something is wrong
          clearInterval(intervalRef.current!);
          setStuckError('Processing seems stuck. The server may have restarted. Please try uploading again.');
          setPollingStatus('failed');
          return;
        }

        setProcessingProgress(newProgress);
        if (res.step) setProcessingStep(res.step);

        if (res.status === 'ready' || res.status === 'needs_review') {
          clearInterval(intervalRef.current!);
          setProcessingProgress(100);
          toast.success('Paper is ready!');
          navigate(`/papers/${paperId}/sets`);
        } else if (res.status === 'failed') {
          clearInterval(intervalRef.current!);
          const errMsg = res.step?.includes('restart')
            ? res.step
            : 'Processing failed. Please try uploading again.';
          setStuckError(errMsg);
          toast.error(errMsg);
        }
      } catch {
        // silent poll error – network blip, keep trying
      }
    }, 1500);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [paperId, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      toast.error('Please select a file first.');
      return;
    }
    if (!title.trim()) {
      toast.error('Please enter a title for this paper.');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setLoadedBytes(0);
    setTotalBytes(file.size);
    setStuckError(null);

    try {
      const paper = await uploadPaper(
        file,
        title.trim(),
        (pct, loaded, total) => {
          setUploadProgress(pct);
          setLoadedBytes(loaded);
          setTotalBytes(total);
        }
      );
      setUploadProgress(100);
      toast.success('File uploaded! Processing your paper…');
      setPaperId(paper.id);
      setPollingStatus('processing');
      setProcessingProgress(10);
      setProcessingStep('Extracting document text…');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Upload failed. Try again.';
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  };

  if (pollingStatus) {
    const isFailed = pollingStatus === 'failed' || !!stuckError;

    return (
      <div className="min-h-screen bg-page flex items-center justify-center px-4">
        <div className="text-center max-w-md w-full">
          <div className={`w-20 h-20 mx-auto mb-6 bg-nav rounded-3xl flex items-center justify-center border border-deeptext shadow-xl`}>
            {isFailed ? (
              <svg className="w-10 h-10 text-red-500" fill="none" viewBox="0 0 24 24">
                <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="w-10 h-10 text-accent animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
          </div>

          <h2 className="text-2xl font-black text-fg">
            {isFailed ? 'Processing Failed' : 'Processing Exam Paper…'}
          </h2>
          <p className="text-muted mt-1 text-sm font-medium">
            {isFailed
              ? 'Something went wrong during processing.'
              : 'Extracting exam sections, questions, and options'}
          </p>

          {/* Progress card */}
          <div className="mt-6 bg-card/95 border border-fg/10 rounded-3xl p-6 shadow-xl space-y-4">
            {isFailed ? (
              <>
                <p className="text-sm text-red-600 font-semibold text-left leading-relaxed">
                  {stuckError || 'Processing failed. Please try uploading again.'}
                </p>
                <button
                  onClick={resetToUploadForm}
                  className="w-full py-3 bg-accent hover:bg-accenth text-onaccent font-black rounded-xl transition-all shadow-md"
                >
                  ← Try Again
                </button>
              </>
            ) : (
              <>
                <div className="flex justify-between items-center gap-2">
                  <span className="text-xs font-bold text-fg text-left line-clamp-1 flex-1">
                    {processingStep}
                  </span>
                  <span className="text-xl font-black text-accent shrink-0">
                    {processingProgress}%
                  </span>
                </div>

                <div className="h-3.5 bg-nav/10 rounded-full overflow-hidden p-0.5 border border-fg/5">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${processingProgress}%` }}
                  />
                </div>

                <div className="flex justify-between items-center text-[11px] text-muted font-semibold">
                  <span className="capitalize">Status: {pollingStatus}</span>
                  <span>{processingProgress}% complete</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-page px-4 py-8">
      <div className="max-w-xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-black text-fg tracking-tight">Upload Paper</h1>
          <p className="text-muted mt-1 font-medium">Upload a PDF or DOCX of your exam paper</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-card/80 backdrop-blur border border-fg/10 rounded-3xl p-6 shadow-sm space-y-6">
          {/* Title */}
          <div>
            <label className="block text-sm font-bold text-fg mb-1.5">
              Paper Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. SSC CGL 2026 — Combined Papers"
              className="w-full px-4 py-3 rounded-xl border border-fg/20 bg-card focus:outline-none focus:ring-2 focus:ring-accent text-fg placeholder-muted/50 font-medium"
              disabled={uploading}
            />
          </div>

          {/* Upload Zone */}
          <div>
            <label className="block text-sm font-bold text-fg mb-1.5">
              File
            </label>
            <UploadZone
              onFileSelect={(selected) => {
                setFile(selected);
                if (!title) {
                  const rawName = selected.name.replace(/\.[^/.]+$/, '');
                  setTitle(rawName);
                }
              }}
              uploading={uploading}
              progress={uploadProgress}
              loadedBytes={loadedBytes}
              totalBytes={totalBytes}
            />
          </div>

          <button
            type="submit"
            disabled={uploading || !file}
            className="w-full py-3.5 bg-accent hover:bg-accenth text-onaccent font-black rounded-xl transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? (
              <span className="inline-flex items-center gap-2 justify-center">
                <svg className="w-4 h-4 animate-spin text-fg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Uploading ({uploadProgress}%)…
              </span>
            ) : (
              'Upload & Process'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
