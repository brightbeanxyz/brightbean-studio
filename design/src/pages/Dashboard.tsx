import { useMemo } from "react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { TrendChart } from "@/components/charts/TrendChart";
import { PlatformMixChart } from "@/components/charts/PlatformMixChart";
import { HeatmapChart } from "@/components/charts/HeatmapChart";
import { TinySparkline } from "@/components/charts/TinySparkline";
import { MetricChip } from "@/components/ui/MetricChip";
import { Tabs } from "@/components/ui/Tabs";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCompactNumber, cn } from "@/lib/utils";
import { useAppStore } from "@/store/AppContext";
import {
  ArrowRight,
  Facebook,
  Globe,
  Hash,
  Image as ImageIcon,
  MessageSquare,
  Play,
  Target,
  TrendingUp,
  Video,
  Youtube,
} from "lucide-react";

const PLATFORM_COLORS: Record<string, string> = {
  facebook: "#3b82f6",
  youtube: "#ef4444",
  tiktok: "#14b8a6",
};

export default function Dashboard() {
  const {
    filteredContents,
    filters,
    setFilters,
    dashboardKpis,
    trendData,
    reports,
    channelAnalytics,
    inboxMessages,
    channels,
  } = useAppStore();

  const platformMixData = useMemo(
    () =>
      (reports?.platformData || []).map((item: any) => ({
        ...item,
        fill: PLATFORM_COLORS[item.name?.toLowerCase()] || "#e4c580",
      })),
    [reports],
  );

  const interactionDistribution = useMemo(() => {
    const totalsByPlatform = channels.reduce(
      (acc: Record<string, { reach: number; engagement: number; comments: number }>, channel: any) => {
        acc[channel.platform] ||= { reach: 0, engagement: 0, comments: 0 };
        return acc;
      },
      {},
    );
    filteredContents.forEach((item: any) => {
      totalsByPlatform[item.platform] ||= { reach: 0, engagement: 0, comments: 0 };
      totalsByPlatform[item.platform].reach += item.reach || 0;
      totalsByPlatform[item.platform].engagement += item.engagement || 0;
      totalsByPlatform[item.platform].comments += item.comments || 0;
    });

    const buildRow = (label: string, key: "reach" | "engagement" | "comments") => {
      const fb = totalsByPlatform.facebook?.[key] || 0;
      const yt = totalsByPlatform.youtube?.[key] || 0;
      const tt = totalsByPlatform.tiktok?.[key] || 0;
      const total = Math.max(fb + yt + tt, 1);
      return {
        label,
        value: formatCompactNumber(total),
        fb,
        yt,
        tt,
        fbPct: Math.round((fb / total) * 100),
        ytPct: Math.round((yt / total) * 100),
        ttPct: Math.max(0, 100 - Math.round((fb / total) * 100) - Math.round((yt / total) * 100)),
      };
    };

    return [
      buildRow("Lượt tiếp cận", "reach"),
      buildRow("Tương tác", "engagement"),
      buildRow("Bình luận", "comments"),
    ];
  }, [channels, filteredContents]);

  const sentimentByPlatform = useMemo(() => {
    const initial = {
      facebook: { total: 0, positive: 0, negative: 0 },
      youtube: { total: 0, positive: 0, negative: 0 },
      tiktok: { total: 0, positive: 0, negative: 0 },
    };
    inboxMessages.forEach((item: any) => {
      if (!initial[item.platform as keyof typeof initial]) return;
      initial[item.platform as keyof typeof initial].total += 1;
      if (item.sentiment === "positive") initial[item.platform as keyof typeof initial].positive += 1;
      if (item.sentiment === "negative") initial[item.platform as keyof typeof initial].negative += 1;
    });
    return initial;
  }, [inboxMessages]);

  const topChannels = useMemo(
    () =>
      [...channels]
        .sort((a: any, b: any) => {
          const aValue = Number(String(a.followers).replace(/[^\d.]/g, "")) || 0;
          const bValue = Number(String(b.followers).replace(/[^\d.]/g, "")) || 0;
          return bValue - aValue;
        })
        .slice(0, 2),
    [channels],
  );

  const heatmapData = channelAnalytics?.heatmapData || [];
  const chartData = trendData || [];

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case "youtube":
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500/20 text-xs font-bold text-red-500">
            Y
          </div>
        );
      case "tiktok":
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500/20 text-xs font-bold text-cyan-500">
            T
          </div>
        );
      case "facebook":
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-500/20 text-xs font-bold text-blue-500">
            F
          </div>
        );
      default:
        return null;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "video":
        return <Video className="h-4 w-4 text-text-tertiary" />;
      case "short":
        return <Play className="h-4 w-4 text-text-tertiary" />;
      default:
        return <ImageIcon className="h-4 w-4 text-text-tertiary" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="mb-1 text-3xl font-semibold tracking-tight text-text-primary">Tổng Quan Điều Hành</h1>
          <p className="text-text-secondary">
            Hiệu suất đa kênh được tổng hợp trực tiếp từ workspace hiện tại.
          </p>
        </div>
      </div>

      <div className="mb-6">
        <Tabs
          value={filters.platforms.length === 0 ? "all" : filters.platforms[0]}
          onValueChange={(value) => setFilters({ platforms: value === "all" ? [] : [value] })}
          options={[
            { label: "Tất cả nền tảng", value: "all" },
            { label: "Facebook", value: "facebook" },
            { label: "YouTube", value: "youtube" },
            { label: "TikTok", value: "tiktok" },
          ]}
        />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        {dashboardKpis.map((kpi: any) => (
          <Card key={kpi.title} interactive className="group relative overflow-hidden p-5">
            <CardDescription className="mb-2 text-xs uppercase tracking-wider">{kpi.title}</CardDescription>
            <div className="mb-3 flex items-end justify-between">
              <div className="text-3xl font-bold tracking-tight text-white">{kpi.value}</div>
              <MetricChip
                value={kpi.change}
                trend={kpi.trend as "up" | "down"}
                variant={kpi.trend === "up" ? "success" : "warning"}
                size="sm"
              />
            </div>
            <div className="mt-auto flex items-center justify-between">
              <div className="flex gap-1.5">
                {kpi.platforms.map((platform: string) => (
                  <div
                    key={platform}
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ backgroundColor: PLATFORM_COLORS[platform] || "#e4c580" }}
                    title={platform}
                  />
                ))}
              </div>
              <div className="opacity-60 transition-opacity group-hover:opacity-100">
                <TinySparkline data={kpi.trendData} trend={kpi.trend as "up" | "down"} />
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="flex min-h-[400px] flex-col lg:col-span-2">
          <CardHeader>
            <div>
              <CardTitle>Tăng trưởng đa kênh</CardTitle>
              <CardDescription>Reach và tương tác 30 ngày gần nhất.</CardDescription>
            </div>
            <div className="flex items-center gap-4 text-xs font-medium text-text-tertiary">
              <div className="flex items-center gap-2">
                <div className="h-0.5 w-3 bg-accent-gold"></div>Tổng quan
              </div>
              <div className="flex items-center gap-2">
                <div className="h-0.5 w-3 bg-red-500"></div>YouTube
              </div>
              <div className="flex items-center gap-2">
                <div className="h-0.5 w-3 bg-cyan-500"></div>TikTok
              </div>
              <div className="flex items-center gap-2">
                <div className="h-0.5 w-3 bg-blue-500"></div>Facebook
              </div>
            </div>
          </CardHeader>
          <div className="mt-4 flex-1 -ml-4">
            <TrendChart data={chartData} />
          </div>
        </Card>

        <Card className="flex min-h-[400px] flex-col">
          <CardHeader className="mb-0">
            <div>
              <CardTitle>Cơ cấu đóng góp</CardTitle>
              <CardDescription>Phân bổ reach theo nền tảng đang kết nối.</CardDescription>
            </div>
          </CardHeader>
          <div className="flex-1">
            <PlatformMixChart
              data={platformMixData}
              centerValue={String(platformMixData.length)}
              centerLabel="Nền tảng"
            />
          </div>
        </Card>
      </div>

      <Card className="flex flex-col overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-white/5 p-5">
          <div>
            <CardTitle>Bảng Xếp Hạng Nội Dung</CardTitle>
            <CardDescription>Top nội dung hiệu suất cao theo analytics hiện có.</CardDescription>
          </div>
          <button className="flex items-center gap-1 text-sm font-medium text-accent-blue transition-colors hover:text-blue-400">
            Xem tất cả <ArrowRight className="h-4 w-4 text-accent-blue" />
          </button>
        </div>
        <div className="flex-1 overflow-auto rounded-b-2xl">
          {filteredContents.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={Globe}
                title="Chưa có nội dung analytics"
                description="Kết nối kênh hoặc đăng nội dung để bắt đầu tổng hợp hiệu suất."
              />
            </div>
          ) : (
            <table className="w-full whitespace-nowrap text-left text-sm">
              <thead className="sticky top-0 z-10 bg-obsidian-950/50">
                <tr>
                  <th className="px-5 py-3 font-medium text-text-tertiary">Nội dung</th>
                  <th className="px-5 py-3 font-medium text-text-tertiary">Reach</th>
                  <th className="px-5 py-3 font-medium text-text-tertiary">Tương tác</th>
                  <th className="w-24 px-5 py-3 text-center font-medium text-text-tertiary">Tác động</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredContents.slice(0, 5).map((item: any) => (
                  <tr key={item.id} className="group transition-colors hover:bg-white/[0.02]">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-4">
                        <div className="relative">
                          <div className="h-8 w-12 shrink-0 overflow-hidden rounded border border-white/10 bg-obsidian-900 transition-colors group-hover:border-white/20">
                            <img
                              src={item.thumbnail}
                              alt={item.title}
                              className="h-full w-full object-cover opacity-80 group-hover:opacity-100"
                            />
                          </div>
                          <div className="absolute -bottom-1 -right-1">{getPlatformIcon(item.platform)}</div>
                        </div>
                        <div>
                          <div className="block max-w-[200px] cursor-pointer truncate font-medium text-text-primary transition-colors group-hover:text-accent-blue xl:max-w-[300px]">
                            {item.title}
                          </div>
                          <div className="mt-0.5 flex items-center gap-1 text-xs text-text-tertiary">
                            {getTypeIcon(item.type || "")} {item.type ? item.type.toUpperCase() : "POST"}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3 font-mono text-text-secondary">{formatCompactNumber(item.reach)}</td>
                    <td className="px-5 py-3 font-mono text-text-secondary">{formatCompactNumber(item.engagement)}</td>
                    <td className="px-5 py-3 text-center">
                      <span
                        className={cn(
                          "inline-block rounded px-2 py-1 text-xs font-mono",
                          item.growthImpact?.includes("High")
                            ? "border border-accent-emerald/20 bg-accent-emerald/10 text-accent-emerald"
                            : "border border-yellow-500/20 bg-yellow-500/10 text-yellow-500",
                        )}
                      >
                        {item.growthImpact || item.status || "N/A"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Phân bổ tương tác theo giờ</CardTitle>
              <CardDescription>Heatmap lấy từ dữ liệu inbox và analytics kênh đang chọn.</CardDescription>
            </div>
          </CardHeader>
          <div className="mt-5">
            {heatmapData.length > 0 ? (
              <HeatmapChart data={heatmapData} />
            ) : (
              <EmptyState
                icon={MessageSquare}
                title="Chưa đủ dữ liệu"
                description="Cần thêm hội thoại hoặc dữ liệu analytics để hiển thị heatmap."
              />
            )}
          </div>
        </Card>

        <div className="flex flex-col justify-between space-y-6">
          <Card className="flex-1">
            <CardHeader className="mb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <MessageSquare className="h-4 w-4 text-accent-blue" /> Bình luận và sentiment theo kênh
              </CardTitle>
            </CardHeader>
            <div className="space-y-4">
              {(["facebook", "youtube", "tiktok"] as const).map((platform) => {
                const stats = sentimentByPlatform[platform];
                const total = Math.max(stats.total, 1);
                const positivePct = Math.round((stats.positive / total) * 100);
                const negativePct = Math.round((stats.negative / total) * 100);
                if (!stats.total) return null;
                return (
                  <div key={platform} className="flex items-center gap-3 rounded-lg border border-white/5 bg-obsidian-900 p-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/5">
                      {platform === "facebook" ? (
                        <Facebook className="h-4 w-4 text-[#1877F2]" />
                      ) : platform === "youtube" ? (
                        <Youtube className="h-4 w-4 text-[#FF0000]" />
                      ) : (
                        <Hash className="h-4 w-4 text-white" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center justify-between">
                        <span className="text-sm font-semibold capitalize text-white">{platform}</span>
                        <span className="text-sm font-bold text-white">{formatCompactNumber(stats.total)}</span>
                      </div>
                      <div className="flex gap-2 text-xs">
                        <span className="truncate rounded bg-accent-emerald/10 px-1.5 py-0.5 font-medium text-accent-emerald">
                          {positivePct}% tích cực
                        </span>
                        <span className="truncate rounded bg-danger/10 px-1.5 py-0.5 font-medium text-danger">
                          {negativePct}% tiêu cực
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card className="flex-1">
            <CardHeader className="mb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Target className="h-4 w-4 text-accent-violet" /> Kênh nổi bật
              </CardTitle>
            </CardHeader>
            <div className="space-y-3">
              {topChannels.map((channel: any) => (
                <div key={channel.id} className="block-interactive rounded-xl border border-white/5 bg-obsidian-900 p-3">
                  <div className="mb-2 flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-surface-elevated text-accent-blue">
                        <Target className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white">{channel.name}</div>
                        <div className="text-xs text-text-tertiary">{channel.handle}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 rounded-full bg-accent-emerald/10 px-2 py-1 text-xs font-bold text-accent-emerald">
                      <TrendingUp className="h-3 w-3" /> {channel.status === "connected" ? "Connected" : "Check"}
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs text-text-secondary">
                    <div>
                      <span className="text-text-tertiary">Followers: </span>
                      <span className="font-semibold text-white">{channel.followers}</span>
                    </div>
                    <div className="h-1 w-px bg-white/10"></div>
                    <div>
                      <span className="text-text-tertiary">Platform: </span>
                      <span className="font-semibold capitalize text-white">{channel.platform}</span>
                    </div>
                    <div className="h-1 w-px bg-white/10"></div>
                    <div>
                      <span className="text-text-tertiary">Sync: </span>
                      <span className="font-semibold text-white">{channel.lastSync}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
