import React, { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

type GlowColor = "blue" | "emerald" | "gold" | "violet" | "default";

interface EmptyStateProps {
  icon?: LucideIcon;
  illustration?: ReactNode;
  title: string;
  description: ReactNode;
  action?: ReactNode;
  secondaryAction?: ReactNode;
  glowColor?: GlowColor;
  className?: string;
}

const colorMap = {
  blue: {
    bg: "bg-accent-blue/10",
    border: "border-accent-blue/20",
    icon: "text-accent-blue",
    glow: "shadow-glow-blue",
  },
  emerald: {
    bg: "bg-accent-emerald/10",
    border: "border-accent-emerald/20",
    icon: "text-accent-emerald",
    glow: "shadow-glow-emerald",
  },
  gold: {
    bg: "bg-accent-gold/10",
    border: "border-accent-gold/20",
    icon: "text-accent-gold",
    glow: "shadow-glow-gold",
  },
  violet: {
    bg: "bg-accent-violet/10",
    border: "border-accent-violet/20",
    icon: "text-accent-violet",
    glow: "shadow-glow-violet",
  },
  default: {
    bg: "bg-surface-elevated text-white/5",
    border: "border-border-default",
    icon: "text-text-tertiary",
    glow: "shadow-none",
  },
};

export function EmptyState({
  icon: Icon,
  illustration,
  title,
  description,
  action,
  secondaryAction,
  glowColor = "default",
  className,
}: EmptyStateProps) {
  const colorStyles = colorMap[glowColor];

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center max-w-md mx-auto h-full min-h-[320px]",
        className
      )}
    >
      <div className="relative mb-6">
        {/* Subtle background glow effect if not default */}
        {glowColor !== "default" && (
          <div
            className={cn(
              "absolute inset-0 blur-3xl opacity-30 rounded-full",
              glowColor === "blue" && "bg-accent-blue",
              glowColor === "emerald" && "bg-accent-emerald",
              glowColor === "gold" && "bg-accent-gold",
              glowColor === "violet" && "bg-accent-violet"
            )}
            style={{ transform: "scale(1.5)" }}
          />
        )}
        
        {/* Icon Container */}
        {illustration ? (
          <div className="relative z-10">{illustration}</div>
        ) : Icon ? (
          <div
            className={cn(
              "relative z-10 w-20 h-20 rounded-2xl flex items-center justify-center border backdrop-blur-xl shadow-elevated",
              colorStyles.bg,
              colorStyles.border,
              glowColor !== "default" && colorStyles.glow
            )}
          >
            <div className="absolute inset-x-0 -top-px h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
            <Icon className={cn("w-10 h-10", colorStyles.icon)} strokeWidth={1.5} />
          </div>
        ) : null}
      </div>

      <h3 className="text-[1.25rem] leading-[1.4] font-medium text-text-primary tracking-tight mb-2">
        {title}
      </h3>
      
      <p className="text-sm md:text-[0.875rem] leading-[1.6] text-text-secondary max-w-[360px] mx-auto mb-8">
        {description}
      </p>

      {(action || secondaryAction) && (
        <div className="flex items-center justify-center gap-3 w-full sm:w-auto flex-wrap">
          {action && (
            <div className="shrink-0">{action}</div>
          )}
          {secondaryAction && (
            <div className="shrink-0">{secondaryAction}</div>
          )}
        </div>
      )}
    </div>
  );
}
