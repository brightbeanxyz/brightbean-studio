import { useState, useRef, useEffect } from "react";
import {
  Search,
  Bell,
  ChevronDown,
  Plus,
  Command,
  CalendarDays,
  History,
  X,
  Check,
  Globe,
  LayoutGrid,
  Save,
  Bookmark,
  CheckSquare,
  Square,
  Moon,
  Sun,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "motion/react";
import { useAppStore } from "@/store/AppContext";
import { ComposePostDrawer } from "@/components/ui/ComposePostDrawer";
import { NotificationDrawer } from "@/components/ui/NotificationDrawer";

const DATE_RANGES = [
  { id: "today", name: "Hôm nay" },
  { id: "7d", name: "7 ngày qua" },
  { id: "30d", name: "30 ngày qua" },
  { id: "90d", name: "90 ngày qua" },
  { id: "ytd", name: "Năm nay (YTD)" },
  { id: "all", name: "Toàn thời gian" },
];

function useOnClickOutside(ref: any, handler: () => void) {
  useEffect(() => {
    const listener = (event: any) => {
      if (!ref.current || ref.current.contains(event.target)) return;
      handler();
    };
    document.addEventListener("mousedown", listener);
    document.addEventListener("touchstart", listener);
    return () => {
      document.removeEventListener("mousedown", listener);
      document.removeEventListener("touchstart", listener);
    };
  }, [ref, handler]);
}

export function Topbar() {
  const { filters, setFilters, clearFilters, alerts, theme, toggleTheme, groups } = useAppStore();
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState(true);
  const [searchFocused, setSearchFocused] = useState(false);
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);

  const toggleDropdown = (name: string) => {
    setActiveDropdown(activeDropdown === name ? null : name);
  };

  const hasActiveFilters = filters.platforms.length > 0 || filters.group !== "all";
  const platformOptions = [
    { id: "facebook", name: "Facebook" },
    { id: "youtube", name: "YouTube" },
    { id: "tiktok", name: "TikTok" },
  ];
  const quickViews = [
    { id: "all", name: "Tất cả", filters: { platforms: [], group: "all" } },
    ...groups
      .filter((group) => group.id !== "all")
      .slice(0, 3)
      .map((group) => ({ id: `group-${group.id}`, name: group.name, filters: { group: group.id } })),
  ];

  interface CustomDropdownProps {
    id: string;
    label: string;
    icon: any;
    options: any[];
    selected: string | string[];
    onSelect: (id: string) => void;
    isMulti?: boolean;
    onClear?: () => void;
  }

  const CustomDropdown = ({ id, label, icon: Icon, options, selected, onSelect, isMulti, onClear }: CustomDropdownProps) => {
    const ref = useRef<HTMLDivElement>(null);
    useOnClickOutside(ref, () => {
      if (activeDropdown === id) setActiveDropdown(null);
    });

    const isOpen = activeDropdown === id;
    const isSelected = isMulti ? (selected as string[]).length > 0 : (selected as string) !== "all";

    let displayText = label;
    if (isMulti) {
      const selectedValues = selected as string[];
      if (selectedValues.length === 1) {
        displayText = options.find((item) => item.id === selectedValues[0])?.name || label;
      } else if (selectedValues.length > 1) {
        displayText = `${selectedValues.length} đã chọn`;
      }
    } else if (selected !== "all") {
      displayText = options.find((item) => item.id === selected)?.name || label;
    }

    return (
      <div className="relative" ref={ref}>
        <button
          onClick={() => toggleDropdown(id)}
          className={cn(
            "group flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all",
            isOpen ? "border-white/20 bg-white/5" : "border-transparent text-text-secondary hover:border-white/10 hover:bg-white/5 hover:text-text-primary",
            isSelected && !isOpen ? "border-accent-blue/30 bg-accent-blue/10 text-accent-blue shadow-glow-blue" : "",
          )}
        >
          <Icon className={cn("h-4 w-4", isSelected ? "text-accent-blue" : "text-text-tertiary")} />
          <span className="max-w-[120px] truncate">{displayText}</span>
          <ChevronDown className={cn("h-3.5 w-3.5 transition-transform duration-240", isOpen ? "rotate-180" : "text-text-tertiary")} />
        </button>

        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: 6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.98 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
              className="absolute left-0 top-full z-50 mt-2 w-64 overflow-hidden rounded-xl border border-white/10 bg-obsidian-900 shadow-elevated backdrop-blur-2xl"
            >
              <div className="flex items-center justify-between border-b border-white/5 bg-obsidian-950/50 px-3 py-2">
                <span className="text-[10px] font-bold uppercase tracking-widest text-text-tertiary">{label}</span>
                {isMulti && (selected as string[]).length > 0 && (
                  <button onClick={onClear} className="text-[10px] font-bold uppercase text-accent-blue transition-colors hover:text-white">
                    Xóa chọn
                  </button>
                )}
              </div>
              <div className="max-h-[300px] overflow-y-auto p-1 custom-scrollbar">
                {options.map((option) => {
                  if (isMulti && option.id === "all") return null;
                  const isChecked = isMulti ? (selected as string[]).includes(option.id) : (selected as string) === option.id;
                  return (
                    <button
                      key={option.id}
                      onClick={() => {
                        onSelect(option.id);
                        if (!isMulti) setActiveDropdown(null);
                      }}
                      className={cn(
                        "mb-0.5 flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-all",
                        isChecked ? "bg-accent-blue/10 font-medium text-accent-blue shadow-soft-inset" : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
                      )}
                    >
                      <div className="flex items-center gap-2 truncate">
                        {isMulti ? (
                          isChecked ? <CheckSquare className="h-4 w-4 shrink-0" /> : <Square className="h-4 w-4 shrink-0 text-text-tertiary" />
                        ) : null}
                        <span className="truncate">{option.name}</span>
                      </div>
                      {!isMulti && isChecked && <Check className="h-4 w-4 shrink-0" />}
                    </button>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  const DateDropdown = () => {
    const ref = useRef<HTMLDivElement>(null);
    useOnClickOutside(ref, () => {
      if (activeDropdown === "date") setActiveDropdown(null);
    });

    const currentRange = DATE_RANGES.find((range) => range.id === filters.dateRange)?.name || "Tùy chỉnh";
    const isOpen = activeDropdown === "date";

    return (
      <div className="relative" ref={ref}>
        <button
          onClick={() => toggleDropdown("date")}
          className={cn(
            "flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-semibold transition-all",
            isOpen ? "border-white/20 bg-white/5 text-text-primary" : "border-transparent text-text-primary hover:border-white/10 hover:bg-white/5",
          )}
        >
          <CalendarDays className="h-4 w-4 text-accent-gold" />
          <span>{currentRange}</span>
          <ChevronDown className={cn("h-3.5 w-3.5 transition-transform duration-240", isOpen ? "rotate-180" : "text-text-tertiary")} />
        </button>
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: 6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.98 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
              className="absolute left-0 top-full z-50 mt-2 w-48 overflow-hidden rounded-xl border border-white/10 bg-obsidian-900 p-1 shadow-elevated backdrop-blur-2xl"
            >
              {DATE_RANGES.map((range) => (
                <button
                  key={range.id}
                  onClick={() => {
                    setFilters({ dateRange: range.id });
                    setActiveDropdown(null);
                  }}
                  className={cn(
                    "mb-0.5 flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-all",
                    filters.dateRange === range.id ? "bg-accent-gold/10 font-medium text-accent-gold" : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
                  )}
                >
                  {range.name}
                  {filters.dateRange === range.id && <Check className="h-4 w-4" />}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  return (
    <div className="sticky top-0 z-40 flex w-full flex-col border-b border-white/[0.05] bg-obsidian-950/80 backdrop-blur-2xl">
      <header className="relative z-30 flex h-[64px] shrink-0 items-center justify-between px-4 lg:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-6">
          <div
            className={cn(
              "group hidden w-80 items-center gap-2 rounded-lg border bg-obsidian-900/50 px-3 py-1.5 shadow-soft-inset transition-all duration-300 md:flex",
              searchFocused ? "border-accent-blue/50 bg-obsidian-900 ring-1 ring-accent-blue/30 shadow-glow-blue/20 line-shadow" : "border-white/10 hover:border-white/20 hover:bg-obsidian-900",
            )}
          >
            <Search className={cn("h-4 w-4 transition-colors", searchFocused ? "text-accent-blue" : "text-text-tertiary group-hover:text-text-secondary")} />
            <input
              type="text"
              value={filters.searchQuery}
              onChange={(e) => setFilters({ searchQuery: e.target.value })}
              placeholder="Tìm lệnh nhanh (ví dụ: 'Xem thống kê TikTok')..."
              className="w-full border-none bg-transparent text-sm font-medium text-text-primary outline-none placeholder-text-tertiary"
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
            />
            <div className="flex items-center gap-1 rounded border border-white/5 bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-text-tertiary transition-colors group-hover:text-text-secondary">
              <Command className="h-3 w-3" />
              <span>K</span>
            </div>
          </div>

          <div className="hidden h-5 w-px bg-white/10 xl:block"></div>

          <div className="hidden items-center gap-1.5 xl:flex">
            <span className="mr-2 flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-text-tertiary">
              <Bookmark className="h-3 w-3" /> Chế độ xem
            </span>
            {quickViews.map((view, idx) => (
              <button
                key={view.id}
                onClick={() => setFilters(view.filters || {})}
                className={cn(
                  "whitespace-nowrap rounded-md border px-3 py-1.5 text-xs font-medium transition-all",
                  idx === 0 && !hasActiveFilters
                    ? "border-white/10 bg-white/10 text-text-primary shadow-soft-inset"
                    : "border-transparent text-text-secondary hover:border-white/10 hover:bg-white/5 hover:text-text-primary",
                )}
              >
                {view.name}
              </button>
            ))}
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-3">
          <button className="group relative rounded-lg border border-transparent p-2 text-text-secondary transition-all hover:border-white/10 hover:bg-white/5 hover:text-text-primary" onClick={toggleTheme}>
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          <button
            className="group relative rounded-lg border border-transparent p-2 text-text-secondary transition-all hover:border-white/10 hover:bg-white/5 hover:text-text-primary"
            onClick={() => setIsNotifOpen(true)}
          >
            <Bell className="h-4 w-4 transition-transform group-hover:rotate-12" />
            {alerts.length > 0 && <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full border border-obsidian-950 bg-accent-blue shadow-glow-blue"></span>}
          </button>

          <div className="hidden items-center gap-2 sm:flex">
            <button
              onClick={() => setIsComposeOpen(true)}
              className="flex items-center gap-2 rounded-lg bg-white px-4 py-1.5 text-sm font-bold text-obsidian-950 shadow-glow-gold/20 transition-transform hover:scale-105"
            >
              <Plus className="h-4 w-4" />
              <span>Tạo mới</span>
            </button>
          </div>
        </div>
      </header>

      <div className="relative z-20 flex min-h-[48px] flex-wrap items-center justify-between gap-4 border-t border-white/[0.05] bg-obsidian-900/30 px-4 py-1 lg:px-6">
        <div className="flex items-center gap-2.5">
          <div className="mr-2 flex items-center rounded-lg border border-white/10 bg-obsidian-950/50 p-0.5 shadow-soft-inset">
            <DateDropdown />
            <div className="mx-1 h-4 w-px bg-white/10"></div>
            <button
              onClick={() => setCompareMode(!compareMode)}
              className={cn(
                "mx-0.5 flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider transition-all",
                compareMode ? "bg-accent-emerald/10 text-accent-emerald shadow-glow-emerald/10" : "text-text-tertiary hover:bg-white/5 hover:text-text-secondary",
              )}
            >
              <History className="h-3 w-3" />
              So sánh
            </button>
          </div>

          <CustomDropdown
            id="platform"
            label="Nền tảng"
            icon={Globe}
            options={platformOptions}
            selected={filters.platforms}
            isMulti
            onSelect={(id) => {
              setFilters({ platforms: filters.platforms.includes(id) ? filters.platforms.filter((platform) => platform !== id) : [...filters.platforms, id] });
            }}
            onClear={() => setFilters({ platforms: [] })}
          />
          <CustomDropdown
            id="group"
            label="Nhóm kênh"
            icon={LayoutGrid}
            options={groups.map((group) => ({ id: group.id, name: group.name }))}
            selected={filters.group}
            onSelect={(id) => setFilters({ group: id })}
          />
        </div>

        <div className="flex items-center gap-2">
          <AnimatePresence>
            {hasActiveFilters && (
              <motion.button
                initial={{ opacity: 0, scale: 0.9, x: 10 }}
                animate={{ opacity: 1, scale: 1, x: 0 }}
                exit={{ opacity: 0, scale: 0.9, x: 10 }}
                onClick={clearFilters}
                className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-[10px] font-bold uppercase tracking-widest text-text-tertiary transition-colors hover:bg-danger/10 hover:text-danger"
              >
                <X className="h-3.5 w-3.5" />
                Đặt lại
              </motion.button>
            )}
          </AnimatePresence>

          {hasActiveFilters && (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-1.5 rounded-md border border-white/5 bg-white/5 px-2 py-1.5 text-[10px] font-bold uppercase tracking-widest text-text-tertiary transition-colors hover:border-white/10 hover:text-text-primary"
            >
              <Save className="h-3.5 w-3.5" />
              Lưu bộ lọc
            </motion.button>
          )}
        </div>
      </div>

      <ComposePostDrawer isOpen={isComposeOpen} onClose={() => setIsComposeOpen(false)} />
      <NotificationDrawer isOpen={isNotifOpen} onClose={() => setIsNotifOpen(false)} />
    </div>
  );
}
