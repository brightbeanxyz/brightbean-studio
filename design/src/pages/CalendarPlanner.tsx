import { useMemo, useState } from "react";
import {
  addDays,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  startOfMonth,
  startOfWeek,
  subDays,
} from "date-fns";
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  List,
  Plus,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/AppContext";
import { PostCard, type Platform, type PostStatus } from "@/components/ui/PostCard";
import { ContentDetailDrawer } from "@/components/ui/ContentDetailDrawer";
import { EmptyState } from "@/components/ui/EmptyState";
import { ComposePostDrawer } from "@/components/ui/ComposePostDrawer";

type ViewMode = "month" | "week" | "agenda";

type CalendarEvent = {
  id: string;
  title: string;
  time: string;
  date: Date;
  platform: Platform;
  status: string;
  perfScore: number;
};

function toPostStatus(status: string): PostStatus {
  switch (status) {
    case "published":
      return "published";
    case "scheduled":
      return "scheduled";
    case "approval":
      return "pending_approval";
    case "error":
      return "failed";
    default:
      return "draft";
  }
}

export default function CalendarPlanner() {
  const { posts } = useAppStore();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState<ViewMode>("month");
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    platform: "all",
    status: "all",
    search: "",
  });

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const monthGridStart = startOfWeek(monthStart, { weekStartsOn: 1 });
  const monthGridEnd = endOfWeek(monthEnd, { weekStartsOn: 1 });
  const monthDays = eachDayOfInterval({ start: monthGridStart, end: monthGridEnd });

  const weekStart = startOfWeek(currentDate, { weekStartsOn: 1 });
  const weekEnd = endOfWeek(currentDate, { weekStartsOn: 1 });
  const weekDays = eachDayOfInterval({ start: weekStart, end: weekEnd });

  const visibleDays = viewMode === "month" ? monthDays : weekDays;

  const events = useMemo<CalendarEvent[]>(() => {
    const sourcePosts = Array.isArray(posts) ? posts : [];
    const today = new Date();

    let normalized = sourcePosts.map((post, index) => {
      const safeOffset = Number(post?.dateOffset ?? 0);
      return {
        id: String(post?.id ?? `post-${index}`),
        title: String(post?.title || "Nội dung chưa đặt tên"),
        time: String(post?.time || "00:00"),
        date: addDays(today, Number.isFinite(safeOffset) ? safeOffset : 0),
        platform: String(post?.platform || "facebook") as Platform,
        status: String(post?.status || "draft"),
        perfScore: Number(post?.perfScore ?? 0),
      };
    });

    if (filters.platform !== "all") {
      normalized = normalized.filter((event) => event.platform === filters.platform);
    }

    if (filters.status !== "all") {
      normalized = normalized.filter((event) => event.status === filters.status);
    }

    if (filters.search.trim()) {
      const query = filters.search.trim().toLowerCase();
      normalized = normalized.filter((event) => event.title.toLowerCase().includes(query));
    }

    return normalized;
  }, [filters, posts]);

  const nextPeriod = () => {
    setCurrentDate(viewMode === "month" ? addDays(monthEnd, 1) : addDays(weekEnd, 1));
  };

  const previousPeriod = () => {
    setCurrentDate(viewMode === "month" ? subDays(monthStart, 1) : subDays(weekStart, 1));
  };

  const emptyState = (
    <EmptyState
      icon={CalendarIcon}
      title="Không tìm thấy nội dung"
      description="Không có nội dung nào phù hợp với bộ lọc hiện tại hoặc trong khoảng thời gian này."
      action={
        <button
          onClick={() => setIsComposeOpen(true)}
          className="rounded-xl bg-text-primary px-4 py-2 text-sm font-medium text-obsidian-950 transition-colors hover:bg-white"
        >
          Tạo chiến dịch
        </button>
      }
    />
  );

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col space-y-6">
      <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="mb-1 text-3xl font-bold tracking-tight text-text-primary">Lịch phân phối</h1>
          <p className="text-text-secondary">Theo dõi lịch đăng, mật độ nội dung và nhịp chiến dịch theo ngày.</p>
        </div>

        <div className="flex w-full items-center gap-3 overflow-x-auto pb-2 md:w-auto md:pb-0">
          <div className="flex shrink-0 rounded-xl border border-white/5 bg-obsidian-800 p-1">
            <button
              onClick={() => setViewMode("month")}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all",
                viewMode === "month" ? "bg-obsidian-600 text-text-primary shadow-sm" : "text-text-secondary hover:text-text-primary",
              )}
            >
              <CalendarIcon className="h-4 w-4" />
              Tháng
            </button>
            <button
              onClick={() => setViewMode("week")}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all",
                viewMode === "week" ? "bg-obsidian-600 text-text-primary shadow-sm" : "text-text-secondary hover:text-text-primary",
              )}
            >
              <List className="h-4 w-4" />
              Tuần
            </button>
            <button
              onClick={() => setViewMode("agenda")}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all",
                viewMode === "agenda" ? "bg-obsidian-600 text-text-primary shadow-sm" : "text-text-secondary hover:text-text-primary",
              )}
            >
              <Clock className="h-4 w-4" />
              Agenda
            </button>
          </div>

          <button
            onClick={() => setShowFilters((current) => !current)}
            className={cn(
              "flex shrink-0 items-center justify-center gap-2 rounded-xl border px-4 py-2 font-medium transition-colors",
              showFilters ? "border-accent-blue bg-accent-blue/10 text-accent-blue" : "border-white/10 bg-obsidian-800 text-text-primary hover:bg-white/5",
            )}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Bộ lọc
          </button>

          <button
            onClick={() => setIsComposeOpen(true)}
            className="flex shrink-0 items-center justify-center gap-2 rounded-xl border border-transparent bg-text-primary px-4 py-2 font-medium text-obsidian-950 transition-colors hover:bg-white"
          >
            <Plus className="h-4 w-4" />
            Tạo lịch đăng
          </button>
        </div>
      </div>

      {showFilters && (
        <div className="grid shrink-0 grid-cols-1 gap-4 rounded-xl border border-border-default bg-surface-elevated p-4 md:grid-cols-4">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Tìm kiếm</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
              <input
                type="text"
                value={filters.search}
                onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
                placeholder="Tìm nội dung..."
                className="w-full rounded-lg border border-border-default bg-obsidian-950 py-2 pl-9 pr-3 text-sm text-text-primary outline-none transition-colors focus:border-accent-blue"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Nền tảng</label>
            <select
              value={filters.platform}
              onChange={(event) => setFilters((current) => ({ ...current, platform: event.target.value }))}
              className="w-full rounded-lg border border-border-default bg-obsidian-950 px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-accent-blue"
            >
              <option value="all">Tất cả nền tảng</option>
              <option value="facebook">Facebook</option>
              <option value="youtube">YouTube</option>
              <option value="tiktok">TikTok</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Trạng thái</label>
            <select
              value={filters.status}
              onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
              className="w-full rounded-lg border border-border-default bg-obsidian-950 px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-accent-blue"
            >
              <option value="all">Tất cả trạng thái</option>
              <option value="published">Đã đăng</option>
              <option value="scheduled">Đã lên lịch</option>
              <option value="approval">Chờ duyệt</option>
              <option value="error">Lỗi tải lên</option>
              <option value="draft">Bản nháp</option>
            </select>
          </div>

          <div className="flex items-end justify-end">
            <button
              onClick={() => setFilters({ platform: "all", status: "all", search: "" })}
              className="px-4 py-2 text-sm font-medium text-text-secondary transition-colors hover:text-white"
            >
              Xóa bộ lọc
            </button>
          </div>
        </div>
      )}

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <Card className="flex flex-1 flex-col overflow-hidden border border-white/10 bg-obsidian-900/40 p-0 shadow-2xl">
          <div className="flex items-center justify-between border-b border-white/10 bg-obsidian-800/80 p-4 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setCurrentDate(new Date())}
                className="rounded-lg border border-white/5 bg-white/5 px-3 py-1.5 text-sm font-medium transition-colors hover:bg-white/10 hover:text-white"
              >
                Hôm nay
              </button>
              <div className="flex items-center gap-1 rounded-lg border border-white/5 bg-obsidian-900 p-0.5">
                <button onClick={previousPeriod} className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-white/10 hover:text-white">
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button onClick={nextPeriod} className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-white/10 hover:text-white">
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
              <h2 className="min-w-[150px] text-xl font-semibold text-white">
                {format(viewMode === "month" ? monthStart : weekStart, "MMMM yyyy")}
              </h2>
            </div>
          </div>

          <div className="flex-1 overflow-auto bg-obsidian-950">
            {events.length === 0 ? (
              <div className="flex min-h-full items-center justify-center p-8">{emptyState}</div>
            ) : viewMode === "agenda" ? (
              <div className="mx-auto flex max-w-4xl flex-col gap-8 p-4 md:p-8">
                {weekDays
                  .filter((day) => events.some((event) => isSameDay(event.date, day)))
                  .map((day) => {
                    const dayEvents = events.filter((event) => isSameDay(event.date, day));
                    return (
                      <div key={day.toISOString()} className="flex gap-4 md:gap-8">
                        <div className="w-16 shrink-0 pt-3 text-right">
                          <div className={cn("text-3xl font-light", isToday(day) ? "font-medium text-accent-blue" : "text-text-primary")}>
                            {format(day, "d")}
                          </div>
                          <div className={cn("mt-1 text-xs uppercase tracking-wider", isToday(day) ? "text-accent-blue" : "text-text-tertiary")}>
                            {format(day, "EEE")}
                          </div>
                        </div>
                        <div className="flex-1 space-y-4 pb-4">
                          {dayEvents.map((event) => (
                            <div key={event.id} className="flex flex-col gap-3 rounded-xl bg-obsidian-900/30 p-3 md:flex-row md:items-center md:bg-transparent md:p-0">
                              <div className="w-24 shrink-0 text-sm font-mono text-text-secondary">{event.time}</div>
                              <div className="min-w-0 flex-1">
                                <PostCard
                                  title={event.title}
                                  platform={event.platform}
                                  status={toPostStatus(event.status)}
                                  time={event.time}
                                  performance={event.perfScore ? { score: event.perfScore } : undefined}
                                  group="General"
                                  onPostClick={() => setSelectedPostId(event.id)}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
              </div>
            ) : (
              <div className="flex min-h-full flex-col">
                <div className="sticky top-0 z-10 grid grid-cols-7 border-b border-white/5 bg-obsidian-900/50 backdrop-blur-md">
                  {["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"].map((label, index) => (
                    <div
                      key={label}
                      className={cn("p-3 text-center text-xs font-semibold uppercase tracking-wider", index >= 5 ? "text-text-tertiary" : "text-text-secondary")}
                    >
                      {label}
                    </div>
                  ))}
                </div>

                <div className={cn("grid grid-cols-7", viewMode === "month" ? "auto-rows-fr" : "auto-rows-auto")}>
                  {visibleDays.map((day) => {
                    const dayEvents = events.filter((event) => isSameDay(event.date, day));
                    return (
                      <div
                        key={day.toISOString()}
                        className={cn(
                          "group relative flex min-h-[140px] flex-col gap-1 border-b border-r border-white/5 p-2 transition-colors",
                          viewMode === "week" && "min-h-[220px]",
                          !isSameMonth(day, currentDate) && viewMode === "month" ? "bg-obsidian-950/60 opacity-40" : "hover:bg-white/[0.02]",
                          isToday(day) && "bg-accent-blue/[0.03]",
                        )}
                      >
                        <div className="mb-1 flex items-center justify-between px-1">
                          <span
                            className={cn(
                              "flex h-7 w-7 items-center justify-center rounded-full text-sm font-semibold",
                              isToday(day) ? "bg-accent-blue text-white" : "text-text-secondary group-hover:text-text-primary",
                            )}
                          >
                            {format(day, "d")}
                          </span>
                        </div>

                        <div className="hide-scrollbar flex-1 space-y-1 overflow-y-auto pr-1">
                          {dayEvents.map((event) => (
                            <PostCard
                              key={event.id}
                              title={event.title}
                              platform={event.platform}
                              status={toPostStatus(event.status)}
                              time={event.time}
                              performance={event.perfScore ? { score: event.perfScore } : undefined}
                              variant={viewMode === "month" ? "compact" : "default"}
                              className="cursor-pointer"
                              onPostClick={() => setSelectedPostId(event.id)}
                            />
                          ))}
                        </div>

                        <button
                          onClick={() => setIsComposeOpen(true)}
                          className="absolute bottom-2 right-2 flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-obsidian-800 text-text-tertiary opacity-0 transition-all hover:scale-110 hover:bg-white/10 hover:text-white group-hover:opacity-100"
                          title="Thêm bài viết"
                        >
                          <Plus className="h-3 w-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>

      <ContentDetailDrawer isOpen={!!selectedPostId} onClose={() => setSelectedPostId(null)} contentId={selectedPostId} />
      <ComposePostDrawer isOpen={isComposeOpen} onClose={() => setIsComposeOpen(false)} />
    </div>
  );
}
