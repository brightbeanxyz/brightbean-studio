import { useState, useMemo } from "react";
import { Card } from "@/components/ui/Card";
import { formatNumber, formatCompactNumber, cn } from "@/lib/utils";
import { FilterBar } from "@/components/ui/FilterBar";
import { useAppStore } from "@/store/AppContext";
import {
  ArrowUpDown,
  MoreHorizontal,
  Play,
  Image as ImageIcon,
  Video,
  Filter,
  Heart,
  MessageCircle,
  Share2,
  Award,
  Zap,
  TrendingUp,
  TrendingDown,
  Eye,
  Users,
  Search,
  ChevronRight,
  X,
  SlidersHorizontal,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { MetricChip } from "@/components/ui/MetricChip";
import { ContentDataTable } from "@/components/ui/ContentDataTable";
import { EmptyState } from "@/components/ui/EmptyState";

export default function ContentExplorer() {
  const { filteredContents, filters, setFilters, clearFilters, groups, channels } = useAppStore();
  const [selectedContentId, setSelectedContentId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const selectedContent = filteredContents.find(
    (c) => c.id === selectedContentId,
  );

  // Group options
  const groupOptions = useMemo(() => {
    return [{ id: "all", name: "Tất cả Nhóm" }, ...groups];
  }, [groups]);

  // Channel options (filtered by selected group)
  const channelOptions = useMemo(() => {
    let baseChannels = channels;
    if (filters.group !== "all") {
      baseChannels = baseChannels.filter(c => c.groupId === filters.group);
    }
    return [{ id: "all", name: "Tất cả Kênh" }, ...baseChannels];
  }, [channels, filters.group]);

  // Platform options
  const platformOptions = [
    { id: "all", name: "Tất cả Nền tảng" },
    { id: "facebook", name: "Facebook" },
    { id: "youtube", name: "YouTube" },
    { id: "tiktok", name: "TikTok" },
  ];

  // Compute derived KPIs from filtered context
  const kpis = useMemo(() => {
    if (!filteredContents.length) return [];
    
    const avgEr = filteredContents.reduce((acc, curr) => acc + (curr.engagementRate || 0), 0) / filteredContents.length;
    const avgReach = filteredContents.reduce((acc, curr) => acc + (curr.reach || 0), 0) / filteredContents.length;
    
    // Determine best pillar (naive mode)
    const pillars: Record<string, { er: number, count: number }> = {};
    filteredContents.forEach(c => {
       if (!pillars[c.pillar]) pillars[c.pillar] = { er: 0, count: 0 };
       pillars[c.pillar].er += c.engagementRate || 0;
       pillars[c.pillar].count += 1;
    });
    
    let bestPillar = "";
    let bestEr = 0;
    Object.entries(pillars).forEach(([key, val]) => {
      const pAvg = val.er / val.count;
      if (pAvg > bestEr) {
        bestEr = pAvg;
        bestPillar = key;
      }
    });

    let worstPillar = "";
    let worstEr = 100;
    Object.entries(pillars).forEach(([key, val]) => {
      const pAvg = val.er / val.count;
      if (pAvg < worstEr) {
        worstEr = pAvg;
        worstPillar = key;
      }
    });

    return [
      { label: "Tổng Nội Dung", value: formatNumber(filteredContents.length) },
      {
        label: "Avg Engagement",
        value: `${avgEr.toFixed(1)}%`,
        trend: "up",
        change: "+1.2%",
      },
      {
        label: "Avg Reach/View",
        value: formatCompactNumber(avgReach),
        trend: "up",
        change: "+5.4%",
      },
      { label: "Best Pillar", value: bestPillar || "-", sub: bestEr ? `${bestEr.toFixed(1)}% ER` : "-" },
      { label: "Needs Review", value: worstPillar || "-", sub: worstEr < 100 ? `${worstEr.toFixed(1)}% ER` : "-" },
    ];
  }, [filteredContents]);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* 1. HEADER */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-1">
            Content Intelligence
          </h1>
          <p className="text-text-secondary">
            Phân tích hiệu suất nội dung chuyên sâu trên toàn hệ thống.
          </p>
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto">
          <button 
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              "px-4 py-2 border rounded-xl font-medium transition-colors flex items-center justify-center gap-2",
              showFilters 
                ? "bg-accent-blue/10 border-accent-blue text-accent-blue" 
                : "bg-obsidian-800 border-white/10 hover:bg-white/5 text-text-primary shadow-card hover:shadow-hover-elevation"
            )}
          >
            <SlidersHorizontal className="w-4 h-4" />
            Bộ Lọc Nâng Cao
          </button>
        </div>
      </div>

      {showFilters && (
        <div className="mb-6 shrink-0 grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-xl border border-border-default bg-surface-elevated animate-in fade-in slide-in-from-top-2">
          <div>
            <label className="block text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">Nhóm Kênh</label>
            <select
              value={filters.group}
              onChange={(e) => setFilters({ group: e.target.value })}
              className="w-full bg-obsidian-950 border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-blue transition-colors"
            >
              {groupOptions.map(g => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">Kênh</label>
            <select
              value={filters.channel}
              onChange={(e) => setFilters({ channel: e.target.value })}
              className="w-full bg-obsidian-950 border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-blue transition-colors"
            >
              {channelOptions.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">Nền Tảng</label>
            <select
              value={filters.platforms.length > 0 ? filters.platforms[0] : 'all'}
              onChange={(e) => {
                const val = e.target.value;
                setFilters({ platforms: val === 'all' ? [] : [val] });
              }}
              className="w-full bg-obsidian-950 border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-blue transition-colors"
            >
              {platformOptions.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end justify-end">
            <button 
              onClick={clearFilters}
              className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-white transition-colors"
            >
              Xóa bộ lọc
            </button>
          </div>
        </div>
      )}

      {/* 3. SUMMARY KPI */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6 shrink-0">
        {kpis.length > 0 ? kpis.map((k, i) => (
          <Card
            key={i}
            className="p-4 bg-obsidian-900/50 hover:bg-obsidian-900/80 transition-colors"
          >
            <div className="text-[10px] text-text-tertiary uppercase tracking-wider mb-1 font-medium">
              {k.label}
            </div>
            <div className="flex items-end justify-between">
              <div className="text-xl font-bold text-white truncate">
                {k.value}
              </div>
              {k.trend && (
                <MetricChip
                  value={k.change!}
                  trend={k.trend as "up" | "down"}
                  variant={k.trend === "up" ? "success" : "warning"}
                  size="sm"
                />
              )}
            </div>
            {k.sub && (
              <div className="text-xs text-text-secondary mt-1">{k.sub}</div>
            )}
          </Card>
        )) : (
          <div className="col-span-full h-[88px] flex items-center justify-center border border-white/10 rounded-xl bg-obsidian-900/50 text-text-tertiary text-sm">
            Không có dữ liệu tổng quan
          </div>
        )}
      </div>

      {/* 4. MAIN LAYOUT */}
      <div className="flex-1 flex gap-6 overflow-hidden min-h-0">
        <div className="flex-1 overflow-auto rounded-2xl bg-surface-card border border-white/5 relative">
          {filteredContents.length > 0 ? (
            <ContentDataTable data={filteredContents} onSelect={setSelectedContentId} selectedId={selectedContentId} />
          ) : (
            <EmptyState 
              icon={Search} 
              title="Không tìm thấy nội dung" 
              description={filters.searchQuery ? `Không có nội dung nào phù hợp với từ khoá "${filters.searchQuery}"` : "Hãy thử thay đổi bộ lọc ở trên để xem thêm dữ liệu."}
            />
          )}
        </div>
      </div>
    </div>
  );
}
