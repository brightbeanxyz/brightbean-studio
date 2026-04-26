import React, { createContext, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { apiGet, apiSend } from "@/lib/api";
import { supabase } from "@/lib/supabase";

export interface GroupData {
  id: string;
  name: string;
  channelsCount: number;
  followers: string;
  health: "healthy" | "warning" | "error";
  platforms: string[];
  growth?: string;
  isPinned?: boolean;
  description?: string;
}

type Filters = {
  dateRange: string;
  platforms: string[];
  group: string;
  channel: string;
  searchQuery: string;
};

type AppContextType = {
  authReady: boolean;
  filters: Filters;
  setFilters: (filters: Partial<Filters>) => void;
  clearFilters: () => void;
  groups: GroupData[];
  addGroup: (group: Partial<GroupData>) => void;
  updateGroup: (id: string, updates: Partial<GroupData>) => void;
  deleteGroup: (id: string) => void;
  contents: any[];
  addContent: (content: any) => void;
  updateContent: (id: string, updates: any) => void;
  deleteContent: (id: string) => void;
  channels: any[];
  addChannel: (platform?: string, groupId?: string) => void;
  importChannelToken: (payload: {
    platform: "facebook" | "youtube" | "tiktok";
    groupId?: string;
    accessToken: string;
    refreshToken?: string;
    externalId?: string;
    expiresIn?: number;
    scope?: string;
  }) => Promise<boolean>;
  updateChannel: (id: string, updates: any) => void;
  runChannelAction: (id: string, action: string) => void;
  deleteChannel: (id: string) => void;
  posts: any[];
  addPost: (post: any) => void;
  updatePost: (id: number | string, updates: any) => void;
  deletePost: (id: number | string) => void;
  alerts: any[];
  addAlert: (alert: any) => void;
  dismissAlert: (id: string) => void;
  clearAlerts: () => void;
  dashboardKpis: any[];
  trendData: any[];
  inboxMessages: any[];
  replyToInboxMessage: (id: string, body: string) => void;
  updateInboxMessage: (id: string, updates: any) => void;
  reports: any;
  channelAnalytics: any;
  settings: any;
  saveSettings: (payload: any) => Promise<boolean>;
  urls: Record<string, string>;
  isManageGroupsModalOpen: boolean;
  setIsManageGroupsModalOpen: (isOpen: boolean) => void;
  user: any | null;
  login: (userData: any) => void;
  register: (userData: any) => void;
  logout: () => void;
  systemUsers: any[];
  addSystemUser: (user: any) => void;
  updateSystemUser: (id: string, updates: any) => void;
  deleteSystemUser: (id: string) => void;
  theme: "dark" | "light";
  toggleTheme: () => void;
  filteredContents: any[];
  filteredChannels: any[];
  refreshState: () => void;
};

const AppContext = createContext<AppContextType | undefined>(undefined);

const DEFAULT_GROUP: GroupData = {
  id: "all",
  name: "Tất cả kênh (Workspace)",
  channelsCount: 0,
  followers: "0",
  health: "healthy",
  platforms: [],
  isPinned: true,
};

const UNDER_DEVELOPMENT_MESSAGE =
  "Tính năng này đang phát triển cho phiên bản read-only analytics. Bạn vẫn có thể kết nối kênh và theo dõi dữ liệu.";

function toDisplayUser(sessionUser: any, fallback?: any) {
  if (!sessionUser && !fallback) return null;
  return {
    name: fallback?.name || sessionUser?.user_metadata?.full_name || sessionUser?.email?.split("@")[0] || "Người dùng",
    email: fallback?.email || sessionUser?.email || "",
    username: fallback?.username || sessionUser?.user_metadata?.username || sessionUser?.email?.split("@")[0] || "",
    role: fallback?.role || "OWNER",
    avatar: fallback?.avatar || sessionUser?.user_metadata?.avatar_url || "",
  };
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [authReady, setAuthReady] = useState(false);
  const [groups, setGroups] = useState<GroupData[]>([DEFAULT_GROUP]);
  const [contents, setContents] = useState<any[]>([]);
  const [channels, setChannels] = useState<any[]>([]);
  const [posts, setPosts] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [dashboardKpis, setDashboardKpis] = useState<any[]>([]);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [inboxMessages, setInboxMessages] = useState<any[]>([]);
  const [reports, setReports] = useState<any>({});
  const [channelAnalytics, setChannelAnalytics] = useState<any>({});
  const [settings, setSettings] = useState<any>({});
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [isManageGroupsModalOpen, setIsManageGroupsModalOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [user, setUser] = useState<any | null>(null);
  const [systemUsers, setSystemUsers] = useState<any[]>([]);
  const [filters, setFiltersState] = useState<Filters>({
    dateRange: "30d",
    platforms: [],
    group: "all",
    channel: "all",
    searchQuery: "",
  });

  const addAlert = (alert: any) => {
    setAlerts((prev) => [
      {
        ...alert,
        id: alert.id || `${Date.now()}-${Math.random()}`,
        time: alert.time || "Vua xong",
      },
      ...prev,
    ]);
  };

  const resetState = () => {
    setGroups([DEFAULT_GROUP]);
    setContents([]);
    setChannels([]);
    setPosts([]);
    setDashboardKpis([]);
    setTrendData([]);
    setInboxMessages([]);
    setReports({});
    setChannelAnalytics({});
    setSettings({});
    setUrls({});
    setSystemUsers([]);
  };

  const refreshState = () => {
    apiGet<any>("/state")
      .then((data) => {
        setGroups(data.groups?.length ? data.groups : [DEFAULT_GROUP]);
        setContents(data.contents || []);
        setChannels(data.channels || []);
        setPosts(data.posts || []);
        setAlerts(data.alerts || []);
        setDashboardKpis(data.kpis || []);
        setTrendData(data.trendData || []);
        setInboxMessages(data.inbox || []);
        setReports(data.reports || {});
        setChannelAnalytics(data.channelAnalytics || {});
        setSettings(data.settings || {});
        setUrls(data.urls || {});
        setUser((prev: any) => toDisplayUser(null, data.user || prev));
        setSystemUsers(data.systemUsers || []);
      })
      .catch((error) => {
        addAlert({
          type: "error",
          title: "Không tải được dữ liệu",
          message: error.message || "Vui lòng tải lại trang.",
        });
      });
  };

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      const nextUser = data.session?.user || null;
      setUser(toDisplayUser(nextUser));
      if (nextUser) {
        refreshState();
      } else {
        resetState();
      }
      setAuthReady(true);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      const nextUser = session?.user || null;
      setUser(toDisplayUser(nextUser));
      if (nextUser) {
        window.setTimeout(() => refreshState(), 0);
      } else {
        resetState();
      }
      setAuthReady(true);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
  }, [theme]);

  const setFilters = (newFilters: Partial<Filters>) => {
    setFiltersState((prev) =>
      newFilters.group && newFilters.group !== prev.group
        ? { ...prev, ...newFilters, channel: "all" }
        : { ...prev, ...newFilters },
    );
  };

  const clearFilters = () =>
    setFiltersState({ dateRange: "30d", platforms: [], group: "all", channel: "all", searchQuery: "" });

  const addGroup = (group: Partial<GroupData>) => {
    apiSend<any>("/groups", "POST", group)
      .then(refreshState)
      .catch((error) => addAlert({ type: "error", title: "Không tạo được nhóm", message: error.message }));
  };

  const updateGroup = (id: string, updates: Partial<GroupData>) => {
    if (id === "all") return;
    apiSend<any>(`/groups/${id}`, "PATCH", updates)
      .then(refreshState)
      .catch((error) => addAlert({ type: "error", title: "Không cập nhật được nhóm", message: error.message }));
  };

  const deleteGroup = (id: string) => {
    if (id === "all") return;
    apiSend<any>(`/groups/${id}`, "DELETE")
      .then(refreshState)
      .catch((error) => addAlert({ type: "error", title: "Không xóa được nhóm", message: error.message }));
  };

  const addContent = (content: any) => setContents((prev) => [{ ...content, id: Date.now().toString() }, ...prev]);
  const updateContent = (id: string, updates: any) =>
    setContents((prev) => prev.map((c) => (c.id === id ? { ...c, ...updates } : c)));
  const deleteContent = (id: string) => setContents((prev) => prev.filter((c) => c.id !== id));

  const addChannel = (platform?: string, groupId?: string) => {
    const params = new URLSearchParams();
    if (platform) params.set("platform", platform);
    if (groupId && groupId !== "all") params.set("groupId", groupId);
    apiGet<{ redirect: string }>(`/oauth/start${params.toString() ? `?${params.toString()}` : ""}`)
      .then((data) => {
        window.location.href = data.redirect;
      })
      .catch((error) =>
        addAlert({
          type: "error",
          title: "Không thể bắt đầu kết nối",
          message: error.message || "Vui lòng kiểm tra cấu hình OAuth và thử lại.",
        }),
      );
  };

  const importChannelToken = async (payload: {
    platform: "facebook" | "youtube" | "tiktok";
    groupId?: string;
    accessToken: string;
    refreshToken?: string;
    externalId?: string;
    expiresIn?: number;
    scope?: string;
  }) => {
    try {
      await apiSend<any>("/channels/import-token", "POST", payload);
      addAlert({
        type: "success",
        title: "Đã kết nối kênh",
        message: "Token hợp lệ đã được lưu và hệ thống đã đồng bộ dữ liệu ban đầu.",
      });
      refreshState();
      return true;
    } catch (error: any) {
      addAlert({
        type: "error",
        title: "Không thể nhập token",
        message: error.message || "Vui lòng kiểm tra lại token, quyền truy cập và định danh kênh.",
      });
      return false;
    }
  };

  const updateChannel = (id: string, updates: any) => {
    apiSend<any>(`/channels/${id}`, "PATCH", updates)
      .then(refreshState)
      .catch((error) => addAlert({ type: "error", title: "Không cập nhật được kênh", message: error.message }));
  };

  const runChannelAction = (id: string, action: string) => {
    apiSend<any>(`/channels/${id}/action`, "POST", { action })
      .then((data) => {
        if (data.redirect) {
          window.location.href = data.redirect;
          return;
        }
        refreshState();
      })
      .catch((error) => addAlert({ type: "error", title: "Không thực hiện được thao tác kênh", message: error.message }));
  };

  const deleteChannel = (id: string) => {
    apiSend<any>(`/channels/${id}`, "DELETE")
      .then(refreshState)
      .catch((error) => addAlert({ type: "error", title: "Không xóa được kênh", message: error.message }));
  };

  const addPost = () => addAlert({ type: "warning", title: "Đang phát triển", message: UNDER_DEVELOPMENT_MESSAGE });
  const updatePost = () => addAlert({ type: "warning", title: "Đang phát triển", message: UNDER_DEVELOPMENT_MESSAGE });
  const deletePost = () => addAlert({ type: "warning", title: "Đang phát triển", message: UNDER_DEVELOPMENT_MESSAGE });

  const replyToInboxMessage = () =>
    addAlert({
      type: "warning",
      title: "Đang phát triển",
      message: "Tính năng trả lời comment/inbox đã được ẩn trong phiên bản read-only analytics.",
    });

  const updateInboxMessage = (id: string, updates: any) => {
    setInboxMessages((prev) =>
      prev.map((message) =>
        message.id === id
          ? {
              ...message,
              ...updates,
              isRead: updates.status ? updates.status !== "unread" : true,
            }
          : message,
      ),
    );
  };

  const saveSettings = (payload: any) => {
    return apiSend<any>("/settings", "PATCH", payload)
      .then(() => {
        setSettings((prev: any) => ({
          ...prev,
          ...payload,
          notifications: {
            ...(prev?.notifications || {}),
            ...(payload.notifications || {}),
          },
        }));
        refreshState();
        return true;
      })
      .catch((error) => {
        addAlert({ type: "error", title: "Không lưu được cài đặt", message: error.message });
        return false;
      });
  };

  const dismissAlert = (id: string) => setAlerts((prev) => prev.filter((a) => a.id !== id));
  const clearAlerts = () => setAlerts([]);

  const addSystemUser = () => addAlert({ type: "warning", title: "Đang phát triển", message: UNDER_DEVELOPMENT_MESSAGE });
  const updateSystemUser = () =>
    addAlert({ type: "warning", title: "Đang phát triển", message: UNDER_DEVELOPMENT_MESSAGE });
  const deleteSystemUser = () =>
    addAlert({ type: "warning", title: "Đang phát triển", message: UNDER_DEVELOPMENT_MESSAGE });

  const login = (userData: any) => setUser(userData);
  const register = (userData: any) => setUser(userData);
  const logout = () => {
    supabase.auth.signOut().finally(() => {
      setUser(null);
      resetState();
      window.location.href = "/login";
    });
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const filteredContents = useMemo(
    () =>
      contents.filter((c) => {
        if (filters.platforms.length > 0 && !filters.platforms.includes(c.platform)) return false;
        if (filters.group !== "all" && c.groupId !== filters.group) return false;
        if (filters.channel !== "all" && c.channelId !== filters.channel) return false;
        if (filters.searchQuery && !String(c.title || "").toLowerCase().includes(filters.searchQuery.toLowerCase()))
          return false;
        return true;
      }),
    [contents, filters],
  );

  const filteredChannels = useMemo(
    () =>
      channels.filter((c) => {
        if (filters.platforms.length > 0 && !filters.platforms.includes(c.platform)) return false;
        if (filters.group !== "all" && c.groupId !== filters.group) return false;
        return true;
      }),
    [channels, filters.platforms, filters.group],
  );

  return (
    <AppContext.Provider
      value={{
        authReady,
        filters,
        setFilters,
        clearFilters,
        groups,
        addGroup,
        updateGroup,
        deleteGroup,
        contents,
        addContent,
        updateContent,
        deleteContent,
        channels,
        addChannel,
        importChannelToken,
        updateChannel,
        runChannelAction,
        deleteChannel,
        posts,
        addPost,
        updatePost,
        deletePost,
        alerts,
        addAlert,
        dismissAlert,
        clearAlerts,
        dashboardKpis,
        trendData,
        inboxMessages,
        replyToInboxMessage,
        updateInboxMessage,
        reports,
        channelAnalytics,
        settings,
        saveSettings,
        urls,
        isManageGroupsModalOpen,
        setIsManageGroupsModalOpen,
        user,
        login,
        register,
        logout,
        systemUsers,
        addSystemUser,
        updateSystemUser,
        deleteSystemUser,
        filteredContents,
        filteredChannels,
        theme,
        toggleTheme,
        refreshState,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export const useAppStore = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppStore must be used within AppProvider");
  return ctx;
};
