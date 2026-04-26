import React, { useState } from "react";
import { Drawer } from "./Drawer";
import { Platform } from "./PostCard";
import { Image, Video, Calendar, Clock, Send, Facebook, Youtube, X as XIcon, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/AppContext";

interface ComposePostDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ComposePostDrawer({ isOpen, onClose }: ComposePostDrawerProps) {
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>(["facebook"]);
  const [selectedChannels, setSelectedChannels] = useState<Record<string, string>>({});
  const [content, setContent] = useState("");
  const [scheduledDate, setScheduledDate] = useState("");
  const [scheduledTime, setScheduledTime] = useState("");

  const { addAlert, channels } = useAppStore();

  const togglePlatform = (p: Platform) => {
    setSelectedPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));
  };

  const notifyReadonly = () => {
    addAlert({
      type: "warning",
      title: "Đang phát triển",
      message: "Tính năng publish, lên lịch và media processing đã được tạm ẩn trong phiên bản read-only analytics.",
    });
    onClose();
  };

  return (
    <Drawer isOpen={isOpen} onClose={onClose} title="Soạn bài mới" size="md">
      <div className="flex flex-col h-full bg-obsidian-950">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="rounded-xl border border-accent-gold/20 bg-accent-gold/10 p-4 text-sm text-text-primary">
            Composer hiện được giữ lại giao diện để tham khảo. Các thao tác đăng bài, lên lịch và upload media sẽ quay lại sau.
          </div>

          <div className="space-y-3">
            <label className="text-sm font-semibold text-text-secondary uppercase tracking-widest">Chọn nền tảng</label>
            <div className="flex items-center gap-3">
              {[
                { id: "facebook", icon: Facebook, color: "text-blue-500", bg: "bg-blue-500/10", border: "border-blue-500/30", name: "Facebook" },
                { id: "youtube", icon: Youtube, color: "text-red-500", bg: "bg-red-500/10", border: "border-red-500/30", name: "YouTube" },
                { id: "tiktok", icon: XIcon, color: "text-cyan-500", bg: "bg-cyan-500/10", border: "border-cyan-500/30", isSvg: true, name: "TikTok" },
              ].map((p) => {
                const isSelected = selectedPlatforms.includes(p.id as Platform);
                const Icon = p.icon;
                return (
                  <button
                    key={p.id}
                    onClick={() => togglePlatform(p.id as Platform)}
                    className={cn(
                      "flex items-center gap-2 px-4 py-2 rounded-xl transition-all border",
                      isSelected ? cn(p.bg, p.border, p.color, "shadow-soft-inset") : "border-white/10 text-text-tertiary hover:bg-white/5",
                    )}
                  >
                    {p.isSvg && p.id === "tiktok" ? (
                      <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
                        <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z" />
                      </svg>
                    ) : (
                      <Icon className="w-5 h-5" />
                    )}
                    <span className="font-semibold capitalize">{p.name}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {selectedPlatforms.length > 0 && (
            <div className="space-y-3">
              <label className="text-sm font-semibold text-text-secondary uppercase tracking-widest">Chọn kênh</label>
              <div className="flex flex-col gap-3">
                {selectedPlatforms.map((platform) => {
                  const platformChannels = channels.filter((c) => c.platform === platform);
                  return (
                    <div key={platform} className="flex items-center gap-3">
                      <div className="w-24 text-sm font-medium text-text-primary capitalize flex items-center gap-2">
                        {platform === "facebook" && <Facebook className="w-4 h-4 text-blue-500" />}
                        {platform === "youtube" && <Youtube className="w-4 h-4 text-red-500" />}
                        {platform === "tiktok" && (
                          <svg className="w-4 h-4 fill-current text-cyan-500" viewBox="0 0 24 24">
                            <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z" />
                          </svg>
                        )}
                        <span className="capitalize">{platform === "tiktok" ? "TikTok" : platform === "youtube" ? "YouTube" : platform}</span>
                      </div>

                      <div className="relative flex-1 group/select">
                        <select
                          className="w-full appearance-none bg-surface-elevated border border-white/10 rounded-xl px-4 py-2.5 text-sm text-text-primary focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/50 outline-none pr-10 cursor-pointer"
                          value={selectedChannels[platform] || "all"}
                          onChange={(e) => setSelectedChannels((prev) => ({ ...prev, [platform]: e.target.value }))}
                        >
                          <option value="all">
                            Tất cả kênh {platform === "tiktok" ? "TikTok" : platform === "youtube" ? "YouTube" : "Facebook"} ({platformChannels.length})
                          </option>
                          {platformChannels.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))}
                        </select>
                        <ChevronDown className="w-4 h-4 text-text-tertiary absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none group-focus-within/select:text-accent-blue transition-colors" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="space-y-3">
            <label className="text-sm font-semibold text-text-secondary uppercase tracking-widest">Media</label>
            <button
              type="button"
              onClick={notifyReadonly}
              className="w-full border border-dashed border-white/10 rounded-2xl p-8 flex flex-col items-center justify-center text-center hover:bg-white/[0.02] transition-colors cursor-pointer group"
            >
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 rounded-full bg-surface-elevated flex items-center justify-center text-text-tertiary group-hover:text-accent-blue transition-colors shadow-card">
                  <Image className="w-5 h-5" />
                </div>
                <div className="w-12 h-12 rounded-full bg-surface-elevated flex items-center justify-center text-text-tertiary group-hover:text-accent-emerald transition-colors shadow-card">
                  <Video className="w-5 h-5" />
                </div>
              </div>
              <p className="text-sm text-text-secondary mb-1">Media processing đang phát triển</p>
              <p className="text-xs text-text-tertiary">Hỗ trợ JPG, PNG, MP4 (Max 500MB)</p>
            </button>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-text-secondary uppercase tracking-widest">Nội dung</label>
            </div>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Nhập nội dung bài đăng..."
              className="w-full bg-surface-elevated border border-white/10 rounded-xl p-4 text-sm text-text-primary focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/50 outline-none resize-none min-h-[160px] custom-scrollbar transition-all"
            />
          </div>

          <div className="space-y-3">
            <label className="text-sm font-semibold text-text-secondary uppercase tracking-widest">Lịch đăng</label>
            <div className="flex items-center gap-3">
              <label className="flex-1 relative cursor-pointer group">
                <div className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-surface-elevated border border-white/10 rounded-xl text-text-primary group-hover:bg-white/5 transition-colors font-medium relative overflow-hidden">
                  <Calendar className="w-4 h-4 text-accent-blue" />
                  <span className="text-sm">Chọn ngày</span>
                  <input
                    type="date"
                    value={scheduledDate}
                    onChange={(event) => setScheduledDate(event.target.value)}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                  />
                </div>
              </label>
              <label className="flex-1 relative cursor-pointer group">
                <div className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-surface-elevated border border-white/10 rounded-xl text-text-primary group-hover:bg-white/5 transition-colors font-medium relative overflow-hidden">
                  <Clock className="w-4 h-4 text-accent-gold" />
                  <span className="text-sm">Chọn giờ</span>
                  <input
                    type="time"
                    value={scheduledTime}
                    onChange={(event) => setScheduledTime(event.target.value)}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                  />
                </div>
              </label>
            </div>
          </div>
        </div>

        <div className="p-4 md:p-6 border-t border-white/10 bg-surface-card flex items-center justify-end gap-3 shrink-0">
          <button onClick={onClose} className="px-5 py-2.5 rounded-xl text-sm font-semibold text-text-secondary hover:text-white transition-colors">
            Hủy
          </button>
          <button onClick={notifyReadonly} className="px-5 py-2.5 rounded-xl text-sm font-semibold border border-white/10 bg-white/5 text-white hover:bg-white/10 transition-colors">
            Lưu nháp
          </button>
          <button onClick={notifyReadonly} className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold bg-accent-blue text-white shadow-glow-blue hover:scale-105 transition-transform">
            <Send className="w-4 h-4" /> Đăng ngay
          </button>
        </div>
      </div>
    </Drawer>
  );
}
