import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Building2, Key, LogIn, User } from "lucide-react";
import { useAppStore } from "@/store/AppContext";
import { Card } from "@/components/ui/Card";
import { Footer } from "@/components/layout/Footer";
import { apiSend } from "@/lib/api";
import { supabase } from "@/lib/supabase";

export default function Login() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const { login, addAlert } = useAppStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier || !password) {
      addAlert({ type: "error", message: "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu." });
      return;
    }

    const result = await apiSend<{ session?: { access_token: string; refresh_token: string; user: any } }>(
      "/auth/sign-in",
      "POST",
      { identifier, password },
    ).catch((error) => {
      addAlert({ type: "error", message: error.message || "Sai tên đăng nhập hoặc mật khẩu." });
      return null;
    });

    if (!result?.session) return;

    const { error } = await supabase.auth.setSession({
      access_token: result.session.access_token,
      refresh_token: result.session.refresh_token,
    });
    if (error) {
      addAlert({ type: "error", message: error.message || "Không thể khởi tạo phiên đăng nhập." });
      return;
    }

    const sessionUser = result.session.user;
    login({
      name: sessionUser?.user_metadata?.full_name || sessionUser?.user_metadata?.username || sessionUser?.email,
      email: sessionUser?.email,
      username: sessionUser?.user_metadata?.username || sessionUser?.email?.split("@")[0] || "",
      role: "OWNER",
      avatar: sessionUser?.user_metadata?.avatar_url || "",
    });
    addAlert({ type: "info", message: "Đăng nhập thành công." });
    navigate("/");
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-obsidian-950 p-4">
      <div className="pointer-events-none absolute left-[-10%] top-[-10%] h-[40%] w-[40%] rounded-full bg-accent-blue/10 blur-[100px]" />
      <div className="pointer-events-none absolute bottom-[-10%] right-[-10%] h-[40%] w-[40%] rounded-full bg-accent-emerald/10 blur-[100px]" />

      <Card className="relative z-10 w-full max-w-md border border-white/10 bg-surface-elevated/80 p-8 shadow-elevated backdrop-blur-3xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-blue to-accent-emerald shadow-glow-blue">
            <Building2 className="h-8 w-8 text-white" />
          </div>
          <h1 className="mb-2 text-2xl font-bold tracking-tight text-white">Hệ Thống QCWorks</h1>
          <p className="text-text-secondary">Quản lý toàn bộ kênh phân phối và nội dung của bạn.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Tên đăng nhập</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-text-tertiary" />
              <input
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                className="w-full rounded-xl border border-border-default bg-obsidian-900 py-3 pl-10 pr-4 text-sm text-text-primary outline-none transition-colors focus:border-accent-blue focus:ring-1 focus:ring-accent-blue"
                placeholder="Tên người dùng của bạn"
              />
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Mật khẩu</label>
              <span className="text-xs font-medium text-text-tertiary">Username Auth</span>
            </div>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-text-tertiary" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-border-default bg-obsidian-900 py-3 pl-10 pr-4 text-sm text-text-primary outline-none transition-colors focus:border-accent-blue focus:ring-1 focus:ring-accent-blue"
                placeholder="Nhập mật khẩu"
              />
            </div>
          </div>

          <button
            type="submit"
            className="group mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-accent-blue px-4 py-3 text-sm font-bold text-white shadow-glow-blue transition-transform hover:scale-[1.02]"
          >
            Đăng Nhập <LogIn className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </button>
        </form>

        <div className="mt-8 text-center text-sm text-text-secondary">
          Chưa có tài khoản?{" "}
          <Link to="/register" className="font-semibold text-accent-blue transition-colors hover:text-white">
            Đăng ký ngay
          </Link>
        </div>
      </Card>

      <div className="absolute bottom-4 w-full">
        <Footer />
      </div>
    </div>
  );
}
