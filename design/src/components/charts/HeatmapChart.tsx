import { cn } from "@/lib/utils";

interface HeatmapChartProps {
  data: {
    name: string;
    data: { hour: number; value: number }[];
  }[];
}

export function HeatmapChart({ data }: HeatmapChartProps) {
  // Find max value to normalize colors
  const maxValue = Math.max(1, ...data.flatMap(d => d.data.map(h => h.value)));

  const getColorOpacity = (val: number) => {
    if (val === 0) return 'bg-obsidian-950/40 border-white/5';
    const ratio = val / maxValue;
    if (ratio < 0.2) return 'bg-accent-emerald/20 border-accent-emerald/10';
    if (ratio < 0.5) return 'bg-accent-emerald/40 border-accent-emerald/20';
    if (ratio < 0.8) return 'bg-accent-emerald/70 border-accent-emerald/40';
    return 'bg-accent-emerald border-accent-emerald';
  };

  return (
    <div className="w-full flex flex-col text-xs font-mono">
      <div className="flex mb-1">
         <div className="w-8 shrink-0"></div>
         <div className="flex-1 grid grid-cols-24 gap-1">
            {[0,3,6,9,12,15,18,21].map(h => (
               <div key={h} className="col-span-3 text-text-tertiary text-[10px]">{h}h</div>
            ))}
         </div>
      </div>
      
      <div className="space-y-1">
        {data.map((day, dIdx) => (
          <div key={dIdx} className="flex items-center">
            <div className="w-8 shrink-0 text-text-secondary font-medium text-[10px]">{day.name}</div>
            <div className="flex-1 grid grid-cols-24 gap-0.5">
               {day.data.map((hour, hIdx) => (
                  <div 
                    key={hIdx} 
                    className={cn(
                      "aspect-square rounded-[2px] border transition-colors hover:border-white/50 cursor-crosshair",
                      getColorOpacity(hour.value)
                    )}
                    title={`${day.name} ${hour.hour}h: ${hour.value} tương tác`}
                  />
               ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
