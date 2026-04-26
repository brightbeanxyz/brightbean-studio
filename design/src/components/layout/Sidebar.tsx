import { NavLink, useNavigate } from "react-router-dom";
import {
  Building2,
  LayoutDashboard,
  Folders,
  Calendar,
  Radio,
  Inbox,
  BarChart4,
  Settings,
  ChevronLeft,
  ChevronRight,
  Plus,
  Hash,
  Crown,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { GroupSwitcher } from "@/components/ui/GroupSwitcher";
import { useAppStore } from "@/store/AppContext";

const NAV_ITEMS = [
  { name: "Tổng quan", path: "/", icon: LayoutDashboard },
  { name: "Nhóm kênh", path: "/portfolio", icon: Building2 },
  { name: "Kênh", path: "/manage", icon: Radio },
  { name: "Nội dung", path: "/content", icon: Folders },
  { name: "Lịch", path: "/calendar", icon: Calendar },
  { name: "Hộp thư", path: "/inbox", icon: Inbox },
  { name: "Báo cáo", path: "/reports", icon: BarChart4 },
];

interface SidebarProps {
  isCollapsed: boolean;
  setIsCollapsed: (v: boolean) => void;
}

export function Sidebar({ isCollapsed, setIsCollapsed }: SidebarProps) {
  const { user, logout, setFilters, groups, channels, setIsManageGroupsModalOpen } = useAppStore();
  const navigate = useNavigate();

  const tokenAlertCount = channels.filter(
    (channel) =>
      channel.missingScopes?.length > 0 ||
      channel.reconnectRequired ||
      channel.connectionStatus !== "connected" ||
      ["expiring", "expiring_refreshable", "expired", "expired_refreshable", "reconnect_required", "missing"].includes(
        channel.tokenHealth?.status,
      ),
  ).length;

  return (
    <aside
      className={cn(
        "relative z-50 flex h-screen shrink-0 flex-col border-r border-border-subtle bg-surface-elevated/50 px-4 pt-5 pb-4 shadow-elevated backdrop-blur-3xl transition-[width,padding] duration-300 ease-fluid",
        isCollapsed ? "w-20 px-3" : "w-[260px]",
      )}
    >
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3.5 top-8 z-10 flex h-7 w-7 items-center justify-center rounded-full border border-border-default bg-surface-elevated text-text-tertiary shadow-card transition-all hover:scale-110 hover:border-text-secondary hover:text-text-primary"
      >
        {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>

      <GroupSwitcher isSidebarCollapsed={isCollapsed} />

      <div
        className={cn(
          "mb-3 text-xs font-semibold tracking-wider text-text-tertiary uppercase",
          isCollapsed ? "text-center" : "px-2",
        )}
      >
        {isCollapsed ? "Menu" : "Menu chính"}
      </div>

      <nav className="z-10 flex flex-col gap-1.5">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "group relative flex items-center rounded-xl transition-all duration-240 ease-fluid",
                isCollapsed ? "mx-auto h-12 w-12 justify-center" : "gap-3 px-3 py-2.5",
                isActive
                  ? "bg-obsidian-800 text-white shadow-soft-inset before:absolute before:top-1/4 before:bottom-1/4 before:left-0 before:w-[3px] before:rounded-r-full before:bg-accent-blue before:shadow-glow-blue"
                  : "text-text-secondary hover:bg-white/[0.04] hover:text-text-primary hover:shadow-hover-elevation",
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={cn(
                    "shrink-0 transition-colors",
                    isCollapsed ? "h-[22px] w-[22px]" : "h-5 w-5",
                    isActive ? "text-accent-blue" : "text-text-secondary group-hover:text-text-primary",
                  )}
                />
                {!isCollapsed && <span className="text-[14px] font-medium">{item.name}</span>}
                {isCollapsed && (
                  <div className="invisible absolute top-1/2 left-[calc(100%+16px)] z-50 -translate-y-1/2 whitespace-nowrap rounded-lg border border-border-default bg-surface-elevated px-3 py-1.5 text-sm font-medium text-white opacity-0 shadow-elevated transition-all group-hover:visible group-hover:opacity-100">
                    {item.name}
                  </div>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {!isCollapsed && (
        <div className="mt-8 mb-4">
          <div className="mb-3 flex items-center justify-between px-2">
            <div className="text-xs font-semibold tracking-wider text-text-tertiary uppercase">Nhóm kênh yêu thích</div>
            <button
              onClick={() => setIsManageGroupsModalOpen(true)}
              className="rounded p-1 text-text-tertiary transition-colors hover:bg-white/5 hover:text-text-primary"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="flex flex-col gap-1">
            {groups
              .filter((group) => group.isPinned && group.id !== "all")
              .map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    setFilters({ group: item.id });
                    navigate("/portfolio");
                  }}
                  className="group flex items-center justify-between rounded-xl px-3 py-2 text-text-secondary transition-all duration-240 ease-fluid hover:bg-white/[0.04] hover:text-text-primary hover:shadow-hover-elevation"
                >
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    <div className="relative flex shrink-0 items-center justify-center">
                      <Hash className="relative z-10 h-4 w-4 text-text-tertiary transition-colors group-hover:text-accent-blue" />
                      <div
                        className={cn(
                          "absolute -right-0.5 -bottom-0.5 z-20 h-1.5 w-1.5 rounded-full",
                          item.health === "healthy"
                            ? "bg-accent-emerald shadow-[0_0_8px_rgba(16,185,129,0.6)]"
                            : item.health === "warning"
                              ? "bg-accent-gold shadow-[0_0_8px_rgba(228,197,128,0.6)]"
                              : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]",
                        )}
                      />
                    </div>
                    <span className="truncate text-[13px] font-medium">{item.name}</span>
                  </div>
                  <span className="rounded border border-white/5 bg-obsidian-900 px-1.5 py-0.5 font-mono text-[10px] font-medium text-text-tertiary opacity-0 transition-opacity group-hover:opacity-100">
                    {item.channelsCount}
                  </span>
                </button>
              ))}
          </div>
        </div>
      )}

      <div className={cn("relative mt-auto flex flex-col gap-3", isCollapsed ? "items-center" : "")}>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              "group mb-2 flex items-center rounded-xl transition-all duration-240",
              isCollapsed ? "h-12 w-12 justify-center" : "gap-3 px-3 py-2.5",
              isActive
                ? "bg-obsidian-800 text-white shadow-soft-inset before:absolute before:top-1/4 before:bottom-1/4 before:left-0 before:w-[3px] before:rounded-r-full before:bg-accent-blue"
                : "text-text-secondary hover:bg-white/[0.04] hover:text-text-primary",
            )
          }
        >
          {({ isActive }) => (
            <>
              <Settings
                className={cn(
                  "shrink-0 transition-colors",
                  isCollapsed ? "h-[22px] w-[22px]" : "h-5 w-5",
                  isActive ? "text-accent-blue" : "text-text-secondary group-hover:text-text-primary",
                )}
              />
              {!isCollapsed && (
                <div className="flex min-w-0 items-center gap-2">
                  <span className="text-[14px] font-medium">Cài đặt hệ thống</span>
                  {tokenAlertCount > 0 && (
                    <span className="inline-flex min-w-6 items-center justify-center rounded-full border border-red-500/30 bg-red-500/15 px-2 py-0.5 text-[10px] font-bold text-red-300 shadow-[0_0_12px_rgba(239,68,68,0.18)]">
                      {tokenAlertCount}
                    </span>
                  )}
                </div>
              )}
              {isCollapsed && (
                <div className="invisible absolute top-1/2 left-[calc(100%+16px)] z-50 -translate-y-1/2 whitespace-nowrap rounded-lg border border-border-default bg-surface-elevated px-3 py-1.5 text-sm font-medium text-white opacity-0 shadow-elevated transition-all group-hover:visible group-hover:opacity-100">
                  <div className="flex items-center gap-2">
                    <span>Cài đặt hệ thống</span>
                    {tokenAlertCount > 0 && (
                      <span className="inline-flex min-w-5 items-center justify-center rounded-full border border-red-500/30 bg-red-500/15 px-1.5 py-0.5 text-[10px] font-bold text-red-300">
                        {tokenAlertCount}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </NavLink>

        <div
          className={cn(
            "flex items-center gap-3.5 border-t border-white/5 pt-5",
            isCollapsed ? "justify-center" : "px-3 pb-1",
          )}
        >
          <div className="group/avatar relative shrink-0 cursor-pointer">
            <div className="h-11 w-11 rounded-full border border-white/10 p-[2px] transition-all hover:border-white/20 hover:bg-white/10">
              <div className="flex h-full w-full items-center justify-center overflow-hidden rounded-full border border-transparent bg-obsidian-900 text-sm font-bold text-white/50">
                {user?.avatar ? (
                  <img src={user.avatar} alt={user?.name || "Avatar"} className="h-full w-full object-cover" />
                ) : (
                  <span>{(user?.name || "A")[0]}</span>
                )}
              </div>
            </div>
            <div className="absolute -right-0.5 -bottom-0.5 flex h-4 w-4 items-center justify-center overflow-hidden rounded-full bg-surface-elevated/80">
              <div className="h-2.5 w-2.5 rounded-full bg-accent-emerald shadow-glow-emerald" />
            </div>
          </div>

          {!isCollapsed && (
            <div className="group/profile flex min-w-0 flex-1 cursor-pointer flex-col overflow-hidden -space-y-0.5">
              <div className="truncate text-[15px] font-bold text-white transition-colors">{user?.name || "Người dùng"}</div>
              <div className="flex items-center gap-1.5 truncate text-[11px] font-semibold tracking-wider text-text-tertiary">
                <Crown className="h-3.5 w-3.5 shrink-0 text-accent-gold drop-shadow-[0_0_4px_rgba(228,197,128,0.5)]" />
                <span className="truncate whitespace-nowrap">{user?.role || "SUPER ADMIN"}</span>
              </div>
            </div>
          )}

          {!isCollapsed && (
            <button
              onClick={logout}
              className="group/logout shrink-0 rounded-lg p-1.5 text-text-tertiary transition-colors hover:text-white"
            >
              <LogOut className="h-[20px] w-[20px] transition-transform group-hover/logout:translate-x-0.5" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
