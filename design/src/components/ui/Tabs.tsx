import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TabsProps {
  value: string;
  onValueChange: (val: string) => void;
  options: { label: string; value: string; icon?: ReactNode }[];
  className?: string;
}

export function Tabs({ value, onValueChange, options, className }: TabsProps) {
  return (
    <div
      className={cn(
        "flex bg-obsidian-950/50 rounded-xl p-1 border border-white/5 backdrop-blur-md w-fit",
        className,
      )}
    >
      {options.map((option) => {
        const isActive = value === option.value;
        return (
          <button
            key={option.value}
            onClick={() => onValueChange(option.value)}
            className={cn(
              "flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-300",
              isActive
                ? "bg-obsidian-700 text-text-primary shadow-sm"
                : "text-text-secondary hover:text-text-primary hover:bg-white/5",
            )}
          >
            {option.icon && <span className="opacity-70">{option.icon}</span>}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
