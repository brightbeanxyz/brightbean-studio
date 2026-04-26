import React from "react";
import { Drawer } from "./Drawer";
import { AlertCard } from "./AlertCard";
import { useAppStore } from "@/store/AppContext";
import { CheckCircle2, Trash2 } from "lucide-react";
import { EmptyState } from "./EmptyState";

interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NotificationDrawer({ isOpen, onClose }: NotificationDrawerProps) {
  const { alerts, dismissAlert, clearAlerts } = useAppStore();

  return (
    <Drawer isOpen={isOpen} onClose={onClose} title="Thông Báo Hệ Thống" size="sm">
      <div className="flex flex-col h-full bg-obsidian-950">
        <div className="p-4 border-b border-white/5 flex items-center justify-between bg-obsidian-900/50">
          <span className="text-xs font-semibold text-text-tertiary uppercase tracking-widest">
            {alerts.length} Thông Báo Mới
          </span>
          {alerts.length > 0 && (
            <button onClick={clearAlerts} className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary hover:text-white transition-colors">
              <Trash2 className="w-3.5 h-3.5" /> Xóa Tất Cả
            </button>
          )}
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {alerts.length === 0 ? (
            <div className="h-full flex items-center justify-center">
               <EmptyState 
                  icon={CheckCircle2} 
                  title="Không có thông báo" 
                  description="Bạn đã đọc hết tất cả thông báo và cảnh báo."
               />
            </div>
          ) : (
            alerts.map((alert) => (
              <div key={alert.id} className="relative group">
                <AlertCard
                  {...alert}
                  onDismiss={() => dismissAlert(alert.id)}
                />
              </div>
            ))
          )}
        </div>
      </div>
    </Drawer>
  );
}
