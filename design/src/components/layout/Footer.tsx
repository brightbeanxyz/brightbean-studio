import React from "react";
import { Sparkles, Heart } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full mt-auto relative z-10">
      {/* Exquisite gradient separator */}
      <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
      
      <div className="max-w-[1600px] mx-auto w-full px-4 md:px-8 py-5">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-obsidian-800 to-obsidian-950 flex items-center justify-center border border-white/10 shadow-soft-inset relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-tr from-accent-gold/10 to-accent-emerald/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <Sparkles className="w-3.5 h-3.5 text-accent-gold drop-shadow-[0_0_8px_rgba(228,197,128,0.6)]" />
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] font-bold text-white tracking-widest uppercase">QCWorks</span>
            </div>
          </div>
          
          <div className="flex flex-col items-center md:items-end gap-1">
            <span className="text-[12px] font-medium text-text-secondary">
              Copyright &copy; 2026 QCWorks. All rights reserved.
            </span>
            <span className="text-[10px] text-text-tertiary flex items-center gap-1.5 uppercase tracking-widest font-semibold">
              Designed with <Heart className="w-2.5 h-2.5 text-red-500 fill-red-500/30" /> by 
              <span className="text-accent-gold tracking-widest drop-shadow-[0_0_4px_rgba(228,197,128,0.3)]">
                Nguyễn Quốc Cường
              </span>
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
