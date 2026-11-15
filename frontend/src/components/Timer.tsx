interface Props {
  timeLeft: number; // seconds
}

function pad(n: number) {
  return String(n).padStart(2, '0');
}

export default function Timer({ timeLeft }: Props) {
  const h = Math.floor(timeLeft / 3600);
  const m = Math.floor((timeLeft % 3600) / 60);
  const s = timeLeft % 60;
  const isWarning = timeLeft <= 300; // 5 minutes

  return (
    <div
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl font-mono font-bold text-lg border-2 transition-colors ${
        isWarning
          ? 'bg-red-50 border-red-500 text-red-600 animate-pulse'
          : 'bg-[#000000] border-[#253900] text-[#08CB00]'
      }`}
    >
      <svg className="w-4 h-4 shrink-0 text-[#08CB00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" strokeWidth={1.5} />
        <path strokeLinecap="round" strokeWidth={1.5} d="M12 6v6l4 2" />
      </svg>
      {pad(h)}:{pad(m)}:{pad(s)}
    </div>
  );
}
