import React from "react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Clock } from "lucide-react";

interface ChannelCardProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  platform: "facebook" | "youtube" | "tiktok";
  followers: string;
  handle: string;
  status: "connected" | "disconnected" | "syncing";
  lastSync: string;
  avatar: string;
  key?: React.Key;
}

export function ChannelCard({
  name,
  platform,
  followers,
  handle,
  status,
  lastSync,
  avatar,
}: ChannelCardProps) {
  const getBadgeColors = () => {
    switch (platform) {
      case "youtube":
        return "bg-red-500 text-white";
      case "facebook":
        return "bg-blue-600 text-white";
      case "tiktok":
        return "bg-cyan-500 text-white";
    }
  };

  const getPlatformName = () => {
    switch (platform) {
      case "youtube":
        return "YouTube";
      case "facebook":
        return "Facebook";
      case "tiktok":
        return "TikTok";
    }
  };

  return (
    <Card className="p-4 flex items-center justify-between group hover:border-white/10 transition-colors">
      <div className="flex items-center gap-4 border-r border-white/5 pr-4 w-1/2">
        <div className="relative">
          <div className="w-12 h-12 rounded-xl overflow-hidden border border-white/10 shrink-0">
            <img
              src={avatar}
              alt={name}
              className="w-full h-full object-cover"
            />
          </div>
          <div
            className={cn(
              "absolute -bottom-1.5 -right-1.5 text-[10px] font-bold px-1.5 py-0.5 rounded shadow-lg",
              getBadgeColors(),
            )}
          >
            {getPlatformName().substring(0, 2)}
          </div>
        </div>
        <div className="truncate">
          <div className="font-semibold text-text-primary text-sm truncate">
            {name}
          </div>
          <div className="text-xs text-text-tertiary truncate">{handle}</div>
        </div>
      </div>

      <div className="w-1/4 px-4">
        <div className="text-sm font-semibold">{followers}</div>
        <div className="text-[10px] uppercase text-text-tertiary tracking-wider">
          Followers
        </div>
      </div>

      <div className="w-1/4 pl-4 flex flex-col items-end">
        <div className="flex items-center gap-1.5 mb-1">
          {status === "connected" ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-accent-emerald" />
          ) : (
            <AlertCircle className="w-3.5 h-3.5 text-red-500" />
          )}
          <span
            className={cn(
              "text-xs font-medium",
              status === "connected" ? "text-accent-emerald" : "text-red-500",
            )}
          >
            {status === "connected" ? "Active" : "Error"}
          </span>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-text-tertiary">
          <Clock className="w-3 h-3" /> {lastSync}
        </div>
      </div>
    </Card>
  );
}
