import React from "react";
import { cn } from "@/lib/utils";
import {
  AlertCircle,
  CheckCircle2,
  Info,
  AlertTriangle,
  ArrowRight,
  Activity,
  XCircle,
  Clock,
} from "lucide-react";

export type AlertSeverity = "info" | "success" | "warning" | "danger";
export type AlertVariant = "default" | "compact" | "list";

export interface AlertCardProps extends Omit<
  React.HTMLAttributes<HTMLDivElement>,
  "title"
> {
  title: string;
  description?: string;
  severity?: AlertSeverity;
  variant?: AlertVariant;
  icon?: React.ReactNode;
  time?: string;
  ctaText?: string;
  onCtaClick?: () => void;
}

const severityConfig = {
  info: {
    icon: Info,
    colorClass: "text-accent-blue bg-accent-blue/10 border-accent-blue/20",
    iconColor: "text-accent-blue",
    glow: "shadow-[0_0_12px_rgba(59,130,246,0.15)]",
  },
  success: {
    icon: CheckCircle2,
    colorClass:
      "text-accent-emerald bg-accent-emerald/10 border-accent-emerald/20",
    iconColor: "text-accent-emerald",
    glow: "shadow-[0_0_12px_rgba(16,185,129,0.15)]",
  },
  warning: {
    icon: AlertTriangle,
    colorClass: "text-amber-400 bg-amber-400/10 border-amber-400/20",
    iconColor: "text-amber-400",
    glow: "shadow-[0_0_12px_rgba(251,191,36,0.15)]",
  },
  danger: {
    icon: AlertCircle,
    colorClass: "text-red-400 bg-red-400/10 border-red-400/20",
    iconColor: "text-red-400",
    glow: "shadow-[0_0_12px_rgba(248,113,113,0.15)]",
  },
};

export function AlertCard({
  title,
  description,
  severity = "info",
  variant = "default",
  icon,
  time,
  ctaText,
  onCtaClick,
  className,
  ...props
}: AlertCardProps) {
  const config = severityConfig[severity];
  const Icon = icon ? () => <>{icon}</> : config.icon;

  if (variant === "compact") {
    return (
      <div
        className={cn(
          "flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all cursor-pointer group bg-surface-card hover:bg-surface-elevated/80 border-white/5 hover:border-white/10",
          className,
        )}
        {...props}
      >
        <div
          className={cn(
            "p-1.5 rounded-lg shrink-0",
            config.colorClass,
            config.glow,
          )}
        >
          <Icon className={cn("w-4 h-4", config.iconColor)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-text-primary truncate group-hover:text-white transition-colors">
            {title}
          </div>
        </div>
        {ctaText && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCtaClick?.();
            }}
            className="text-[11px] font-bold uppercase tracking-widest text-text-tertiary group-hover:text-text-primary transition-colors hover:bg-white/5 px-2 py-1 rounded"
          >
            {ctaText}
          </button>
        )}
      </div>
    );
  }

  if (variant === "list") {
    return (
      <div
        className={cn(
          "flex items-start gap-3 py-3 border-b border-white/5 last:border-0 hover:bg-white/[0.02] px-2 -mx-2 transition-colors group cursor-pointer",
          className,
        )}
        {...props}
      >
        <Icon className={cn("w-4 h-4 mt-0.5 shrink-0", config.iconColor)} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-0.5">
            <span className="text-sm font-medium text-text-primary group-hover:text-white transition-colors">
              {title}
            </span>
            {time && (
              <span className="text-xs text-text-tertiary border border-white/5 px-1.5 py-0.5 rounded">
                {time}
              </span>
            )}
          </div>
          {description && (
            <div className="text-sm text-text-secondary leading-snug">
              {description}
            </div>
          )}
          {ctaText && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCtaClick?.();
              }}
              className="mt-2 text-xs font-medium flex items-center gap-1 transition-colors hover:underline"
              style={{
                color: `var(--color-${severity === "warning" ? "amber-400" : severity === "danger" ? "red-400" : severity === "success" ? "emerald-400" : "blue-400"})`,
              }}
            >
              {ctaText} <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // Default variant
  return (
    <div
      className={cn(
        "relative overflow-hidden flex flex-col p-4 rounded-xl border bg-obsidian-950/80 hover:bg-obsidian-900 transition-colors cursor-pointer group shadow-card border-white/5 hover:border-white/10",
        className,
      )}
      {...props}
    >
      <div className="flex items-start gap-3 relative z-10 w-full">
        <div
          className={cn(
            "p-2 rounded-xl shrink-0 transition-transform group-hover:scale-105",
            config.colorClass,
            config.glow,
          )}
        >
          <Icon className={cn("w-5 h-5", config.iconColor)} />
        </div>
        <div className="flex-1 min-w-0 pt-0.5">
          <div className="flex items-start justify-between gap-2 mb-1.5">
            <h4 className="text-sm font-semibold text-text-primary group-hover:text-white transition-colors leading-tight">
              {title}
            </h4>
            {time && (
              <span className="text-[10px] font-mono text-text-tertiary bg-white/5 px-1.5 py-0.5 rounded uppercase">
                {time}
              </span>
            )}
          </div>
          {description && (
            <p className="text-sm text-text-secondary leading-snug pr-4">
              {description}
            </p>
          )}
          {ctaText && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCtaClick?.();
              }}
              className="mt-3 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-text-tertiary group-hover:text-white transition-colors bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg w-fit"
            >
              {ctaText} <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
