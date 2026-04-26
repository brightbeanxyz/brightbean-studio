import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { TrendChart } from "@/components/charts/TrendChart";
import { ChannelCard } from "@/components/ui/ChannelCard";
import { MetricChip } from "@/components/ui/MetricChip";
import { Tabs } from "@/components/ui/Tabs";
import { FilterBar } from "@/components/ui/FilterBar";
import { cn, formatCompactNumber } from "@/lib/utils";
import { Edit2, Users, Target, CalendarDays, ExternalLink, ArrowRight, Play, Trash2 } from "lucide-react";
import { useAppStore } from "@/store/AppContext";
import { ConnectChannelModal } from "@/components/ui/ConnectChannelModal";

export default function Portfolio() {
  const navigate = useNavigate();
  const { filteredChannels, filteredContents, posts, filters, groups, deleteChannel, trendData } = useAppStore();
  const [activeTab, setActiveTab] = useState("overview");
  const [isAddChannelModalOpen, setIsAddChannelModalOpen] = useState(false);

  const currentGroup = groups.find((group) => group.id === filters.group) || groups[0] || {
    id: "all",
    name: "Tất cả kênh (Workspace)",
    channelsCount: 0,
    followers: "0",
    health: "healthy",
    platforms: [],
    isPinned: true,
  };

  const totalFollowers = filteredChannels.reduce((acc, curr) => {
    let followers = curr.followers;
    if (typeof followers === "string") {
      if (followers.endsWith("M")) followers = parseFloat(followers) * 1000000;
      else if (followers.endsWith("K")) followers = parseFloat(followers) * 1000;
      else followers = parseFloat(followers);
    }
    return acc + (followers || 0);
  }, 0);

  const removeChannel = (id: string, name: string) => {
    if (!window.confirm(`Xóa kênh "${name}" khỏi nhóm hiện tại?`)) return;
    deleteChannel(id);
  };

  return (
    <div className="space-y-6">
      <div className="relative isolate flex flex-col items-start justify-between gap-6 overflow-hidden rounded-3xl border border-white/5 bg-obsidian-800 p-8 md:flex-row md:items-end">
        <div className="pointer-events-none absolute top-0 right-0 -z-10 h-full w-full bg-gradient-to-l from-accent-gold/5 via-accent-violet/5 to-transparent md:w-1/2" />
        <div className="pointer-events-none absolute -top-24 -right-12 -z-10 h-64 w-64 rounded-full bg-accent-gold/10 blur-[80px]" />

        <div className="flex items-start gap-6">
          <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-br from-obsidian-700 to-obsidian-900 p-1 shadow-[0_10px_40px_rgba(0,0,0,0.5)]">
            <div className="h-full w-full overflow-hidden rounded-xl">
              <img src="https://images.unsplash.com/photo-1560179707-f14e90ef3623?w=200&q=80" alt="Workspace" className="h-full w-full object-cover" />
            </div>
          </div>
          <div>
            <div className="mb-1 flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight text-text-primary">{currentGroup.name}</h1>
              <span className="rounded border border-accent-gold/20 bg-accent-gold/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-accent-gold">
                Brand Cluster
              </span>
            </div>
            <p className="mb-4 max-w-xl text-sm text-text-secondary">
              Cụm kênh chính thức dùng để theo dõi hiệu suất, xu hướng nội dung và tốc độ tăng trưởng hợp nhất theo nhóm.
            </p>
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-text-tertiary" />
                <span className="text-sm font-semibold text-text-primary">
                  {formatCompactNumber(totalFollowers)} <span className="font-normal text-text-secondary">Khán giả</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-text-tertiary" />
                <span className="text-sm font-semibold text-text-primary">
                  {filteredChannels.length} <span className="font-normal text-text-secondary">Kênh</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex w-full flex-col gap-3 md:w-auto">
          <button
            onClick={() => navigate("/settings")}
            className="flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-2 font-medium text-obsidian-950 shadow-lg transition-colors hover:bg-white/90"
          >
            <Edit2 className="h-4 w-4" />
            Chỉnh sửa nhóm
          </button>
          <button
            onClick={() => navigate("/manage")}
            className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-obsidian-950 px-4 py-2 font-medium text-text-primary transition-colors hover:bg-white/5"
          >
            <ExternalLink className="h-4 w-4 text-text-secondary" />
            Liên kết tài khoản mới
          </button>
        </div>
      </div>

      <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
        <Tabs
          value={activeTab}
          onValueChange={(value) => {
            if (value === "content") navigate("/content");
            else if (value === "platforms") navigate("/manage");
            else if (value === "settings") navigate("/settings");
            else setActiveTab(value);
          }}
          options={[
            { label: "Tổng quan chung", value: "overview" },
            { label: "Quản lý nội dung", value: "content" },
            { label: "Phân tích nền tảng", value: "platforms" },
            { label: "Thiết lập nhóm", value: "settings" },
          ]}
        />
        <FilterBar className="border-0 bg-transparent p-0 backdrop-blur-none" />
      </div>

      <Card className="flex-none">
        <CardHeader className="mb-4 flex flex-row items-center justify-between border-b border-white/5 pb-4">
          <CardTitle>{filteredChannels.length} Kênh thành viên</CardTitle>
        </CardHeader>
        <div className="hide-scrollbar flex flex-row gap-4 overflow-x-auto pb-4 snap-x">
          {filteredChannels.map((channel) => (
            <div key={channel.id} className="group relative min-w-[280px] snap-center">
              <button
                onClick={() => removeChannel(channel.id, channel.name)}
                className="absolute -top-2 -right-2 z-10 hidden rounded-full border border-obsidian-950 bg-red-500 p-1.5 shadow-md transition-opacity hover:bg-red-600 group-hover:block"
                title="Xóa kênh"
              >
                <Trash2 className="h-3 w-3 text-white" />
              </button>
              <ChannelCard {...channel} platform={channel.platform as any} status={channel.status as any} />
            </div>
          ))}
        </div>
        <button
          onClick={() => setIsAddChannelModalOpen(true)}
          className="mt-2 w-full rounded-xl border border-dashed border-white/20 py-2.5 text-sm text-text-tertiary transition-all hover:border-white/40 hover:bg-white/5 hover:text-text-primary"
        >
          + Thêm kênh mới vào nhóm
        </button>
      </Card>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-4">
        <div className="space-y-6 xl:col-span-3">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[
              { label: "Reach nhom", value: "8.2M", diff: "+14%", trend: "up" },
              { label: "Tương tác nhóm", value: "1.05M", diff: "+5%", trend: "up" },
              { label: "Lượt xem video", value: "12.4M", diff: "-2%", trend: "down" },
              { label: "Lượt click link", value: "45.2K", diff: "+22%", trend: "up" },
            ].map((kpi, index) => (
              <Card key={index} className="p-4" interactive>
                <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-text-tertiary">{kpi.label}</div>
                <div className="mb-2 text-2xl font-bold text-white">{kpi.value}</div>
                <MetricChip value={kpi.diff} trend={kpi.trend as "up" | "down"} variant={kpi.trend === "up" ? "success" : "warning"} size="sm" />
              </Card>
            ))}
          </div>

          <Card className="flex min-h-[350px] flex-col">
            <CardHeader>
              <div>
                <CardTitle>Tăng trưởng nhóm: Tương tác và phân phối</CardTitle>
                <CardDescription>Biểu đồ hợp nhất dữ liệu từ tất cả kênh trong nhóm đã chọn.</CardDescription>
              </div>
            </CardHeader>
            <div className="mt-2 ml-[-0.5rem] flex-1">
              <TrendChart data={trendData} />
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-6">
            <Card>
              <CardHeader className="mb-4">
                <div className="flex w-full items-center justify-between">
                  <div>
                    <CardTitle>Top nội dung của nhóm</CardTitle>
                    <CardDescription>Nội dung dẫn dắt tăng trưởng</CardDescription>
                  </div>
                  <button className="flex items-center text-xs font-semibold text-accent-blue">
                    Toàn bộ <ArrowRight className="ml-1 h-3 w-3" />
                  </button>
                </div>
              </CardHeader>
              <div className="space-y-4">
                {filteredContents.slice(0, 4).map((item) => (
                  <div key={item.id} className="group flex cursor-pointer items-center gap-3">
                    <div className="relative h-10 w-16 overflow-hidden rounded border border-white/5 bg-obsidian-900">
                      <img src={item.thumbnail} className="h-full w-full object-cover transition-opacity group-hover:opacity-80" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <div className="truncate text-sm font-medium text-text-primary transition-colors group-hover:text-accent-blue">{item.title}</div>
                      <div className="text-xs capitalize text-text-tertiary">
                        {item.platform} · {formatCompactNumber(item.reach)} reach
                      </div>
                    </div>
                    <div className="rounded bg-accent-emerald/10 px-2 py-0.5 font-mono text-xs text-accent-emerald">
                      {formatCompactNumber(item.engagement)}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>

        <div className="flex h-full flex-col space-y-6">
          <Card>
            <CardHeader className="mb-4">
              <CardTitle className="flex items-center gap-2">
                <CalendarDays className="h-4 w-4 text-text-tertiary" /> Lịch đăng nhóm
              </CardTitle>
            </CardHeader>
            <div className="space-y-3">
              {posts.slice(0, 4).map((post) => (
                <div key={post.id} className="flex gap-3 rounded-lg border border-white/[0.02] bg-white/[0.02] p-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-white/5 bg-obsidian-950 shadow-inner">
                    <Play className={cn("h-3.5 w-3.5", post.platform === "youtube" ? "text-red-500" : post.platform === "tiktok" ? "text-cyan-500" : "text-blue-500")} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-text-primary">{post.title}</div>
                    <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-text-tertiary">
                      {post.time}
                      <span className="h-1 w-1 rounded-full bg-white/20" />
                      <span className={cn("rounded bg-obsidian-950 px-1", post.status === "scheduled" ? "text-accent-emerald" : "text-yellow-500")}>
                        {post.status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {isAddChannelModalOpen && <ConnectChannelModal onClose={() => setIsAddChannelModalOpen(false)} defaultGroupId={currentGroup.id} />}
    </div>
  );
}
