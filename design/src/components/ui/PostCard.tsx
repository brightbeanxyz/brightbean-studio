import React from "react";
import { cn } from "@/lib/utils";
import {
  Facebook,
  Youtube,
  Instagram,
  Twitter,
  Linkedin,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileEdit,
  Send,
  Eye,
  Activity,
  User,
  Image as ImageIcon,
  MoreHorizontal,
} from "lucide-react";

export type PostStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "scheduled"
  | "published"
  | "failed";
export type Platform =
  | "facebook"
  | "youtube"
  | "instagram"
  | "twitter"
  | "linkedin"
  | "tiktok";

export interface PostCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  platform: Platform;
  group?: string;
  time: string;
  status: PostStatus;
  performance?: {
    views?: string;
    engagement?: string;
    score?: number;
  };
  thumbnail?: string;
  assignedUser?: {
    name: string;
    avatar?: string;
  };
  variant?: "default" | "compact";
  isDragging?: boolean;
  isSelected?: boolean;
  onPostClick?: () => void;
  className?: string;
  key?: React.Key;
}

const statusConfig: Record<
  PostStatus,
  { icon: any; colorClass: string; label: string; bgClass: string }
> = {
  draft: {
    icon: FileEdit,
    colorClass: "text-text-tertiary",
    bgClass: "bg-white/5",
    label: "Bản nháp",
  },
  pending_approval: {
    icon: Clock,
    colorClass: "text-amber-400",
    bgClass: "bg-amber-400/10",
    label: "Chờ duyệt",
  },
  approved: {
    icon: CheckCircle2,
    colorClass: "text-cyan-400",
    bgClass: "bg-cyan-400/10",
    label: "Đã duyệt",
  },
  scheduled: {
    icon: Send,
    colorClass: "text-accent-blue",
    bgClass: "bg-accent-blue/10",
    label: "Đã lên lịch",
  },
  published: {
    icon: Eye,
    colorClass: "text-accent-emerald",
    bgClass: "bg-accent-emerald/10",
    label: "Đã đăng",
  },
  failed: {
    icon: AlertCircle,
    colorClass: "text-red-400",
    bgClass: "bg-red-400/10",
    label: "Đăng lỗi",
  },
};

const platformIconMap: Record<Platform, any> = {
  facebook: Facebook,
  youtube: Youtube,
  instagram: Instagram,
  twitter: Twitter,
  linkedin: Linkedin,
  tiktok: Activity, // Fallback for tiktok
};

export function PostCard({
  title,
  platform,
  group,
  time,
  status,
  performance,
  thumbnail,
  assignedUser,
  variant = "default",
  isDragging = false,
  isSelected = false,
  onPostClick,
  className,
  ...props
}: PostCardProps) {
  const StatusIcon = statusConfig[status].icon;
  const PlatformIcon = platformIconMap[platform] || Activity;

  const isCompact = variant === "compact";

  return (
    <div className="relative group/post">
      {/* Premium Hover Tooltip (appears on top or bottom depending on position, but simplified here) */}
      <div className="absolute z-50 left-full top-0 ml-2 w-64 bg-surface-elevated border border-border-default rounded-xl shadow-2xl p-3 opacity-0 invisible group-hover/post:opacity-100 group-hover/post:visible transition-all duration-200 pointer-events-none translate-x-[-10px] group-hover/post:translate-x-0">
        <div className="flex items-center gap-2 mb-2">
          <PlatformIcon className="w-4 h-4 text-text-secondary" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-text-tertiary">
            {group || "General"}
          </span>
        </div>
        <p className="text-sm font-semibold text-white mb-2 line-clamp-2">
          {title}
        </p>
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-secondary">{time}</span>
          <div
            className={cn(
              "flex items-center gap-1 font-medium",
              statusConfig[status].colorClass,
            )}
          >
            <StatusIcon className="w-3.5 h-3.5" />
            {statusConfig[status].label}
          </div>
        </div>
      </div>

      <div
        onClick={onPostClick}
        className={cn(
          "relative overflow-hidden flex flex-col rounded-xl border bg-surface-card transition-all cursor-grab active:cursor-grabbing",
          isDragging
            ? "opacity-60 shadow-none scale-95 border-white/5"
            : "hover:border-white/15 shadow-sm hover:shadow-hover-elevation hover:-translate-y-0.5",
          isSelected
            ? "border-accent-blue bg-accent-blue/5 ring-1 ring-accent-blue/30"
            : "border-white/5",
          isCompact ? "p-2 gap-1.5" : "p-3 gap-2.5",
          className,
        )}
        {...props}
      >
        {/* Top/Header Area */}
        <div className="flex items-start justify-between gap-2">
          {/* Platform and Group */}
          <div className="flex items-center gap-1.5 min-w-0">
            <div className="w-5 h-5 rounded-md bg-white/5 flex items-center justify-center shrink-0">
              <PlatformIcon className="w-3 h-3 text-text-secondary" />
            </div>
            {!isCompact && group && (
              <span className="text-[10px] font-bold uppercase tracking-widest text-text-tertiary truncate">
                {group}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-xs font-mono text-text-secondary">
              {time}
            </span>
            <div
              className={cn(
                "w-2 h-2 rounded-full",
                statusConfig[status].bgClass,
              )}
            >
              <div
                className={cn(
                  "w-full h-full rounded-full opacity-60 mix-blend-screen",
                  statusConfig[status].colorClass,
                )}
              ></div>
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex gap-2.5">
          {/* Thumbnail / Media Hint */}
          {(thumbnail || status === "draft" || isCompact === false) && (
            <div
              className={cn(
                "shrink-0 rounded-md overflow-hidden bg-obsidian-950 border border-white/5 relative flex items-center justify-center",
                isCompact ? "w-8 h-8" : "w-12 h-12",
              )}
            >
              {thumbnail ? (
                <img
                  src={thumbnail}
                  alt=""
                  className="w-full h-full object-cover"
                />
              ) : (
                <ImageIcon className="w-4 h-4 text-text-tertiary opacity-50" />
              )}
            </div>
          )}

          <div className="flex-1 min-w-0 flex flex-col">
            <h4
              className={cn(
                "font-medium text-text-primary truncate group-hover/post:text-white transition-colors",
                isCompact
                  ? "text-xs"
                  : "text-sm leading-snug line-clamp-2 white-space-normal",
              )}
            >
              {title}
            </h4>

            {/* Detailed view extra info */}
            {!isCompact && (
              <div className="mt-auto pt-1.5 flex items-center justify-between">
                <div className="flex items-center gap-1">
                  {assignedUser?.avatar ? (
                    <img
                      src={assignedUser.avatar}
                      alt={assignedUser.name}
                      className="w-4 h-4 rounded-full"
                    />
                  ) : (
                    <div className="w-4 h-4 rounded-full bg-white/10 flex items-center justify-center">
                      <User className="w-2.5 h-2.5 text-text-secondary" />
                    </div>
                  )}
                </div>

                {performance && status === "published" ? (
                  <div className="flex items-center gap-2 text-[10px] font-mono text-text-secondary">
                    {performance.views && (
                      <span className="flex items-center gap-0.5">
                        <Eye className="w-3 h-3" />
                        {performance.views}
                      </span>
                    )}
                    {performance.score && (
                      <span
                        className={cn(
                          "flex items-center gap-0.5 px-1 py-0.5 rounded font-bold",
                          performance.score >= 90
                            ? "text-accent-emerald bg-accent-emerald/10"
                            : "text-text-primary bg-white/5",
                        )}
                      >
                        <Activity className="w-3 h-3" />
                        {performance.score}
                      </span>
                    )}
                  </div>
                ) : (
                  <div
                    className={cn(
                      "text-[10px] font-medium px-1.5 py-0.5 rounded",
                      statusConfig[status].colorClass,
                      statusConfig[status].bgClass,
                    )}
                  >
                    {statusConfig[status].label}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Selected Indicator */}
        {isSelected && (
          <div className="absolute top-1/2 -left-1 w-2 h-8 -translate-y-1/2 bg-accent-blue rounded-r-full shadow-glow-blue"></div>
        )}
      </div>
    </div>
  );
}
