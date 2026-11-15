interface Props {
  total: number;
  answers: Record<number, number | null>; // questionId -> optionId | null
  questionIds: number[];
  currentIndex: number;
  onJump: (index: number) => void;
}

export default function QuestionPalette({ total, answers, questionIds, currentIndex, onJump }: Props) {
  return (
    <div className="bg-white/90 rounded-2xl p-4 border border-[#000000]/10 shadow-sm">
      <h3 className="text-xs font-bold text-[#253900] uppercase tracking-wider mb-3">
        Question Palette
      </h3>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1.5 mb-4 text-xs text-[#555555]">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-[#08CB00] inline-block" /> Answered
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded border-2 border-[#000000]/30 inline-block" /> Not visited
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded border-2 border-[#08CB00] bg-[#253900] inline-block" /> Current
        </span>
      </div>

      <div className="grid grid-cols-5 gap-1.5">
        {Array.from({ length: total }).map((_, i) => {
          const qId = questionIds[i];
          const answered = qId !== undefined && answers[qId] !== null && answers[qId] !== undefined;
          const isCurrent = i === currentIndex;

          return (
            <button
              key={i}
              onClick={() => onJump(i)}
              className={`
                w-9 h-9 text-xs font-bold rounded-lg transition-all
                ${isCurrent
                  ? 'ring-2 ring-[#08CB00] ring-offset-1 bg-[#253900] text-[#08CB00]'
                  : answered
                  ? 'bg-[#08CB00] text-[#000000]'
                  : 'border-2 border-[#000000]/15 text-[#555555] hover:border-[#08CB00] hover:text-[#000000]'
                }
              `}
            >
              {i + 1}
            </button>
          );
        })}
      </div>

      {/* Stats */}
      <div className="mt-4 pt-3 border-t border-[#000000]/10 grid grid-cols-2 gap-2 text-xs">
        <div className="text-center">
          <div className="font-bold text-[#08CB00] text-base">
            {Object.values(answers).filter((v) => v !== null).length}
          </div>
          <div className="text-[#555555]">Answered</div>
        </div>
        <div className="text-center">
          <div className="font-bold text-[#000000] text-base">
            {total - Object.values(answers).filter((v) => v !== null).length}
          </div>
          <div className="text-[#555555]">Remaining</div>
        </div>
      </div>
    </div>
  );
}
