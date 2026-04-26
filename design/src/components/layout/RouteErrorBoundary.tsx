import { Component, type ReactNode } from "react";

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
  errorMessage: string;
};

export class RouteErrorBoundary extends Component<Props, State> {
  declare props: Props;

  state: State = {
    hasError: false,
    errorMessage: "",
  };

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      errorMessage: error?.message || "Unknown route error",
    };
  }

  componentDidCatch(error: Error) {
    console.error("Route render failed:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-red-500/20 bg-obsidian-900/60 p-8">
          <div className="max-w-xl text-center">
            <div className="mb-3 text-xs font-bold uppercase tracking-[0.22em] text-red-400">Route Error</div>
            <h2 className="mb-3 text-2xl font-bold text-white">Trang này đang gặp lỗi hiển thị</h2>
            <p className="mb-4 text-sm leading-7 text-text-secondary">
              Ứng dụng đã chặn lỗi để tránh đen màn hình. Hãy tải lại trang hoặc quay lại menu khác.
            </p>
            <div className="mb-6 rounded-2xl border border-white/10 bg-obsidian-950 p-4 text-left font-mono text-sm text-text-primary">
              {this.state.errorMessage}
            </div>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={() => window.location.reload()}
                className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-obsidian-950 transition-colors hover:bg-white/90"
              >
                Tải lại trang
              </button>
              <button
                onClick={() => (window.location.href = "/")}
                className="rounded-xl border border-white/10 px-4 py-2 text-sm font-semibold text-text-primary transition-colors hover:bg-white/5"
              >
                Về tổng quan
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
