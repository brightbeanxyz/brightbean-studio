import { Search, Filter, SlidersHorizontal, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface FilterBarProps {
  onSearch?: (term: string) => void;
  placeholder?: string;
  leftActions?: ReactNode;
  rightActions?: ReactNode;
  className?: string;
  count?: number;
}

export function FilterBar({
  onSearch,
  placeholder = "Tìm kiếm...",
  leftActions,
  rightActions,
  className,
  count,
}: FilterBarProps) {
  return (
    <div
      className={cn(
        "p-4 border-b border-white/5 flex flex-wrap gap-4 items-center justify-between bg-obsidian-900/50 backdrop-blur-md sticky top-0 z-20",
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-text-tertiary group-focus-within:text-accent-blue transition-colors" />
          </div>
          <input
            type="text"
            placeholder={placeholder}
            onChange={(e) => onSearch?.(e.target.value)}
            className="block w-64 md:w-80 pl-9 pr-3 py-2 border border-white/10 rounded-lg bg-obsidian-950/50 text-sm text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent-blue/50 focus:ring-1 focus:ring-accent-blue/50 transition-all shadow-inner"
          />
        </div>

        <button className="flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-sm font-medium transition-colors text-text-secondary hover:text-text-primary">
          <Filter className="w-4 h-4" />
          <span className="hidden sm:inline">Bộ lọc</span>
        </button>

        {leftActions}
      </div>

      <div className="flex items-center gap-3">
        {count !== undefined && (
          <span className="text-xs font-mono text-text-tertiary hidden sm:inline-block border border-white/5 px-2 py-1 rounded bg-obsidian-950">
            {count} kết quả
          </span>
        )}

        {rightActions}

        <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-obsidian-800 border border-white/5 hover:bg-obsidian-700 hover:border-white/10 text-sm font-medium transition-colors">
          <Download className="w-4 h-4" />
          <span className="hidden sm:inline">Xuất dữ liệu</span>
        </button>
      </div>
    </div>
  );
}
