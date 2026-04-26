import { Navigate, Outlet } from "react-router-dom";
import { useAppStore } from "@/store/AppContext";

export function ProtectedRoute() {
  const { user, authReady } = useAppStore();

  if (!authReady) {
    return <div className="min-h-screen bg-obsidian-950" />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
