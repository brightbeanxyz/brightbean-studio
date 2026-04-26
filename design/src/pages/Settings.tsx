import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Bell, Globe, KeySquare, Plus, RefreshCw, Shield, User } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/AppContext";
import { ConnectChannelModal } from "@/components/ui/ConnectChannelModal";

type SettingsTab = "integrations" | "token-alerts" | "profile" | "notifications" | "users" | "security" | "apikeys";
type Platform = "facebook" | "youtube" | "tiktok";
type IntegrationFilter = "all" | "expiring" | "reconnect";

const PLATFORM_META: Record<Platform, { title: string; description: string; badge: string; icon: string }> = {
  facebook: {
    title: "Facebook Graph API",
    description: "Đồng bộ fanpage, bài đăng gần đây và tín hiệu tương tác.",
    badge: "bg-blue-500/20 text-blue-400",
    icon: "F",
  },
  youtube: {
    title: "YouTube Data API",
    description: "Đồng bộ kênh, video, lượt xem, bình luận và analytics tổng hợp.",
    badge: "bg-red-500/20 text-red-400",
    icon: "Y",
  },
  tiktok: {
    title: "TikTok API",
    description: "Đồng bộ hồ sơ creator, video gần đây và chỉ số short-form.",
    badge: "bg-cyan-500/20 text-cyan-400",
    icon: "T",
  },
};

function tokenBadgeClass(severity?: string) {
  if (severity === "error") return "border-red-500/20 bg-red-500/10 text-red-400";
  if (severity === "warning") return "border-amber-500/20 bg-amber-500/10 text-amber-300";
  return "border-emerald-500/20 bg-emerald-500/10 text-emerald-300";
}

function formatExpiry(value?: string | null) {
  if (!value) return "Không có thời hạn rõ ràng";
  return new Date(value).toLocaleString("vi-VN");
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("integrations");
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [integrationFilter, setIntegrationFilter] = useState<IntegrationFilter>("all");
  const [tokenAlertPlatformFilter, setTokenAlertPlatformFilter] = useState<"all" | Platform>("all");
  const { channels, user, systemUsers, addAlert, saveSettings, runChannelAction, deleteChannel, settings } = useAppStore();

  const [emailNotif, setEmailNotif] = useState(true);
  const [pushNotif, setPushNotif] = useState(true);
  const [alertNotif, setAlertNotif] = useState(true);
  const [profileName, setProfileName] = useState("");
  const [profileEmail, setProfileEmail] = useState("");

  useEffect(() => {
    const notifications = settings?.notifications;
    if (!notifications) return;
    setEmailNotif(notifications.email ?? true);
    setPushNotif(notifications.push ?? true);
    setAlertNotif(notifications.alerts ?? true);
  }, [settings]);

  useEffect(() => {
    setProfileName(user?.name || "");
    setProfileEmail(user?.email || "");
  }, [user]);

  const connectedPlatforms = useMemo(
    () => ({
      facebook: channels.filter((channel) => channel.platform === "facebook"),
      youtube: channels.filter((channel) => channel.platform === "youtube"),
      tiktok: channels.filter((channel) => channel.platform === "tiktok"),
    }),
    [channels],
  );

  const integrationCounts = useMemo(
    () => ({
      all: channels.length,
      expiring: channels.filter((item) => ["expiring", "expiring_refreshable", "expired_refreshable"].includes(item.tokenHealth?.status)).length,
      reconnect: channels.filter((item) => item.reconnectRequired || item.connectionStatus !== "connected" || ["expired", "reconnect_required", "missing"].includes(item.tokenHealth?.status)).length,
    }),
    [channels],
  );

  const tokenAlertChannels = useMemo(
    () =>
      channels.filter(
        (item) =>
          item.missingScopes?.length > 0 ||
          item.reconnectRequired ||
          item.connectionStatus !== "connected" ||
          ["expiring", "expiring_refreshable", "expired", "expired_refreshable", "reconnect_required", "missing"].includes(item.tokenHealth?.status),
      ),
    [channels],
  );

  const filteredTokenAlertChannels = useMemo(
    () =>
      tokenAlertPlatformFilter === "all"
        ? tokenAlertChannels
        : tokenAlertChannels.filter((item) => item.platform === tokenAlertPlatformFilter),
    [tokenAlertChannels, tokenAlertPlatformFilter],
  );

  const filterIntegrationItems = (items: any[]) => {
    if (integrationFilter === "expiring") {
      return items.filter((item) => ["expiring", "expiring_refreshable", "expired_refreshable"].includes(item.tokenHealth?.status));
    }
    if (integrationFilter === "reconnect") {
      return items.filter((item) => item.reconnectRequired || item.connectionStatus !== "connected" || ["expired", "reconnect_required", "missing"].includes(item.tokenHealth?.status));
    }
    return items;
  };

  const scopeChip = (scope: string, tone: "neutral" | "danger" = "neutral") => (
    <span
      key={scope}
      className={cn(
        "rounded-lg border px-2 py-1 text-[11px] font-medium",
        tone === "danger" ? "border-red-500/20 bg-red-500/10 text-red-300" : "border-white/10 bg-white/5 text-text-secondary",
      )}
    >
      {scope}
    </span>
  );

  const handleDeleteChannel = (channelId: string, channelName: string) => {
    if (!window.confirm(`Xóa kết nối của kênh "${channelName}" khỏi workspace?`)) return;
    deleteChannel(channelId);
  };

  const renderChannelCard = (channel: any) => (
    <div key={channel.id} className="rounded-2xl border border-white/5 bg-obsidian-950/40 p-5">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex items-start gap-4">
          <img src={channel.avatar} alt={channel.name} className="h-12 w-12 rounded-full border border-white/10 object-cover" />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-base font-semibold text-white">{channel.name}</div>
              <span className={cn("rounded-lg border px-2.5 py-1 text-xs font-semibold", tokenBadgeClass(channel.tokenHealth?.severity))}>
                {channel.tokenHealth?.label || "Không rõ"}
              </span>
              <span className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-semibold text-text-secondary">
                {channel.platform}
              </span>
              {channel.reconnectRequired && (
                <span className="rounded-lg border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-xs font-semibold text-red-400">
                  Cần kết nối lại
                </span>
              )}
            </div>
            <div className="mt-1 text-sm text-text-secondary">{channel.handle || channel.nativeId}</div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => runChannelAction(channel.id, "sync")}
            className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-white/5"
          >
            Đồng bộ ngay
          </button>
          <button
            onClick={() => runChannelAction(channel.id, "reconnect")}
            className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-2 text-sm font-medium text-amber-300 transition-colors hover:bg-amber-500/20"
          >
            Kết nối lại
          </button>
          <button
            onClick={() => handleDeleteChannel(channel.id, channel.name)}
            className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/20"
          >
            Xóa
          </button>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-text-tertiary">Tài khoản cấp quyền</div>
          <div className="mt-1 text-sm text-white">{channel.authAccountLabel || "Chưa ghi nhận"}</div>
          <div className="mt-1 text-xs text-text-secondary">{channel.authAccountId || "Không có ID nguồn"}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-text-tertiary">Phương thức kết nối</div>
          <div className="mt-1 text-sm text-white">{channel.connectionMethod === "oauth" ? "OAuth chính thức" : "Nhập token thủ công"}</div>
          <div className="mt-1 text-xs text-text-secondary">{channel.groupName || "Chưa phân nhóm"}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-text-tertiary">Token</div>
          <div className="mt-1 text-sm text-white">{channel.hasRefreshToken ? "Có refresh token" : "Không có refresh token"}</div>
          <div className="mt-1 text-xs text-text-secondary">Hết hạn: {formatExpiry(channel.tokenExpiresAt)}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-text-tertiary">Đồng bộ gần nhất</div>
          <div className="mt-1 text-sm text-white">{channel.lastSync}</div>
          <div className="mt-1 text-xs text-text-secondary">{channel.connectedByName ? `Kết nối bởi ${channel.connectedByName}` : "Không rõ người kết nối"}</div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-xl border border-white/5 bg-obsidian-950/50 p-4">
          <div className="text-xs uppercase tracking-wider text-text-tertiary">Scope bắt buộc</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(channel.requiredScopes || []).length > 0 ? (channel.requiredScopes || []).map((scope: string) => scopeChip(scope)) : <span className="text-sm text-text-secondary">Chưa có cấu hình scope.</span>}
          </div>
        </div>
        <div className="rounded-xl border border-white/5 bg-obsidian-950/50 p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs uppercase tracking-wider text-text-tertiary">Scope hiện có</div>
            <span className={cn("rounded-full px-2.5 py-1 text-[11px] font-semibold", (channel.missingScopes || []).length > 0 ? "bg-red-500/10 text-red-300" : "bg-emerald-500/10 text-emerald-300")}>
              {(channel.missingScopes || []).length > 0 ? `Thiếu ${(channel.missingScopes || []).length}` : "Đủ quyền"}
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(channel.grantedScopes || []).length > 0 ? (channel.grantedScopes || []).map((scope: string) => scopeChip(scope)) : <span className="text-sm text-text-secondary">Token chưa khai báo scope.</span>}
          </div>
          {(channel.missingScopes || []).length > 0 && (
            <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3">
              <div className="text-xs uppercase tracking-wider text-amber-200">Scope đang thiếu</div>
              <div className="mt-2 flex flex-wrap gap-2">{(channel.missingScopes || []).map((scope: string) => scopeChip(scope, "danger"))}</div>
              <div className="mt-3 text-sm text-amber-100">Cần kết nối lại kênh này để cấp lại token với đầy đủ quyền.</div>
            </div>
          )}
        </div>
      </div>

      {(channel.lastError || channel.tokenHealth?.description) && (
        <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
          {channel.lastError || channel.tokenHealth?.description}
        </div>
      )}
    </div>
  );

  const platformCard = (platform: Platform) => {
    const meta = PLATFORM_META[platform];
    const items = filterIntegrationItems(connectedPlatforms[platform]);
    const baseItems = connectedPlatforms[platform];
    const healthy = baseItems.filter((item) => !item.reconnectRequired && item.connectionStatus === "connected").length;
    const warning = baseItems.filter((item) => item.tokenHealth?.severity === "warning").length;
    const reconnect = baseItems.filter((item) => item.reconnectRequired || item.connectionStatus !== "connected").length;

    return (
      <Card key={platform} className="border border-white/5 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className={cn("flex h-14 w-14 items-center justify-center rounded-2xl text-xl font-bold", meta.badge)}>{meta.icon}</div>
            <div>
              <h3 className="text-lg font-bold text-text-primary">{meta.title}</h3>
              <p className="mt-1 text-sm text-text-secondary">{meta.description}</p>
            </div>
          </div>
          <button
            onClick={() => setIsConnectModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-obsidian-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white hover:text-black"
          >
            <Plus className="h-4 w-4" />
            Thêm kết nối
          </button>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-white/5 bg-obsidian-950/60 p-4">
            <div className="text-xs uppercase tracking-wider text-text-tertiary">Kênh đang hoạt động</div>
            <div className="mt-2 text-2xl font-bold text-emerald-300">{healthy}</div>
          </div>
          <div className="rounded-xl border border-white/5 bg-obsidian-950/60 p-4">
            <div className="text-xs uppercase tracking-wider text-text-tertiary">Token cần theo dõi</div>
            <div className="mt-2 text-2xl font-bold text-amber-300">{warning}</div>
          </div>
          <div className="rounded-xl border border-white/5 bg-obsidian-950/60 p-4">
            <div className="text-xs uppercase tracking-wider text-text-tertiary">Cần kết nối lại</div>
            <div className="mt-2 text-2xl font-bold text-red-400">{reconnect}</div>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          {items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 bg-obsidian-950/40 p-4 text-sm text-text-secondary">
              Không có kênh nào khớp với bộ lọc hiện tại trên nền tảng này.
            </div>
          ) : (
            items.map(renderChannelCard)
          )}
        </div>
      </Card>
    );
  };

  const renderIntegrations = () => (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-primary">Quản lý kết nối kênh</h2>
          <p className="mt-1 text-sm text-text-secondary">
            Theo dõi token, trạng thái kết nối, tài khoản đã cấp quyền và các kênh đang đồng bộ trên từng nền tảng.
          </p>
        </div>
        <button
          onClick={() => setIsConnectModalOpen(true)}
          className="inline-flex items-center gap-2 rounded-xl bg-text-primary px-4 py-2 text-sm font-semibold text-obsidian-950 transition-colors hover:bg-white"
        >
          <Plus className="h-4 w-4" />
          Kết nối kênh mới
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          { id: "all", label: "Tất cả", count: integrationCounts.all },
          { id: "expiring", label: "Sắp hết hạn", count: integrationCounts.expiring },
          { id: "reconnect", label: "Cần kết nối lại", count: integrationCounts.reconnect },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => setIntegrationFilter(item.id as IntegrationFilter)}
            className={cn(
              "inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition-colors",
              integrationFilter === item.id ? "border-accent-blue bg-accent-blue/10 text-accent-blue" : "border-white/10 bg-obsidian-950 text-text-secondary hover:text-white",
            )}
          >
            {item.label}
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", integrationFilter === item.id ? "bg-accent-blue/20 text-accent-blue" : "bg-white/10 text-text-secondary")}>
              {item.count}
            </span>
          </button>
        ))}
      </div>

      {(["facebook", "youtube", "tiktok"] as Platform[]).map(platformCard)}
    </div>
  );

  const renderTokenAlerts = () => (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-primary">Cảnh báo token</h2>
          <p className="mt-1 text-sm text-text-secondary">Gom toàn bộ kênh sắp hết hạn token hoặc cần kết nối lại vào một chỗ để xử lý nhanh.</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-obsidian-950 px-4 py-2 text-sm text-text-secondary">
          Tổng cảnh báo: <span className="font-semibold text-white">{tokenAlertChannels.length}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          { id: "all", label: "Tất cả", count: tokenAlertChannels.length },
          { id: "facebook", label: "Facebook", count: tokenAlertChannels.filter((item) => item.platform === "facebook").length },
          { id: "youtube", label: "YouTube", count: tokenAlertChannels.filter((item) => item.platform === "youtube").length },
          { id: "tiktok", label: "TikTok", count: tokenAlertChannels.filter((item) => item.platform === "tiktok").length },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => setTokenAlertPlatformFilter(item.id as "all" | Platform)}
            className={cn(
              "inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition-colors",
              tokenAlertPlatformFilter === item.id ? "border-accent-blue bg-accent-blue/10 text-accent-blue" : "border-white/10 bg-obsidian-950 text-text-secondary hover:text-white",
            )}
          >
            {item.label}
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", tokenAlertPlatformFilter === item.id ? "bg-accent-blue/20 text-accent-blue" : "bg-white/10 text-text-secondary")}>
              {item.count}
            </span>
          </button>
        ))}
      </div>

      {filteredTokenAlertChannels.length === 0 ? (
        <Card className="p-6 text-sm text-text-secondary">Hiện chưa có kênh nào phát sinh cảnh báo token.</Card>
      ) : (
        <div className="space-y-4">{filteredTokenAlertChannels.map(renderChannelCard)}</div>
      )}
    </div>
  );

  const renderProfile = () => (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-text-primary">Hồ sơ cá nhân</h2>
        <p className="mt-1 text-sm text-text-secondary">Quản lý thông tin cá nhân và ảnh đại diện.</p>
      </div>
      <Card className="space-y-6 p-6">
        <div className="flex items-center gap-6">
          <img src={user?.avatar || "https://api.dicebear.com/7.x/identicon/svg?seed=user1"} alt="Avatar" className="h-20 w-20 rounded-full border border-white/10" />
          <button className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium transition-colors hover:bg-white/5">Thay đổi ảnh đại diện</button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-text-secondary">Họ tên</label>
            <input value={profileName} onChange={(event) => setProfileName(event.target.value)} className="w-full rounded-xl border border-border-default bg-obsidian-900 px-4 py-2 text-white outline-none transition-colors focus:border-accent-blue" />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-text-secondary">Email</label>
            <input value={profileEmail} disabled className="w-full cursor-not-allowed rounded-xl border border-border-default bg-obsidian-900/70 px-4 py-2 text-text-secondary" />
            <div className="mt-2 text-xs text-text-tertiary">Email được quản lý bởi Supabase Auth và chưa hỗ trợ đổi trực tiếp trong màn hình này.</div>
          </div>
        </div>
        <div className="flex justify-end border-t border-white/5 pt-4">
          <button
            className="rounded-xl bg-accent-blue px-6 py-2 text-sm font-bold text-white transition-colors hover:bg-blue-600"
            onClick={async () => {
              const ok = await saveSettings({ profile: { name: profileName || user?.name } });
              if (ok) addAlert({ title: "Thành công", message: "Đã lưu hồ sơ", type: "success" });
            }}
          >
            Lưu thay đổi
          </button>
        </div>
      </Card>
    </div>
  );

  const renderNotifications = () => {
    const toggle = async (key: "email" | "push" | "alerts", value: boolean, setter: (next: boolean) => void) => {
      setter(value);
      const ok = await saveSettings({ notifications: { [key]: value } });
      if (!ok) setter(!value);
    };

    const ToggleRow = ({
      title,
      description,
      value,
      onChange,
    }: {
      title: string;
      description: string;
      value: boolean;
      onChange: (next: boolean) => void;
    }) => (
      <div className="flex items-center justify-between border-t border-white/5 pt-6 first:border-t-0 first:pt-0">
        <div>
          <div className="mb-1 text-sm font-bold text-white">{title}</div>
          <div className="text-xs text-text-secondary">{description}</div>
        </div>
        <div className={cn("relative h-6 w-12 cursor-pointer rounded-full transition-colors", value ? "bg-accent-emerald" : "bg-obsidian-600")} onClick={() => onChange(!value)}>
          <div className={cn("absolute top-1 h-4 w-4 rounded-full shadow transition-all", value ? "right-1 bg-white" : "left-1 bg-text-secondary")} />
        </div>
      </div>
    );

    return (
      <div className="max-w-2xl space-y-6">
        <div>
          <h2 className="text-xl font-bold text-text-primary">Tùy chỉnh thông báo</h2>
          <p className="mt-1 text-sm text-text-secondary">Quản lý cách hệ thống thông báo sự kiện cho bạn.</p>
        </div>
        <Card className="space-y-6 p-6">
          <ToggleRow title="Thông báo Email" description="Nhận báo cáo tổng hợp qua email." value={emailNotif} onChange={(next) => toggle("email", next, setEmailNotif)} />
          <ToggleRow title="Thông báo đẩy" description="Nhận thông báo realtime trên trình duyệt." value={pushNotif} onChange={(next) => toggle("push", next, setPushNotif)} />
          <ToggleRow title="Cảnh báo bất thường" description="Báo trước khi token sắp hết hạn hoặc sync gặp lỗi." value={alertNotif} onChange={(next) => toggle("alerts", next, setAlertNotif)} />
        </Card>
      </div>
    );
  };

  const renderUsers = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-text-primary">Quản lý người dùng</h2>
        <p className="mt-1 text-sm text-text-secondary">Trang này hiện vẫn ở chế độ read-only cho thành viên workspace.</p>
      </div>
      <Card className="overflow-hidden border border-white/5 p-0">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-white/5 bg-obsidian-900/50">
            <tr>
              <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-text-tertiary">Người dùng</th>
              <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-text-tertiary">Vai trò</th>
              <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-text-tertiary">Trạng thái</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {systemUsers.map((member) => (
              <tr key={member.id}>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <img src={member.avatar} alt={member.name} className="h-10 w-10 rounded-full border border-white/10" />
                    <div>
                      <div className="font-medium text-white">{member.name}</div>
                      <div className="text-xs text-text-secondary">{member.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-text-secondary">{member.role}</td>
                <td className="px-6 py-4 text-text-secondary">{member.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );

  const renderPlaceholder = (title: string, description: string) => (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-text-primary">{title}</h2>
        <p className="mt-1 text-sm text-text-secondary">{description}</p>
      </div>
      <Card className="p-6 text-sm text-text-secondary">Khu vực này đang được giữ lại để hoàn thiện ở bước sau, không ảnh hưởng tới phần quản lý kênh và analytics.</Card>
    </div>
  );

  const tabButton = (tab: SettingsTab, label: string, icon: ReactNode, count?: number) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={cn(
        "flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
        activeTab === tab ? "bg-accent-gold/10 text-accent-gold" : "text-text-secondary hover:bg-white/5 hover:text-white",
      )}
    >
      <span className="flex items-center gap-3">
        {icon}
        {label}
      </span>
      {typeof count === "number" ? (
        <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", activeTab === tab ? "bg-accent-gold/20 text-accent-gold" : "bg-white/10 text-text-secondary")}>
          {count}
        </span>
      ) : null}
    </button>
  );

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="shrink-0 border-b border-white/[0.05] bg-obsidian-950/50 px-6 py-5 lg:px-8">
        <h1 className="mb-1 text-3xl font-bold tracking-tight text-text-primary">Cài đặt hệ thống</h1>
        <p className="text-sm text-text-secondary">Quản lý tích hợp, tài khoản và cấu hình workspace.</p>
      </div>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <div className="w-64 shrink-0 overflow-y-auto border-r border-white/5 bg-obsidian-900/30 p-4">
          <div className="space-y-1">
            <div className="mb-2 px-3 py-2 text-xs font-bold uppercase tracking-widest text-text-tertiary">Cá nhân</div>
            {tabButton("profile", "Hồ sơ", <User className="h-4 w-4" />)}
            {tabButton("notifications", "Thông báo", <Bell className="h-4 w-4" />)}
          </div>
          <div className="mt-8 space-y-1">
            <div className="mb-2 px-3 py-2 text-xs font-bold uppercase tracking-widest text-text-tertiary">Không gian làm việc</div>
            {tabButton("users", "Người dùng", <User className="h-4 w-4" />)}
            {tabButton("integrations", "Tích hợp kênh", <Globe className="h-4 w-4" />)}
            {tabButton("token-alerts", "Cảnh báo token", <RefreshCw className="h-4 w-4" />, tokenAlertChannels.length)}
            {tabButton("security", "Bảo mật", <Shield className="h-4 w-4" />)}
            {tabButton("apikeys", "Khóa API", <KeySquare className="h-4 w-4" />)}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 md:p-10">
          <div className="mx-auto max-w-5xl">
            {activeTab === "integrations" && renderIntegrations()}
            {activeTab === "token-alerts" && renderTokenAlerts()}
            {activeTab === "profile" && renderProfile()}
            {activeTab === "notifications" && renderNotifications()}
            {activeTab === "users" && renderUsers()}
            {activeTab === "security" && renderPlaceholder("Bảo mật tài khoản", "Đổi mật khẩu và 2FA sẽ được nối với Supabase Auth ở bước tiếp theo.")}
            {activeTab === "apikeys" && renderPlaceholder("Quản lý khóa API", "Khu vực cấp khóa API read-only cho tích hợp ngoài sẽ được bổ sung sau.")}
          </div>
        </div>
      </div>

      {isConnectModalOpen && <ConnectChannelModal onClose={() => setIsConnectModalOpen(false)} />}
    </div>
  );
}
