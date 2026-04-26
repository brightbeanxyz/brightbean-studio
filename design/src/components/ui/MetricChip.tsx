import { cn } from "@/lib/utils";

interface MetricChipProps {
  value: string | number;
  label?: string;
  trend?: "up" | "down" | "neutral";
  variant?: "default" | "success" | "warning" | "brand";
  size?: "sm" | "md";
  className?: string;
}

export function MetricChip({
  value,
  label,
  trend,
  variant = "default",
  size = "md",
  className,
}: MetricChipProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 font-mono rounded border",
        size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
        variant === "success"
          ? "bg-accent-emerald/10 text-accent-emerald border-accent-emerald/20"
          : variant === "warning"
            ? "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
            : variant === "brand"
              ? "bg-accent-blue/10 text-accent-blue border-accent-blue/20"
              : "bg-obsidian-950 text-text-primary border-white/10",
        className,
      )}
    >
      {label && (
        <span className="text-text-tertiary mr-1 font-sans font-medium uppercase tracking-wider">
          {label}
        </span>
      )}
      <span className="font-semibold">{value}</span>
      {trend === "up" && <span className="text-accent-emerald">↑</span>}
      {trend === "down" && <span className="text-red-400">↓</span>}
    </div>
  );
}
