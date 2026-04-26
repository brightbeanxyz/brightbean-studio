import { cn } from "@/lib/utils";

interface GaugeProps {
  value: number; // 0-100
  label?: string;
}

export function Gauge({ value, label }: GaugeProps) {
  const radius = 60;
  const stroke = 12;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  // Dashboard gauge needs to be an arc (half circle)
  const strokeDashoffset = circumference - (value / 100) * (circumference / 2);

  const getColor = (v: number) => {
    if (v >= 80) return "text-accent-emerald";
    if (v >= 60) return "text-yellow-500";
    return "text-red-500";
  };

  return (
    <div className="relative flex flex-col items-center justify-center">
      <div className="relative w-40 h-24 overflow-hidden flex items-end justify-center">
        <svg
          height={radius * 2}
          width={radius * 2}
          className="absolute top-0 rotate-180"
        >
          <circle
            stroke="currentColor"
            className="text-white/5"
            fill="transparent"
            strokeWidth={stroke}
            strokeDasharray={`${circumference / 2} ${circumference}`}
            r={normalizedRadius}
            cx={radius}
            cy={radius}
            strokeLinecap="round"
          />
          <circle
            stroke="currentColor"
            className={cn(
              getColor(value),
              "transition-all duration-1000 ease-out",
            )}
            fill="transparent"
            strokeWidth={stroke}
            strokeDasharray={`${circumference / 2} ${circumference}`}
            style={{ strokeDashoffset }}
            r={normalizedRadius}
            cx={radius}
            cy={radius}
            strokeLinecap="round"
          />
        </svg>
        <div className="text-center pb-2 z-10 w-full flex flex-col items-center">
          <span
            className={cn(
              "text-4xl font-bold tracking-tighter drop-shadow-lg",
              getColor(value),
            )}
          >
            {value}
          </span>
        </div>
      </div>
      {label && (
        <span className="text-xs uppercase tracking-wider font-semibold text-text-tertiary mt-2">
          {label}
        </span>
      )}
    </div>
  );
}
