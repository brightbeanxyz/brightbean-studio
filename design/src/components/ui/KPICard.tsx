import React from "react";
import { cn } from "@/lib/utils";
import { TinySparkline } from "../charts/TinySparkline";
import { TrendingUp, TrendingDown, Minus, Info } from "lucide-react";

export type TrendDirection = "up" | "down" | "neutral";

export interface KPICardProps {
  title: string;
  value: string | number;
  delta?: number;
  deltaType?: "percentage" | "absolute";
  trend?: TrendDirection; // If not provided, inferred from delta
  sparklineData?: number[];
  note?: string;
  badge?: {
    text: string;
    color?: "gold" | "blue" | "emerald" | "violet" | "default" | "danger";
  };
  mode?: "default" | "compact";
  isLoading?: boolean;
  className?: string;
}

export function KPICard({
  title,
  value,
  delta,
  deltaType = "percentage",
  trend,
  sparklineData,
  note,
  badge,
  mode = "default",
  isLoading = false,
  className,
}: KPICardProps) {
  const isCompact = mode === "compact";

  // Infer trend from delta if not explicitly provided
  const actualTrend: TrendDirection =
    trend || (delta === undefined ? "neutral" : delta > 0 ? "up" : delta < 0 ? "down" : "neutral");

  const trendConfig = {
    up: {
      color: "text-accent-emerald",
      bg: "bg-accent-emerald/10",
      icon: TrendingUp,
      sign: "+",
    },
    down: {
      color: "text-danger",
      bg: "bg-danger/10",
      icon: TrendingDown,
      sign: "", // Negative numbers already include a minus sign typically, or we handle it
    },
    neutral: {
      color: "text-text-tertiary",
      bg: "bg-white/5",
      icon: Minus,
      sign: "",
    },
  };

  const currentTrend = trendConfig[actualTrend];
  const TrendIcon = currentTrend.icon;

  const formatDelta = (d: number) => {
    const absD = Math.abs(d);
    const suffix = deltaType === "percentage" ? "%" : "";
    const displayNum = deltaType === "percentage" ? absD.toFixed(1) : absD;
    return `${currentTrend.sign}${actualTrend === "down" ? "-" : ""}${displayNum}${suffix}`;
  };

  const badgeColorConfig = {
    gold: "bg-accent-gold/10 text-accent-gold border-accent-gold/20",
    blue: "bg-accent-blue/10 text-accent-blue border-accent-blue/20",
    emerald: "bg-accent-emerald/10 text-accent-emerald border-accent-emerald/20",
    violet: "bg-accent-violet/10 text-accent-violet border-accent-violet/20",
    danger: "bg-danger/10 text-danger border-danger/20",
    default: "bg-white/5 text-text-secondary border-border-default",
  };

  if (isLoading) {
    return (
      <div
        className={cn(
          "ds-card flex flex-col justify-between animate-pulse",
          isCompact ? "p-4" : "p-6",
          className
        )}
      >
        <div className="flex justify-between items-start mb-4">
          <div className="w-1/2 h-4 bg-white/10 rounded-md"></div>
          {badge && <div className="w-12 h-4 bg-white/10 rounded-full"></div>}
        </div>
        <div className="w-2/3 h-8 bg-white/10 rounded-md mb-2"></div>
        {sparklineData && <div className="w-[60px] h-6 bg-white/5 rounded-md self-end mt-2"></div>}
        <div className="w-1/3 h-4 bg-white/5 rounded-md mt-4"></div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "ds-card-interactive group flex flex-col justify-between overflow-hidden relative",
        isCompact ? "p-4" : "p-6 sm:p-5 lg:p-6",
        className
      )}
    >
      {/* Top Header */}
      <div className="flex items-start justify-between mb-2">
        <h4 className={cn(
          "font-medium text-text-secondary tracking-tight line-clamp-1",
          isCompact ? "text-xs" : "text-sm"
        )}>
          {title}
        </h4>
        
        {badge && (
          <span
            className={cn(
              "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border",
              badgeColorConfig[badge.color || "default"]
            )}
          >
            {badge.text}
          </span>
        )}
      </div>

      {/* Main Value & Delta */}
      <div className={cn("flex items-end gap-3", isCompact ? "mb-1" : "mb-3")}>
        <div className={cn(
          "font-mono font-medium text-white tracking-tight leading-none",
          isCompact ? "text-2xl" : "text-3xl md:text-4xl" // tabular-nums applied via CSS/Tailwind usually, or explicitly: tabular-nums
        )}>
          <span className="tabular-nums">{value}</span>
        </div>

        {delta !== undefined && (
          <div
            className={cn(
              "flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-semibold tabular-nums",
              currentTrend.bg,
              currentTrend.color
            )}
          >
            <TrendIcon className="w-3 h-3" strokeWidth={3} />
            {formatDelta(delta)}
          </div>
        )}
      </div>

      {/* Footer Area: Sparkline & Secondary Note */}
      <div className="flex items-end justify-between mt-auto">
        {note && (
          <div className="text-[11px] md:text-xs text-text-tertiary font-medium">
            {note}
          </div>
        )}
        
        {!note && <div />} {/* Spacer if no note but sparkline exists */}

        {sparklineData && sparklineData.length > 0 && (
          <div className={cn("shrink-0", isCompact && "scale-90 origin-bottom-right")}>
             <TinySparkline data={sparklineData} trend={actualTrend} />
          </div>
        )}
      </div>

      {/* Subtle Glow Overlay */}
      <div className={cn(
        "absolute -bottom-10 -right-10 w-32 h-32 blur-3xl opacity-0 group-hover:opacity-10 transition-opacity duration-300 pointer-events-none",
        actualTrend === "up" ? "bg-accent-emerald" : actualTrend === "down" ? "bg-danger" : "bg-white"
      )} />
    </div>
  );
}
