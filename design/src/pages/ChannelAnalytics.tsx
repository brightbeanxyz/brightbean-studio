import { useMemo, useState } from "react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { TrendChart } from "@/components/charts/TrendChart";
import { HeatmapChart } from "@/components/charts/HeatmapChart";
import { MetricChip } from "@/components/ui/MetricChip";
import { ContentDataTable } from "@/components/ui/ContentDataTable";
import { useAppStore } from "@/store/AppContext";
import { CalendarRange, Download, ExternalLink, MessageSquare, RefreshCw, Settings, Users, Video } from "lucide-react";

export default function ChannelAnalytics() {
  const { channelAnalytics, filteredContents, runChannelAction } = useAppStore();
  const [activeTab, setActiveTab] = useState("overview");

  const selectedChannel = channelAnalytics?.selected;
  const summary = channelAnalytics?.summary || {};
  const kpis = channelAnalytics?.kpis || [];
  const trendData = channelAnalytics?.trendData || [];
  const heatmapData = channelAnalytics?.heatmapData || [];
  const comments = channelAnalytics?.comments || [];
  const topContent = channelAnalytics?.topContent || [];

  const channelContents = useMemo(() => {
    if (!selectedChannel?.id) {
      return filteredContents;
    }
    const ownContent = filteredContents.filter((item) => item.channelId === selectedChannel.id);
    return ownContent.length > 0 ? ownContent : topContent;
  }, [filteredContents, selectedChannel?.id, topContent]);

  const positiveRate = useMemo(() => {
    if (!comments.length) {
      return 0;
    }
    const positives = comments.filter((item) => item.sentiment === "positive").length;
    return Math.round((positives / comments.length) * 100);
  }, [comments]);

  if (!selectedChannel) {
    return (
      <Card className="flex min-h-[420px] items-center justify-center border-dashed border-white/10 bg-transparent">
        <div className="text-center">
          <h2 className="mb-2 text-xl font-semibold text-text-primary">Chưa có kênh để phân tích</h2>
          <p className="text-sm text-text-tertiary">Cần ít nhất một kênh đã kết nối để hiển thị analytics.</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="mb-2 flex items-center gap-2 text-sm text-text-tertiary">
        <span>{summary.groupName || "Workspace"}</span>
        <span>/</span>
        <span className="text-text-primary">{selectedChannel.name}</span>
      </div>

      <div className="flex flex-col items-start justify-between gap-4 border-b border-white/5 pb-6 md:flex-row md:items-center">
        <div className="flex items-center gap-5">
          <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-2xl border border-white/10 bg-obsidian-800 shadow-lg">
            <img src={selectedChannel.avatar} alt={selectedChannel.name} className="h-full w-full object-cover" />
          </div>
          <div>
            <div className="mb-1 flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-text-primary">{selectedChannel.name}</h1>
              <span className="rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-text-primary">
                {selectedChannel.platform}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-text-secondary">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-accent-emerald"></span>
                {summary.connectionLabel || "Kết nối ổn định"}
              </span>
              <span className="flex items-center gap-1.5">
                <RefreshCw className="h-3.5 w-3.5 text-text-tertiary" />
                Đồng bộ {selectedChannel.lastSync || summary.syncLabel || "vừa xong"}
              </span>
              <a href="#" className="flex items-center gap-1 text-accent-blue transition-colors hover:text-blue-400">
                {summary.handle || selectedChannel.handle}
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </div>
        </div>

        <div className="flex w-full items-center gap-3 md:w-auto">
          <button
            onClick={() => runChannelAction(selectedChannel.id, "sync")}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/10 bg-obsidian-800 px-4 py-2 font-medium text-text-primary transition-colors hover:bg-white/5 md:flex-none"
          >
            <RefreshCw className="h-4 w-4 text-text-secondary" />
            Đồng bộ lại
          </button>
          <button
            onClick={() => runChannelAction(selectedChannel.id, "reconnect")}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/10 bg-obsidian-800 px-4 py-2 font-medium text-text-primary transition-colors hover:bg-white/5 md:flex-none"
          >
            <Settings className="h-4 w-4 text-text-secondary" />
            Kết nối lại
          </button>
        </div>
      </div>

      <div className="flex flex-col items-start justify-between gap-4 xl:flex-row xl:items-center">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          options={[
            { label: "Tổng quan", value: "overview" },
            { label: "Nội dung", value: "content" },
            { label: "Tăng trưởng", value: "growth" },
            { label: "Khán giả", value: "audience" },
            { label: "Bình luận", value: "comments" },
          ]}
        />
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:bg-white/10 hover:text-text-primary">
            <CalendarRange className="h-4 w-4" />
            <span>30 ngày qua</span>
          </button>
          <button className="rounded-lg border border-white/10 bg-obsidian-800 px-3 py-1.5 text-sm font-medium transition-colors hover:border-white/20 hover:bg-white/5">
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>

      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
            {kpis.map((kpi: any) => (
              <Card key={kpi.label} className="p-4" interactive>
                <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-text-tertiary">{kpi.label}</div>
                <div className="mb-2 text-2xl font-bold text-white">{kpi.value}</div>
                <MetricChip
                  value={kpi.change}
                  trend={(kpi.trend || "up") as "up" | "down"}
                  variant={kpi.trend === "down" ? "warning" : "success"}
                  size="sm"
                />
              </Card>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader>
                <div>
                  <CardTitle>Xu hướng reach theo ngày</CardTitle>
                  <CardDescription>Biến động hiệu suất 30 ngày gần nhất của kênh đã chọn.</CardDescription>
                </div>
              </CardHeader>
              <div className="mt-4">
                <TrendChart data={trendData} />
              </div>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <div>
                    <CardTitle>Khung giờ tương tác</CardTitle>
                    <CardDescription>Dựa trên inbox và nhịp hoạt động gần đây của kênh.</CardDescription>
                  </div>
                </CardHeader>
                <div className="mt-4">
                  <HeatmapChart data={heatmapData} />
                </div>
              </Card>

              <Card className="bg-obsidian-800">
                <CardHeader className="mb-2">
                  <CardTitle className="flex items-center gap-2 text-base text-accent-blue">
                    <MessageSquare className="h-4 w-4" />
                    Bình luận cần xử lý
                  </CardTitle>
                </CardHeader>
                <div className="space-y-3">
                  {comments.slice(0, 3).map((item: any) => (
                    <div key={item.id} className="flex gap-3 text-sm">
                      <img src={item.authorAvatar} alt={item.authorName} className="h-8 w-8 shrink-0 rounded-full bg-obsidian-950" />
                      <div className="min-w-0 flex-1">
                        <div className="mb-0.5 font-medium text-text-primary">{item.authorName}</div>
                        <div className="line-clamp-2 text-xs text-text-secondary">{item.content}</div>
                      </div>
                    </div>
                  ))}
                  {!comments.length && <div className="text-sm text-text-tertiary">Chưa có bình luận mới trong giai đoạn này.</div>}
                </div>
              </Card>
            </div>
          </div>

          <div>
            <div className="mb-4">
              <h3 className="text-lg font-bold text-white">Nội dung nổi bật của kênh</h3>
              <p className="text-sm text-text-tertiary">Hiệu suất chi tiết của các bài đăng gắn với kênh hiện tại.</p>
            </div>
            <ContentDataTable data={channelContents} />
          </div>
        </div>
      )}

      {activeTab === "content" && <ContentDataTable data={channelContents} />}

      {activeTab === "growth" && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader>
              <div>
                <CardTitle>Tăng trưởng reach</CardTitle>
                <CardDescription>So sánh hiệu suất ngày hiện tại với chu kỳ gần nhất.</CardDescription>
              </div>
            </CardHeader>
            <div className="mt-4">
              <TrendChart data={trendData} />
            </div>
          </Card>
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Tóm tắt tăng trưởng</CardTitle>
                <CardDescription>Các chỉ số tổng hợp từ analytics của kênh.</CardDescription>
              </div>
            </CardHeader>
            <div className="space-y-4">
              <div className="rounded-xl border border-white/5 bg-obsidian-900 p-4">
                <div className="mb-1 text-xs uppercase tracking-wider text-text-tertiary">Reach kỳ gần nhất</div>
                <div className="text-2xl font-bold text-white">{summary.latestReach || 0}</div>
              </div>
              <div className="rounded-xl border border-white/5 bg-obsidian-900 p-4">
                <div className="mb-1 text-xs uppercase tracking-wider text-text-tertiary">Reach kỳ trước</div>
                <div className="text-2xl font-bold text-white">{summary.previousReach || 0}</div>
              </div>
              <div className="rounded-xl border border-white/5 bg-obsidian-900 p-4">
                <div className="mb-1 text-xs uppercase tracking-wider text-text-tertiary">Lượt xem video</div>
                <div className="text-2xl font-bold text-white">{summary.videoViews || 0}</div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {activeTab === "audience" && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <Card className="p-5">
            <div className="mb-2 flex items-center gap-2 text-sm text-text-secondary">
              <Users className="h-4 w-4" />
              Người theo dõi hiện tại
            </div>
            <div className="text-3xl font-bold text-white">{kpis.find((item: any) => item.label === "Followers")?.value || "0"}</div>
          </Card>
          <Card className="p-5">
            <div className="mb-2 flex items-center gap-2 text-sm text-text-secondary">
              <Video className="h-4 w-4" />
              Video views
            </div>
            <div className="text-3xl font-bold text-white">{kpis.find((item: any) => item.label === "Video Views")?.value || "0"}</div>
          </Card>
          <Card className="p-5">
            <div className="mb-2 flex items-center gap-2 text-sm text-text-secondary">
              <MessageSquare className="h-4 w-4" />
              Tỷ lệ tích cực
            </div>
            <div className="text-3xl font-bold text-white">{positiveRate}%</div>
          </Card>
        </div>
      )}

      {activeTab === "comments" && (
        <Card className="p-6">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-text-primary">Bình luận và tin nhắn liên quan</h3>
              <p className="text-sm text-text-tertiary">Danh sách mới nhất từ inbox của kênh này.</p>
            </div>
            <div className="rounded-lg bg-white/5 px-3 py-1 text-xs text-text-secondary">
              Tích cực: <span className="font-bold text-accent-emerald">{positiveRate}%</span>
            </div>
          </div>
          <div className="space-y-4">
            {comments.map((item: any) => (
              <div key={item.id} className="flex gap-4 rounded-xl border border-white/5 bg-obsidian-900 p-4">
                <img src={item.authorAvatar} alt={item.authorName} className="h-10 w-10 shrink-0 rounded-full bg-white/10" />
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-baseline justify-between">
                    <span className="text-sm font-semibold text-text-primary">{item.authorName}</span>
                    <span className="text-[10px] text-text-tertiary">{item.timestamp}</span>
                  </div>
                  <p className="mb-2 text-sm text-text-secondary">{item.content}</p>
                  <div className="text-xs text-text-tertiary">
                    {item.postTitle ? `Liên quan: ${item.postTitle}` : "Không gắn với bài đăng cụ thể"}
                  </div>
                </div>
              </div>
            ))}
            {!comments.length && <div className="text-sm text-text-tertiary">Chưa có hội thoại nào cho kênh này.</div>}
          </div>
        </Card>
      )}
    </div>
  );
}
