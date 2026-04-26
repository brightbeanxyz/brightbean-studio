import { useState } from "react";
import { X, RefreshCw, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/AppContext";

type Platform = "facebook" | "youtube" | "tiktok";
type ConnectMode = "oauth" | "token";

interface ConnectChannelModalProps {
  onClose: () => void;
  defaultGroupId?: string;
}

const PLATFORM_META: Record<Platform, { label: string; icon: string; card: string; badge: string }> = {
  facebook: {
    label: "Facebook",
    icon: "F",
    card: "hover:border-blue-500/50 hover:bg-blue-500/10",
    badge: "bg-blue-500/20 text-blue-500",
  },
  youtube: {
    label: "YouTube",
    icon: "Y",
    card: "hover:border-red-500/50 hover:bg-red-500/10",
    badge: "bg-red-500/20 text-red-500",
  },
  tiktok: {
    label: "TikTok",
    icon: "T",
    card: "hover:border-cyan-500/50 hover:bg-cyan-500/10",
    badge: "bg-cyan-500/20 text-cyan-500",
  },
};

export function ConnectChannelModal({ onClose, defaultGroupId = "all" }: ConnectChannelModalProps) {
  const { addChannel, importChannelToken } = useAppStore();
  const [mode, setMode] = useState<ConnectMode>("oauth");
  const [platform, setPlatform] = useState<Platform>("facebook");
  const [accessToken, setAccessToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [externalId, setExternalId] = useState("");
  const [scope, setScope] = useState("");
  const [expiresIn, setExpiresIn] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConnect = (selectedPlatform: Platform) => {
    addChannel(selectedPlatform, defaultGroupId);
  };

  const platformCard = (selectedPlatform: Platform) => {
    const meta = PLATFORM_META[selectedPlatform];
    return (
      <button
        key={selectedPlatform}
        onClick={() => (mode === "oauth" ? handleConnect(selectedPlatform) : setPlatform(selectedPlatform))}
        className={cn(
          "flex flex-col items-center justify-center gap-4 rounded-xl border border-white/5 bg-obsidian-800 p-6 transition-all",
          meta.card,
          mode === "token" && platform === selectedPlatform && "border-accent-blue bg-accent-blue/10",
        )}
      >
        <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl text-lg font-bold", meta.badge)}>{meta.icon}</div>
        <span className="font-semibold text-white">{meta.label}</span>
      </button>
    );
  };

  const handleImportToken = async () => {
    if (!accessToken.trim()) return;
    setIsSubmitting(true);
    const ok = await importChannelToken({
      platform,
      groupId: defaultGroupId,
      accessToken: accessToken.trim(),
      refreshToken: refreshToken.trim() || undefined,
      externalId: externalId.trim() || undefined,
      scope: scope.trim() || undefined,
      expiresIn: expiresIn.trim() ? Number(expiresIn) : undefined,
    });
    setIsSubmitting(false);
    if (ok) onClose();
  };

  const needsExternalId = platform === "facebook";

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-obsidian-950/80 p-4 backdrop-blur-sm">
      <div className="flex w-full max-w-3xl flex-col rounded-2xl border border-white/5 bg-obsidian-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/5 p-5">
          <div>
            <h2 className="text-lg font-bold text-white">Kết nối kênh mới</h2>
            <p className="mt-1 text-sm text-text-secondary">Chọn OAuth chuẩn hoặc nhập token API hợp lệ do bạn tự cấp từ app developer.</p>
          </div>
          <button onClick={onClose} className="rounded-xl p-2 text-text-tertiary transition-colors hover:bg-white/5 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="border-b border-white/5 px-5 pt-4">
          <div className="flex gap-2">
            <button
              onClick={() => setMode("oauth")}
              className={cn(
                "rounded-t-xl px-4 py-2 text-sm font-medium transition-colors",
                mode === "oauth" ? "bg-obsidian-800 text-white" : "text-text-secondary hover:text-white",
              )}
            >
              Kết nối OAuth
            </button>
            <button
              onClick={() => setMode("token")}
              className={cn(
                "rounded-t-xl px-4 py-2 text-sm font-medium transition-colors",
                mode === "token" ? "bg-obsidian-800 text-white" : "text-text-secondary hover:text-white",
              )}
            >
              Nhập token thủ công
            </button>
          </div>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {(["facebook", "youtube", "tiktok"] as Platform[]).map(platformCard)}
          </div>

          {mode === "oauth" ? (
            <p className="mt-6 text-sm text-text-secondary">
              Luồng này sẽ chuyển sang màn cấp quyền chính thức của nền tảng, sau đó quay lại workspace và tự đồng bộ dữ liệu.
            </p>
          ) : (
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    Chỉ hỗ trợ token API chính thức. Không hỗ trợ cookie, session browser hoặc cơ chế né đăng nhập của nền tảng.
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {needsExternalId && (
                  <div className="md:col-span-2">
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Page ID</label>
                    <input
                      type="text"
                      value={externalId}
                      onChange={(event) => setExternalId(event.target.value)}
                      placeholder="Nhập Facebook Page ID"
                      className="w-full rounded-xl border border-white/10 bg-obsidian-950 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-accent-blue"
                    />
                  </div>
                )}

                <div className="md:col-span-2">
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Access Token</label>
                  <textarea
                    value={accessToken}
                    onChange={(event) => setAccessToken(event.target.value)}
                    rows={5}
                    placeholder="Dán access token API hợp lệ"
                    className="w-full rounded-xl border border-white/10 bg-obsidian-950 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-accent-blue"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Refresh Token</label>
                  <textarea
                    value={refreshToken}
                    onChange={(event) => setRefreshToken(event.target.value)}
                    rows={3}
                    placeholder="Khuyến nghị cho YouTube và TikTok nếu bạn muốn tự refresh token"
                    className="w-full rounded-xl border border-white/10 bg-obsidian-950 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-accent-blue"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Expires In (giây)</label>
                  <input
                    type="number"
                    value={expiresIn}
                    onChange={(event) => setExpiresIn(event.target.value)}
                    placeholder="Ví dụ 3600"
                    className="w-full rounded-xl border border-white/10 bg-obsidian-950 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-accent-blue"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-text-tertiary">Scope</label>
                  <input
                    type="text"
                    value={scope}
                    onChange={(event) => setScope(event.target.value)}
                    placeholder="Danh sách quyền, phân tách bằng dấu phẩy"
                    className="w-full rounded-xl border border-white/10 bg-obsidian-950 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-accent-blue"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  onClick={handleImportToken}
                  disabled={isSubmitting || !accessToken.trim() || (needsExternalId && !externalId.trim())}
                  className="rounded-xl bg-text-primary px-5 py-3 text-sm font-medium text-obsidian-950 transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSubmitting ? "Đang xác thực token..." : `Nhập token ${PLATFORM_META[platform].label}`}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-white/5 bg-obsidian-950 p-5 text-sm text-text-tertiary">
          <div className="flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Đồng bộ kênh sẽ chạy ngay sau khi xác thực thành công.
          </div>
          <button onClick={onClose} className="font-medium text-text-secondary transition-colors hover:text-white">
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
}
