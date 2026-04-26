import { useMemo, useState } from "react";
import { Drawer } from "./Drawer";
import { Tabs } from "./Tabs";
import {
  Activity,
  Calendar,
  Eye,
  Hash,
  MessageCircle,
  Play,
  Share2,
  ThumbsUp,
  TrendingUp,
} from "lucide-react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useAppStore } from "@/store/AppContext";
import { formatCompactNumber } from "@/lib/utils";

interface ContentDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  contentId: string | null;
}

export function ContentDetailDrawer({ isOpen, onClose, contentId }: ContentDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState("overview");
  const { contents, posts, inboxMessages, groups, addAlert } = useAppStore();

  const content =
    contents.find((item) => item.id.toString() === contentId) ||
    posts.find((item) => item.id.toString() === contentId);

  const relatedComments = useMemo(
    () => inboxMessages.filter((item: any) => !content?.channelId || item.channelId === content.channelId).slice(0, 5),
    [content?.channelId, inboxMessages],
  );

  const title = content?.title || "Nội dung chưa có tiêu đề";
  const caption = content?.caption || content?.content || "Chưa có mô tả chi tiết cho nội dung này.";
  const platform = content?.platform || "N/A";
  const thumbnail = content?.thumbnail || "";
  const groupName = content?.groupId ? groups.find((item) => item.id === content.groupId)?.name : "Không có nhóm";
  const channelName = content?.channel || "Không có thông tin kênh";
  const statusLabel = content?.growthImpact || content?.status || "Đang theo dõi";
  const dateLabel =
    content?.date && typeof content.date === "string"
      ? new Date(content.date).toLocaleDateString("vi-VN")
      : new Date().toLocaleDateString("vi-VN");

  const timelineData = [
    { name: "Reach", value: content?.reach || 0 },
    { name: "Tương tác", value: content?.engagement || 0 },
    { name: "Bình luận", value: content?.comments || 0 },
    { name: "Chia sẻ", value: content?.shares || 0 },
    { name: "Lưu bài", value: content?.saves || 0 },
  ];

  const hashtags = useMemo(() => {
    const matches = caption.match(/#[\p{L}\p{N}_]+/gu) || [];
    return matches.slice(0, 4);
  }, [caption]);

  const positiveRate = useMemo(() => {
    if (!relatedComments.length) return 0;
    const positives = relatedComments.filter((item: any) => item.sentiment === "positive").length;
    return Math.round((positives / relatedComments.length) * 100);
  }, [relatedComments]);

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      size="lg"
      title={
        <div className="flex items-center gap-3">
          <span className="max-w-[400px] truncate">{title}</span>
          <span className="shrink-0 rounded border border-accent-blue/20 bg-accent-blue/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-accent-blue">
            {platform}
          </span>
        </div>
      }
      subtitle={
        <div className="mt-1.5 flex flex-col gap-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-medium text-white">{channelName}</span>
            <span className="text-text-tertiary">•</span>
            <span className="text-text-secondary">{groupName}</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-text-tertiary">
            <span className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5" /> {dateLabel}
            </span>
            <div className="h-1 w-1 rounded-full bg-text-tertiary" />
            <span className="flex items-center gap-1 font-medium text-accent-emerald">
              <Activity className="h-3.5 w-3.5" /> {statusLabel}
            </span>
          </div>
        </div>
      }
      footer={
        <div className="flex w-full items-center justify-between">
          <div className="text-sm font-medium text-text-tertiary">Hiển thị dữ liệu từ phân tích và hộp thư hiện có</div>
          <button
            onClick={() =>
              addAlert({
                type: "warning",
                title: "Đang phát triển",
                message: "Tính năng đẩy mạnh nội dung và publish đang tạm ẩn trong phiên bản read-only analytics.",
              })
            }
            className="flex items-center gap-2 rounded-xl bg-accent-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-blue/90"
          >
            <TrendingUp className="h-4 w-4" />
            Đẩy mạnh nội dung
          </button>
        </div>
      }
    >
      <div className="sticky top-0 z-10 border-b border-white/5 bg-obsidian-950/80 px-6 pt-2 pb-2 backdrop-blur-xl">
        <Tabs
          options={[
            { value: "overview", label: "Tổng quan" },
            { value: "audience", label: "Khán giả" },
            { value: "comments", label: "Bình luận" },
          ]}
          value={activeTab}
          onValueChange={setActiveTab}
          className="w-full border-0 bg-transparent p-0"
        />
      </div>

      <div className="p-6">
        {activeTab === "overview" && (
          <div className="space-y-8">
            <div className="flex gap-5 rounded-2xl border border-white/5 bg-obsidian-900 p-4">
              <div className="relative h-24 w-32 shrink-0 overflow-hidden rounded-lg bg-black">
                {thumbnail ? (
                  <img src={thumbnail} alt={title} className="h-full w-full object-cover opacity-90" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-obsidian-950 text-text-tertiary">
                    <Play className="h-5 w-5" />
                  </div>
                )}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/20 backdrop-blur-md">
                    <Play className="ml-0.5 h-4 w-4 fill-white text-white" />
                  </div>
                </div>
              </div>
              <div className="min-w-0 flex-1">
                <p className="mb-3 line-clamp-4 text-sm leading-relaxed text-text-secondary">{caption}</p>
                <div className="flex flex-wrap gap-2">
                  {(hashtags.length ? hashtags : ["#content", "#social"]).map((tag) => (
                    <span
                      key={tag}
                      className="flex items-center gap-1 rounded border border-white/10 bg-white/5 px-2 py-1 text-[10px] font-mono text-text-tertiary"
                    >
                      <Hash className="h-3 w-3" />
                      {tag.replace(/^#/, "")}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <h4 className="mb-4 text-xs font-bold uppercase tracking-widest text-text-tertiary">Chỉ số hiệu suất</h4>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {[
                  { label: "Lượt xem / Reach", value: content?.reach || 0, icon: Eye, color: "text-blue-400" },
                  { label: "Tương tác", value: content?.engagement || 0, icon: Activity, color: "text-emerald-400" },
                  { label: "Bình luận", value: content?.comments || 0, icon: MessageCircle, color: "text-pink-400" },
                  { label: "Chia sẻ", value: content?.shares || 0, icon: Share2, color: "text-amber-400" },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-xl border border-white/5 bg-surface-card p-4">
                    <div className="mb-2 flex items-center gap-2 text-xs font-medium text-text-tertiary">
                      <stat.icon className={`h-3.5 w-3.5 ${stat.color}`} />
                      {stat.label}
                    </div>
                    <div className="text-2xl font-bold text-white">{formatCompactNumber(stat.value)}</div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-4 flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-widest text-text-tertiary">Phân bổ chỉ số nội dung</h4>
                <span className="flex items-center gap-1 rounded border border-accent-emerald/20 bg-accent-emerald/10 px-1.5 py-0.5 text-[10px] font-bold text-accent-emerald">
                  <TrendingUp className="h-3 w-3" />
                  Phân tích trực tiếp
                </span>
              </div>
              <div className="h-48 w-full rounded-xl border border-white/5 bg-obsidian-900 p-4">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timelineData}>
                    <defs>
                      <linearGradient id="contentMetricArea" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 10 }} dy={10} />
                    <YAxis hide />
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: "#1e1e24",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                    />
                    <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#contentMetricArea)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {activeTab === "audience" && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-white/5 bg-obsidian-900 p-4">
              <div className="mb-2 text-xs uppercase tracking-wider text-text-tertiary">Tỷ lệ tích cực</div>
              <div className="text-3xl font-bold text-white">{positiveRate}%</div>
            </div>
            <div className="rounded-xl border border-white/5 bg-obsidian-900 p-4">
              <div className="mb-2 text-xs uppercase tracking-wider text-text-tertiary">Người theo dõi tăng</div>
              <div className="text-3xl font-bold text-white">+{formatCompactNumber(content?.followersGained || 0)}</div>
            </div>
            <div className="rounded-xl border border-white/5 bg-obsidian-900 p-4">
              <div className="mb-2 text-xs uppercase tracking-wider text-text-tertiary">Lưu bài</div>
              <div className="text-3xl font-bold text-white">{formatCompactNumber(content?.saves || 0)}</div>
            </div>
          </div>
        )}

        {activeTab === "comments" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-widest text-text-tertiary">Bình luận liên quan</h4>
              <div className="rounded bg-white/5 px-2 py-1 text-xs text-text-secondary">
                Cảm xúc: <span className="font-bold text-accent-emerald">{positiveRate}% tích cực</span>
              </div>
            </div>
            <div className="space-y-4">
              {relatedComments.map((item: any) => (
                <div key={item.id} className="flex gap-4 rounded-xl border border-white/5 bg-obsidian-900 p-4">
                  <img src={item.authorAvatar} alt={item.authorName} className="h-10 w-10 shrink-0 rounded-full bg-white/10" />
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-baseline justify-between">
                      <span className="text-sm font-semibold text-text-primary">{item.authorName}</span>
                      <span className="text-[10px] text-text-tertiary">{item.timestamp}</span>
                    </div>
                    <p className="mb-3 text-sm text-text-secondary">{item.content}</p>
                    <div className="flex items-center gap-4 text-xs font-medium text-text-tertiary">
                      <span className="flex items-center gap-1.5">
                        <ThumbsUp className="h-3.5 w-3.5" />
                        {item.sentiment}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <MessageCircle className="h-3.5 w-3.5" />
                        {item.status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
              {!relatedComments.length && (
                <div className="py-8 text-center text-sm text-text-tertiary">Chưa có bình luận hoặc tin nhắn liên quan tới nội dung này.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
}
