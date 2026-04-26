import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Key, Mail, User, UserPlus } from "lucide-react";
import { useAppStore } from "@/store/AppContext";
import { Card } from "@/components/ui/Card";
import { Footer } from "@/components/layout/Footer";
import { apiSend } from "@/lib/api";
import { supabase } from "@/lib/supabase";

export default function Register() {
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { register, addAlert } = useAppStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !username || !password) {
      addAlert({ type: "error", message: "Vui lòng điền đầy đủ họ tên, tên đăng nhập và mật khẩu." });
      return;
    }

    const result = await apiSend<{ session?: { access_token: string; refresh_token: string; user: any } }>(
      "/auth/sign-up",
      "POST",
      { name, username, email, password },
    ).catch((error) => {
      addAlert({ type: "error", message: error.message || "Không thể đăng ký." });
      return null;
    });

    if (!result?.session) {
      addAlert({ type: "info", message: "Tài khoản đã được tạo. Hãy đăng nhập để tiếp tục." });
      navigate("/login");
      return;
    }

    const { error } = await supabase.auth.setSession({
      access_token: result.session.access_token,
      refresh_token: result.session.refresh_token,
    });
    if (error) {
      addAlert({ type: "error", message: error.message || "Không thể khởi tạo phiên đăng nhập." });
      return;
    }

    register({
      name,
      email: result.session.user?.email || email,
      username,
      role: "OWNER",
      avatar: "",
    });
    addAlert({ type: "info", message: "Đăng ký thành công." });
    navigate("/");
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-obsidian-950 p-4">
      <div className="pointer-events-none absolute right-[-10%] top-[20%] h-[40%] w-[40%] rounded-full bg-accent-gold/10 blur-[100px]" />
      <div className="pointer-events-none absolute bottom-[10%] left-[-10%] h-[40%] w-[40%] rounded-full bg-accent-blue/10 blur-[100px]" />

      <Card className="relative z-10 w-full max-w-md border border-white/10 bg-surface-elevated/80 p-8 shadow-elevated backdrop-blur-3xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-gold to-accent-emerald shadow-glow-emerald">
            <UserPlus className="h-8 w-8 text-white" />
          </div>
          <h1 className="mb-2 text-2xl font-bold tracking-tight text-white">Tài Khoản QCWorks</h1>
          <p className="text-text-secondary">Bắt đầu quản lý kênh của bạn chỉ sau vài giây.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Họ và tên</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-text-tertiary" />
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-border-default bg-obsidian-900 py-3 pl-10 pr-4 text-sm text-text-primary outline-none transition-colors focus:border-accent-gold focus:ring-1 focus:ring-accent-gold"
                placeholder="Nguyễn Quốc Cường"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Tên đăng nhập</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-text-tertiary" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-xl border border-border-default bg-obsidian-900 py-3 pl-10 pr-4 text-sm text-text-primary outline-none transition-colors focus:border-accent-gold focus:ring-1 focus:ring-accent-gold"
                placeholder="Tên người dùng của bạn"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Email nội bộ (không bắt buộc)</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-text-tertiary" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-border-default bg-obsidian-900 py-3 pl-10 pr-4 text-sm text-text-primary outline-none transition-colors focus:border-accent-gold focus:ring-1 focus:ring-accent-gold"
                placeholder="you@company.local"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Mật khẩu</label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-text-tertiary" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-border-default bg-obsidian-900 py-3 pl-10 pr-4 text-sm text-text-primary outline-none transition-colors focus:border-accent-gold focus:ring-1 focus:ring-accent-gold"
                placeholder="Nhập mật khẩu"
              />
            </div>
          </div>

          <button
            type="submit"
            className="group mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-accent-gold px-4 py-3 text-sm font-bold text-obsidian-950 shadow-[0_0_15px_rgba(228,197,128,0.4)] transition-transform hover:scale-[1.02]"
          >
            Đăng Ký Ngay <UserPlus className="h-4 w-4 transition-transform group-hover:scale-110" />
          </button>
        </form>

        <div className="mt-8 text-center text-sm text-text-secondary">
          Đã có tài khoản?{" "}
          <Link to="/login" className="font-semibold text-accent-gold transition-colors hover:text-white">
            Đăng nhập
          </Link>
        </div>
      </Card>

      <div className="absolute bottom-4 w-full">
        <Footer />
      </div>
    </div>
  );
}
