import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatCompactNumber } from "@/lib/utils";

const COLORS = {
  youtube: "#ef4444", // Red
  tiktok: "#0ea5e9", // Cyan/Blue
  facebook: "#3b82f6", // Blue
  total: "#e4c580" // Gold
};

interface TrendChartProps {
  data: any[];
}

export function TrendChart({ data }: TrendChartProps) {
  return (
    <div className="w-full h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            {Object.entries(COLORS).map(([key, color]) => (
              <linearGradient key={key} id={`color${key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0.0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
          <XAxis 
            dataKey="date" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: "#71717a", fontSize: 12 }}
            dy={10}
            minTickGap={20}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: "#71717a", fontSize: 12 }} 
            tickFormatter={formatCompactNumber}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: "rgba(18, 18, 21, 0.9)", 
              backdropFilter: "blur(10px)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "12px",
              boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
              color: "#fff"
            }}
            itemStyle={{ color: "#e4c580" }}
          />
          {/* Main Total Line (Soft Gold) */}
          <Area type="monotone" dataKey="total" stroke={COLORS.total} fillOpacity={0.5} fill={`url(#colortotal)`} strokeWidth={2} />
          
          {/* Platform Specific Lines - subtle */}
          <Area type="monotone" dataKey="tiktok" stroke={COLORS.tiktok} fillOpacity={0} strokeWidth={1} strokeDasharray="4 4" />
          <Area type="monotone" dataKey="youtube" stroke={COLORS.youtube} fillOpacity={0} strokeWidth={1} strokeDasharray="4 4" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
