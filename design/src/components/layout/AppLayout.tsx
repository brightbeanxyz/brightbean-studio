import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { Footer } from "./Footer";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/AppContext";
import { Bell } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { RouteErrorBoundary } from "./RouteErrorBoundary";

export function AppLayout() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { alerts, dismissAlert } = useAppStore();
  const location = useLocation();
  
  // Show only the most recent unfixed alert as toast for 5 seconds
  const latestAlert = alerts.length > 0 ? alerts[0] : null;
  const [visibleToast, setVisibleToast] = useState<string | null>(null);

  useEffect(() => {
    if (latestAlert && latestAlert.id !== visibleToast) {
       setVisibleToast(latestAlert.id);
       const timer = setTimeout(() => setVisibleToast(null), 5000);
       return () => clearTimeout(timer);
    }
  }, [latestAlert]);

  return (
    <div className="flex h-screen overflow-hidden bg-obsidian-950 text-text-primary selection:bg-accent-blue/30 selection:text-white">
      <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />
      <div className="flex flex-col flex-1 w-full min-w-0 transition-all duration-300 relative z-0">
        <Topbar />
        
        {/* Global Toast */}
        <AnimatePresence>
          {visibleToast && latestAlert && (
            <motion.div
              initial={{ opacity: 0, x: 50, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 50, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
              className={cn(
                "fixed top-6 right-6 z-[100] w-full max-w-[380px] p-4 rounded-2xl border shadow-2xl flex items-start gap-4 cursor-pointer backdrop-blur-2xl transition-colors hover:bg-obsidian-800/95",
                "bg-obsidian-900/90",
                latestAlert.type === 'error' ? "border-red-500/40 shadow-red-500/10" : 
                latestAlert.type === 'warning' ? "border-accent-gold/40 shadow-accent-gold/10" : 
                latestAlert.type === 'success' ? "border-emerald-500/40 shadow-emerald-500/10" :
                "border-accent-blue/40 shadow-accent-blue/10"
              )}
              onClick={() => setVisibleToast(null)}
            >
              <div className={cn(
                 "w-10 h-10 rounded-full flex items-center justify-center shrink-0 border",
                 latestAlert.type === 'error' ? "bg-red-500/10 border-red-500/20 text-red-500" :
                 latestAlert.type === 'warning' ? "bg-accent-gold/10 border-accent-gold/20 text-accent-gold" :
                 latestAlert.type === 'success' ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500" :
                 "bg-accent-blue/10 border-accent-blue/20 text-accent-blue"
              )}>
                 <Bell className="w-5 h-5 flex-shrink-0" />
              </div>
              <div className="flex-1 pt-0.5 min-w-0">
                <p className="text-[15px] font-semibold text-white leading-tight mb-1">{latestAlert.title || 'Thông báo'}</p>
                <p className="text-[13px] text-text-secondary leading-relaxed line-clamp-2">{latestAlert.message}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <main className="flex-1 overflow-auto bg-obsidian-900 border-t border-white/5 shadow-soft-inset flex flex-col">
          <div className="w-full max-w-[1600px] mx-auto flex-1 p-4 md:p-6 lg:p-8">
            <RouteErrorBoundary key={location.pathname}>
              <Outlet />
            </RouteErrorBoundary>
          </div>
          <Footer />
        </main>
      </div>
    </div>
  );
}
