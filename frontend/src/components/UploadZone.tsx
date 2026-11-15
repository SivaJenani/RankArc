import { useCallback, useRef, useState } from 'react';

interface Props {
  onFileSelect: (file: File) => void;
  uploading?: boolean;
  progress?: number;
  loadedBytes?: number;
  totalBytes?: number;
}

const MAX_SIZE_MB = 100;
const ALLOWED_TYPES = [
  'application/pdf',
  'application/x-pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
];
const ALLOWED_EXTS = ['.pdf', '.docx', '.doc'];

export default function UploadZone({
  onFileSelect,
  uploading = false,
  progress = 0,
  loadedBytes = 0,
  totalBytes = 0,
}: Props) {
  const [dragging, setDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (!ext || !ALLOWED_EXTS.includes(`.${ext}`)) {
        return 'Only PDF and DOCX files are allowed.';
      }
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File size must be under ${MAX_SIZE_MB}MB.`;
    }
    return null;
  };

  const handleFile = useCallback(
    (file: File) => {
      const err = validate(file);
      if (err) {
        setError(err);
        setSelectedFile(null);
        return;
      }
      setError(null);
      setSelectedFile(file);
      onFileSelect(file);
    },
    [onFileSelect]
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="space-y-3">
      <div
        onClick={() => !uploading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`
          relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all
          ${dragging ? 'border-[#08CB00] bg-[#08CB00]/10' : 'border-[#000000]/25 hover:border-[#08CB00] hover:bg-[#08CB00]/5 bg-white/70'}
          ${uploading ? 'pointer-events-none opacity-70' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={onInputChange}
        />

        {/* Icon */}
        <div className="mx-auto mb-4 w-14 h-14 bg-[#08CB00]/15 rounded-2xl flex items-center justify-center">
          <svg className="w-7 h-7 text-[#253900]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>

        {selectedFile ? (
          <div>
            <p className="font-semibold text-[#000000]">{selectedFile.name}</p>
            <p className="text-sm text-[#555555] mt-1">
              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
            </p>
          </div>
        ) : (
          <div>
            <p className="font-semibold text-[#000000]">Drop your file here</p>
            <p className="text-sm text-[#555555] mt-1">or click to browse</p>
            <p className="text-xs text-[#253900] font-semibold mt-2">PDF or DOCX · Max {MAX_SIZE_MB}MB</p>
          </div>
        )}
      </div>

      {/* Upload progress */}
      {uploading && (
        <div className="space-y-2 mt-3 p-4 rounded-2xl bg-white border border-[#000000]/10 shadow-sm">
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold text-[#000000] flex items-center gap-2">
              <svg className="w-3.5 h-3.5 animate-spin text-[#08CB00]" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {progress >= 100 ? 'Upload complete! Preparing parser…' : 'Uploading to server…'}
            </span>
            <span className="font-black text-[#08CB00] text-sm">{progress}%</span>
          </div>
          <div className="h-2.5 bg-[#000000]/10 rounded-full overflow-hidden p-0.5 border border-[#000000]/5">
            <div
              className="h-full bg-[#08CB00] rounded-full transition-all duration-150 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          {totalBytes > 0 && (
            <div className="flex justify-between text-[11px] text-[#555555] font-semibold">
              <span>{(loadedBytes / (1024 * 1024)).toFixed(2)} MB of {(totalBytes / (1024 * 1024)).toFixed(2)} MB</span>
              <span>{progress}%</span>
            </div>
          )}
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600 font-medium">{error}</p>
      )}
    </div>
  );
}
