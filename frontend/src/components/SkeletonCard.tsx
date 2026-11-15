interface Props {
  count?: number;
}

function SkeletonCard() {
  return (
    <div className="bg-white/70 rounded-2xl p-5 border border-[#000000]/10 animate-pulse">
      <div className="flex items-start justify-between mb-4">
        <div className="space-y-2 flex-1">
          <div className="h-5 bg-[#000000]/10 rounded-lg w-3/4" />
          <div className="h-3.5 bg-[#000000]/10 rounded w-1/3" />
        </div>
        <div className="h-6 w-20 bg-[#000000]/10 rounded-full ml-4" />
      </div>
      <div className="flex gap-3 mt-6">
        <div className="h-9 bg-[#000000]/10 rounded-lg flex-1" />
        <div className="h-9 bg-[#000000]/10 rounded-lg flex-1" />
      </div>
    </div>
  );
}

export default function SkeletonCards({ count = 3 }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
