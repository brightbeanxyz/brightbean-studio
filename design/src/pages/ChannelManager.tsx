import { useMemo, useState } from "react";
import {
  Plus,
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  LayoutGrid,
  List as ListIcon,
  Trash2,
  Power,
  Globe,
  FolderPlus,
  Link2,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { useAppStore } from "@/store/AppContext";
import { cn } from "@/lib/utils";
import { EmptyState } from "@/components/ui/EmptyState";
import { ConnectChannelModal } from "@/components/ui/ConnectChannelModal";

type ViewMode = "grid" | "list";
type StatusFilter = "all" | "connected" | "error";

export default function ChannelManager() {
  const {
    channels,
    filteredChannels,
    filters,
    setFilters,
    groups,
    runChannelAction,
    deleteChannel,
    addAlert,
    setIsManageGroupsModalOpen,
  } = useAppStore();

  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [isAddChannelModalOpen, setIsAddChannelModalOpen] = useState(false);
  const [busyChannelId, setBusyChannelId] = useState<string | null>(null);

  const selectedGroup = filters.group;
  const setSelectedGroup = (id: string) => setFilters({ group: id });

  const channelGroups = groups.map((group) => ({
    id: group.id,
    name: group.name,
    count: group.id === "all" ? channels.length : channels.filter((channel) => channel.groupId === group.id).length,
  }));

  const visibleChannels = useMemo(() => {
    return filteredChannels.filter((channel) => {
      const haystack = `${channel.name || ""} ${channel.handle || ""}`.toLowerCase();
      const searchMatch = !searchTerm || haystack.includes(searchTerm.toLowerCase());
      const statusMatch =
        statusFilter === "all" ||
        (statusFilter === "connected" && channel.status === "connected") ||
        (statusFilter === "error" && channel.status !== "connected");
      return searchMatch && statusMatch;
    });
  }, [filteredChannels, searchTerm, statusFilter]);

  const totalAudience = useMemo(() => {
    return visibleChannels.reduce((sum, channel) => {
      const numeric = Number(String(channel.followers || 0).replace(/[^\d.]/g, "")) || 0;
      return sum + numeric;
    }, 0);
  }, [visibleChannels]);

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case "youtube":
        return <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-red-500/20 text-xs font-bold text-red-500">Y</div>;
      case "tiktok":
        return <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-cyan-500/20 text-xs font-bold text-cyan-500">T</div>;
      case "facebook":
        return <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-blue-500/20 text-xs font-bold text-blue-500">F</div>;
      default:
        return <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/10 text-xs font-bold text-white">?</div>;
    }
  };

  const getStatusColor = (status: string) => {
    if (status === "connected") return "border-accent-emerald/20 bg-accent-emerald/10 text-accent-emerald";
    if (status === "disconnected" || status === "error") return "border-red-500/20 bg-red-500/10 text-red-500";
    return "border-accent-gold/20 bg-accent-gold/10 text-accent-gold";
  };

  const handleChannelAction = async (channelId: string, action: "sync" | "reconnect") => {
    try {
      setBusyChannelId(channelId);
      runChannelAction(channelId, action);
    } finally {
      window.setTimeout(() => setBusyChannelId((current) => (current === channelId ? null : current)), 1200);
    }
  };

  const handleDeleteChannel = (channelId: string, channelName: string) => {
    const confirmed = window.confirm(`Xóa kênh "${channelName}" khỏi workspace?`);
    if (!confirmed) return;
    deleteChannel(channelId);
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="mb-6 flex shrink-0 flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="mb-1 text-3xl font-bold tracking-tight text-text-primary">Quản lý kênh</h1>
          <p className="text-text-secondary">Theo dõi kết nối, sức khỏe đồng bộ và cấu trúc kênh trong workspace.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="mr-2 flex rounded-xl border border-white/5 bg-obsidian-800 p-1">
            <button
              onClick={() => setViewMode("grid")}
              className={cn("rounded-lg p-1.5 transition-all", viewMode === "grid" ? "bg-obsidian-600 text-text-primary shadow-sm" : "text-text-secondary hover:text-text-primary")}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={cn("rounded-lg p-1.5 transition-all", viewMode === "list" ? "bg-obsidian-600 text-text-primary shadow-sm" : "text-text-secondary hover:text-text-primary")}
            >
              <ListIcon className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={() => setIsManageGroupsModalOpen(true)}
            className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-obsidian-900 px-4 py-2 font-medium text-text-primary transition-colors hover:bg-white/5"
          >
            <FolderPlus className="h-4 w-4" />
            Quản lý nhóm
          </button>
          <button
            onClick={() => setIsAddChannelModalOpen(true)}
            className="flex items-center justify-center gap-2 rounded-xl bg-text-primary px-4 py-2 font-medium text-obsidian-950 transition-colors hover:bg-white"
          >
            <Plus className="h-4 w-4" />
            Thêm kênh mới
          </button>
        </div>
      </div>

      <div className="mb-6 grid shrink-0 grid-cols-2 gap-4 lg:grid-cols-4">
        <Card className="flex flex-col justify-center bg-obsidian-900/50 p-4">
          <div className="mb-1 text-xs font-medium uppercase tracking-wider text-text-tertiary">Tổng kênh</div>
          <div className="text-2xl font-bold text-white">{visibleChannels.length}</div>
        </Card>
        <Card className="flex flex-col justify-center bg-obsidian-900/50 p-4">
          <div className="mb-1 text-xs font-medium uppercase tracking-wider text-text-tertiary">Đang hoạt động</div>
          <div className="text-2xl font-bold text-accent-emerald">
            {visibleChannels.filter((channel) => channel.status === "connected").length}
          </div>
        </Card>
        <Card className="flex flex-col justify-center bg-obsidian-900/50 p-4">
          <div className="mb-1 flex items-center justify-between">
            <div className="text-xs font-medium uppercase tracking-wider text-text-tertiary">Cần xử lý</div>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </div>
          <div className="text-2xl font-bold text-red-500">
            {visibleChannels.filter((channel) => channel.status !== "connected").length}
          </div>
        </Card>
        <Card className="relative flex flex-col justify-center overflow-hidden bg-obsidian-900/50 p-4">
          <div className="absolute -bottom-4 -right-4 h-24 w-24 rounded-full bg-accent-blue/10 blur-xl" />
          <div className="relative z-10 mb-1 text-xs font-medium uppercase tracking-wider text-text-tertiary">Tệp audience hợp nhất</div>
          <div className="relative z-10 text-2xl font-bold text-white">{totalAudience.toLocaleString()}</div>
        </Card>
      </div>

      <div className="flex min-h-0 flex-1 gap-6 overflow-hidden">
        <div className="flex w-64 shrink-0 flex-col gap-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">Nhóm kênh</h3>
            <button
              onClick={() => setIsManageGroupsModalOpen(true)}
              className="rounded p-1 text-text-tertiary transition-colors hover:bg-white/10"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-1">
            {channelGroups.map((group) => (
              <button
                key={group.id}
                onClick={() => setSelectedGroup(group.id)}
                className={cn(
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors",
                  selectedGroup === group.id ? "bg-accent-blue/10 font-medium text-accent-blue" : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
                )}
              >
                <span className="truncate pr-4">{group.name}</span>
                <span className={cn("rounded px-1.5 py-0.5 font-mono text-xs", selectedGroup === group.id ? "bg-accent-blue/20" : "bg-white/5 text-text-tertiary")}>
                  {group.count}
                </span>
              </button>
            ))}
          </div>

          <div className="mt-8 border-t border-white/5 pt-6">
            <h3 className="mb-3 px-2 text-xs font-semibold uppercase tracking-wider text-text-tertiary">Lọc theo nền tảng</h3>
            <div className="space-y-1">
              <button
                onClick={() => setFilters({ platforms: [] })}
                className={cn(
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors",
                  filters.platforms.length === 0 ? "bg-accent-blue/10 font-medium text-accent-blue" : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
                )}
              >
                <div className="flex items-center gap-3">
                  <Globe className="h-4 w-4" />
                  <span className="truncate">Tất cả nền tảng</span>
                </div>
              </button>
              {["facebook", "youtube", "tiktok"].map((platform) => (
                <button
                  key={platform}
                  onClick={() => setFilters({ platforms: [platform] })}
                  className={cn(
                    "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors",
                    filters.platforms.includes(platform) ? "bg-accent-blue/10 font-medium text-accent-blue" : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
                  )}
                >
                  <div className="flex items-center gap-3">
                    {getPlatformIcon(platform)}
                    <span className="truncate capitalize">{platform}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div className="relative w-72">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <Search className="h-4 w-4 text-text-tertiary" />
              </div>
              <input
                type="text"
                placeholder="Tìm tên kênh, handle..."
                className="w-full rounded-xl border border-white/10 bg-obsidian-900 py-2 pl-9 pr-4 text-sm transition-all focus:border-accent-blue focus:outline-none focus:ring-1 focus:ring-accent-blue hover:bg-obsidian-800"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-obsidian-800 px-3 py-2 text-sm text-text-secondary">
                <Filter className="h-4 w-4" />
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
                  className="bg-transparent text-sm text-text-primary outline-none"
                >
                  <option value="all">Tất cả trạng thái</option>
                  <option value="connected">Đang hoạt động</option>
                  <option value="error">Cần xử lý</option>
                </select>
              </div>
            </div>
          </div>

          <div className="custom-scrollbar flex-1 overflow-y-auto pr-2">
            {channels.length === 0 ? (
              <EmptyState
                icon={Link2}
                glowColor="blue"
                title="Chưa kết nối kênh nào"
                description="Quản lý tập trung mọi tài sản mạng xã hội. Thêm kênh đầu tiên để bắt đầu thu thập dữ liệu."
                action={
                  <button
                    onClick={() => setIsAddChannelModalOpen(true)}
                    className="rounded-xl bg-text-primary px-4 py-2 text-sm font-medium text-obsidian-950 transition-colors hover:bg-white"
                  >
                    Kết nối kênh mới
                  </button>
                }
              />
            ) : visibleChannels.length === 0 ? (
              <EmptyState
                icon={Search}
                title="Không có kết quả lọc"
                description="Không tìm thấy kênh nào khớp với bộ lọc hiện tại. Thử đổi nhóm, nền tảng hoặc trạng thái."
                action={
                  <button
                    onClick={() => {
                      setSearchTerm("");
                      setStatusFilter("all");
                    }}
                    className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-white/5"
                  >
                    Xóa bộ lọc cục bộ
                  </button>
                }
                secondaryAction={
                  <button
                    onClick={() => {
                      setFilters({ platforms: [], group: "all" });
                      setSearchTerm("");
                      setStatusFilter("all");
                    }}
                    className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-white/5"
                  >
                    Đặt lại tất cả
                  </button>
                }
              />
            ) : viewMode === "grid" ? (
              <div className="space-y-8 pb-12">
                {["facebook", "youtube", "tiktok"].map((platform) => {
                  const platformChannels = visibleChannels.filter((channel) => channel.platform === platform);
                  if (platformChannels.length === 0) return null;

                  return (
                    <div key={platform} className="animate-in fade-in slide-in-from-bottom-2">
                      <div className="mb-4 flex items-center gap-3 border-b border-white/5 pb-2">
                        {getPlatformIcon(platform)}
                        <h3 className="text-lg font-bold capitalize text-white">{platform}</h3>
                        <span className="rounded-md bg-white/5 px-2 py-0.5 font-mono text-xs text-text-tertiary">{platformChannels.length}</span>
                      </div>
                      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                        {platformChannels.map((channel) => {
                          const needsReconnect = channel.status !== "connected";
                          const isBusy = busyChannelId === channel.id;

                          return (
                            <Card
                              key={channel.id}
                              className="group flex flex-col overflow-hidden border border-white/5 bg-obsidian-900/60 p-0 shadow-none transition-all hover:border-white/20 hover:bg-obsidian-800/80 hover:shadow-hover-elevation"
                            >
                              <div className="flex items-start justify-between p-5">
                                <div className="flex items-center gap-4">
                                  <div className="relative h-14 w-14 overflow-hidden rounded-2xl border border-white/10 bg-obsidian-950 shadow-sm ring-2 ring-transparent transition-all group-hover:ring-white/10">
                                    <img src={channel.avatar} alt={channel.name} className="h-full w-full object-cover" />
                                  </div>
                                  <div>
                                    <div className="mb-0.5 line-clamp-1 text-base font-semibold text-text-primary transition-colors group-hover:text-accent-blue">
                                      {channel.name}
                                    </div>
                                    <div className="flex items-center gap-2 text-sm text-text-secondary">
                                      <span className="max-w-[140px] truncate">{channel.handle || "Không có handle"}</span>
                                      <span className="h-1 w-1 shrink-0 rounded-full bg-white/20" />
                                      <span className="rounded bg-white/5 px-1.5 font-mono text-xs text-text-primary">{channel.followers}</span>
                                    </div>
                                  </div>
                                </div>
                              </div>

                              <div className="border-t border-white/5 bg-obsidian-950/30 px-5 py-4">
                                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                                  <div className={cn("flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-semibold", getStatusColor(channel.status))}>
                                    {needsReconnect ? <AlertCircle className="h-3.5 w-3.5" /> : <Power className="h-3.5 w-3.5" />}
                                    {needsReconnect ? "Cần kết nối lại" : "API đã kết nối"}
                                  </div>
                                  <div className="flex items-center gap-1.5 text-[11px] font-medium text-text-tertiary">
                                    <RefreshCw className={cn("h-3 w-3 opacity-60", isBusy && "animate-spin")} />
                                    Sync: {channel.lastSync}
                                  </div>
                                </div>

                                <div className="flex flex-wrap gap-2">
                                  <button
                                    onClick={() => handleChannelAction(channel.id, "sync")}
                                    className="rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:bg-white/5"
                                  >
                                    Đồng bộ ngay
                                  </button>
                                  <button
                                    onClick={() => handleChannelAction(channel.id, "reconnect")}
                                    className="rounded-lg border border-accent-gold/20 bg-accent-gold/10 px-3 py-1.5 text-xs font-medium text-accent-gold transition-colors hover:bg-accent-gold/20"
                                  >
                                    Kết nối lại
                                  </button>
                                  <button
                                    onClick={() => handleDeleteChannel(channel.id, channel.name)}
                                    className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-500 transition-colors hover:bg-red-500/20"
                                  >
                                    Xóa kênh
                                  </button>
                                </div>
                              </div>
                            </Card>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <Card className="overflow-hidden border border-white/5 p-0">
                <table className="w-full whitespace-nowrap text-left text-sm">
                  <thead className="sticky top-0 z-10 border-b border-white/5 bg-obsidian-900/80 backdrop-blur-md">
                    <tr>
                      <th className="px-5 py-3 font-medium text-text-tertiary">Kênh</th>
                      <th className="px-5 py-3 font-medium text-text-tertiary">Nền tảng</th>
                      <th className="px-5 py-3 font-medium text-text-tertiary">Khán giả</th>
                      <th className="px-5 py-3 font-medium text-text-tertiary">Trạng thái API</th>
                      <th className="px-5 py-3 font-medium text-text-tertiary">Hành động</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {visibleChannels.map((channel) => {
                      const isBusy = busyChannelId === channel.id;
                      const needsReconnect = channel.status !== "connected";

                      return (
                        <tr key={channel.id} className="group transition-colors hover:bg-white/[0.02]">
                          <td className="px-5 py-3">
                            <div className="flex items-center gap-3">
                              <div className="h-10 w-10 shrink-0 overflow-hidden rounded-lg border border-white/10 shadow-sm">
                                <img src={channel.avatar} alt={channel.name} className="h-full w-full object-cover" />
                              </div>
                              <div>
                                <div className="font-medium text-text-primary transition-colors group-hover:text-accent-blue">{channel.name}</div>
                                <div className="text-xs text-text-secondary">{channel.handle || "Không có handle"}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-5 py-3">
                            <div className="flex items-center gap-2">
                              {getPlatformIcon(channel.platform)}
                              <span className="capitalize">{channel.platform}</span>
                            </div>
                          </td>
                          <td className="px-5 py-3 font-mono text-text-secondary">{channel.followers}</td>
                          <td className="px-5 py-3">
                            <div className={cn("inline-flex rounded border px-2 py-0.5 text-xs font-medium", getStatusColor(channel.status))}>
                              {needsReconnect ? "Cần xử lý" : "OK"}
                            </div>
                            <div className="mt-1 flex items-center gap-1 text-[10px] text-text-tertiary">
                              <RefreshCw className={cn("h-3 w-3", isBusy && "animate-spin")} />
                              Sync {channel.lastSync}
                            </div>
                          </td>
                          <td className="px-5 py-3">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleChannelAction(channel.id, "sync")}
                                className="rounded border border-white/10 p-1.5 text-text-tertiary transition-colors hover:bg-white/10 hover:text-text-primary"
                                title="Đồng bộ ngay"
                              >
                                <RefreshCw className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => handleChannelAction(channel.id, "reconnect")}
                                className="rounded border border-white/10 p-1.5 text-text-tertiary transition-colors hover:bg-white/10 hover:text-text-primary"
                                title="Kết nối lại"
                              >
                                <Link2 className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => handleDeleteChannel(channel.id, channel.name)}
                                className="rounded border border-red-500/20 p-1.5 text-text-tertiary transition-colors hover:bg-red-500/20 hover:text-red-500"
                                title="Xóa kênh"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </Card>
            )}
          </div>
        </div>
      </div>

      {isAddChannelModalOpen && <ConnectChannelModal onClose={() => setIsAddChannelModalOpen(false)} defaultGroupId={selectedGroup} />}
    </div>
  );
}
