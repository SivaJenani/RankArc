interface Props {
  total: number;
  answers: Record<number, number | null>; // questionId -> optionId | null
  questionIds: number[];
  currentIndex: number;
  onJump: (index: number) => void;
}

export default function QuestionPalette({ total, answers, questionIds, currentIndex, onJump }: Props) {
  return (
    <div className="bg-card/90 rounded-2xl p-4 border border-fg/10 shadow-sm">
      <h3 className="text-xs font-bold text-deeptext uppercase tracking-wider mb-3">
        Question Palette
      </h3>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1.5 mb-4 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-accent inline-block" /> Answered
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded border-2 border-fg/30 inline-block" /> Not visited
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded border-2 border-accent bg-deep inline-block" /> Current
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
                  ? 'ring-2 ring-accent ring-offset-1 bg-deep text-accent'
                  : answered
                  ? 'bg-accent text-onaccent'
                  : 'border-2 border-fg/15 text-muted hover:border-accent hover:text-fg'
                }
              `}
            >
              {i + 1}
            </button>
          );
        })}
      </div>

      {/* Stats */}
      <div className="mt-4 pt-3 border-t border-fg/10 grid grid-cols-2 gap-2 text-xs">
        <div className="text-center">
          <div className="font-bold text-accent text-base">
            {Object.values(answers).filter((v) => v !== null).length}
          </div>
          <div className="text-muted">Answered</div>
        </div>
        <div className="text-center">
          <div className="font-bold text-fg text-base">
            {total - Object.values(answers).filter((v) => v !== null).length}
          </div>
          <div className="text-muted">Remaining</div>
        </div>
      </div>
    </div>
  );
}
