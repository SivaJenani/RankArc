import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

interface KeyPreview { entries: { number: number; label: string; question_text: string }[]; errors: string[]; fingerprint: string; notice: string; question_count: number }

export default function AnswerKeyUpload({ paperId }: { paperId: number }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<KeyPreview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const readKey = async () => {
    if (!file) return;
    setBusy(true); setError(''); setPreview(null); setConfirmed(false);
    try {
      const data = new FormData(); data.append('file', file);
      const response = await client.post<KeyPreview>(`/api/papers/${paperId}/answer-key/preview`, data);
      setPreview(response.data);
    } catch (e: any) { setError(typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : 'Could not read this answer key. Try a clear numbered text key.'); }
    finally { setBusy(false); }
  };
  const apply = async () => {
    if (!preview || !confirmed || preview.errors.length) return;
    setBusy(true); setError('');
    try {
      const { data } = await client.post(`/api/papers/${paperId}/answer-key/apply`, { entries: preview.entries.map(({ number, label }) => ({ number, label })), fingerprint: preview.fingerprint, confirmed: true });
      setPreview(null); setConfirmed(false); setFile(null);
      navigate(`/papers/${data.paper_id}/review`);
    } catch (e: any) { setError(typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : 'Could not apply the key. Upload and review it again.'); }
    finally { setBusy(false); }
  };
  return <section className="bg-card border border-fg/10 rounded-2xl p-5 mb-6 space-y-3 text-fg" aria-label="Separate answer key">
    <h2 className="text-lg font-bold">Upload answer key</h2>
    <p className="text-sm text-muted">No answers in the paper? Upload your own key. Use question-number and letter pairs, such as "1 B". PDF, DOCX, TXT, CSV, PNG or JPG; max 5 MB. Scanned keys use local OCR and need careful review. Multiple sets with repeated numbers must be split first.</p>
    <input aria-label="Answer key file" type="file" accept=".pdf,.docx,.txt,.csv,.png,.jpg,.jpeg" className="block w-full min-w-0 text-sm" disabled={busy} onChange={e => { setFile(e.target.files?.[0] || null); setPreview(null); setConfirmed(false); setError(''); }} />
    <button type="button" disabled={!file || busy} onClick={readKey} className="px-4 py-2 bg-accent text-onaccent font-bold rounded-xl disabled:opacity-50">{busy ? 'Working…' : 'Read key & review mapping'}</button>
    {error && <p role="alert" className="text-red-500 text-sm break-words">{error}</p>}
    {preview && <div className="space-y-3">
      <p className="text-sm font-semibold">{preview.notice}</p>
      <p className="text-sm">{preview.entries.length} key entries / {preview.question_count} questions</p>
      {!!preview.errors.length && <div role="alert" className="text-red-500 text-sm space-y-1">{preview.errors.map((e, i) => <p key={i}>{e}</p>)}<p>Correct the key file and upload it again. No answers have been changed.</p></div>}
      <div className="max-h-80 overflow-auto border border-fg/10 rounded-xl">
        <table className="w-full text-sm text-left"><thead><tr className="bg-card"><th className="p-2">Question</th><th className="p-2">Key answer</th></tr></thead><tbody>{preview.entries.map((e, i) => <tr key={i} className="border-t border-fg/10"><td className="p-2">{e.number}</td><td className="p-2 font-bold">{e.label}</td></tr>)}</tbody></table>
      </div>
      <label className="flex items-start gap-3 text-sm"><input type="checkbox" className="mt-1 shrink-0" checked={confirmed} disabled={busy || !!preview.errors.length} onChange={e => setConfirmed(e.target.checked)} /><span>I checked every question number and answer against my source key. Create a separate keyed copy. Keep the original paper and past results unchanged.</span></label>
      <button type="button" onClick={apply} disabled={busy || !confirmed || !!preview.errors.length} className="px-4 py-2 bg-accent text-onaccent font-bold rounded-xl disabled:opacity-50">Confirm mapping & create keyed copy</button>
    </div>}
  </section>;
}
