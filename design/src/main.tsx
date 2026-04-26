import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { supabaseConfigError } from './lib/supabase';

function ConfigErrorScreen({ message }: { message: string }) {
  return (
    <div className="min-h-screen bg-obsidian-950 text-text-primary flex items-center justify-center p-6">
      <div className="w-full max-w-2xl rounded-3xl border border-red-500/20 bg-obsidian-900/80 p-8 shadow-2xl">
        <div className="mb-4 text-xs font-bold uppercase tracking-[0.24em] text-red-400">Configuration Required</div>
        <h1 className="mb-3 text-3xl font-bold">Supabase chưa được cấu hình</h1>
        <p className="mb-6 text-sm leading-7 text-text-secondary">
          Ứng dụng không thể khởi động đầy đủ vì frontend đang dùng giá trị placeholder trong file <code>.env</code>.
        </p>
        <div className="rounded-2xl border border-white/10 bg-obsidian-950 p-4 font-mono text-sm text-text-primary">
          {message}
        </div>
        <div className="mt-6 space-y-2 text-sm text-text-secondary">
          <p>Cần thay giá trị thật cho:</p>
          <p><code>VITE_SUPABASE_URL</code></p>
          <p><code>VITE_SUPABASE_ANON_KEY</code></p>
          <p><code>SUPABASE_URL</code></p>
          <p><code>SUPABASE_ANON_KEY</code></p>
          <p><code>SUPABASE_SERVICE_ROLE_KEY</code></p>
        </div>
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {supabaseConfigError ? <ConfigErrorScreen message={supabaseConfigError} /> : <App />}
  </StrictMode>,
);
