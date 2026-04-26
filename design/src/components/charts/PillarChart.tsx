import { ResponsiveContainer, Radar, RadarChart, PolarGrid, PolarAngleAxis, Tooltip } from "recharts";

interface PillarChartProps {
  data: { subject: string; value: number; fullMark: number }[];
}

export function PillarChart({ data }: PillarChartProps) {
  return (
    <div className="w-full h-[280px] flex items-center justify-center">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="rgba(255,255,255,0.1)" />
          <PolarAngleAxis 
            dataKey="subject" 
            tick={{ fill: "#a1a1aa", fontSize: 11, fontWeight: 500 }} 
          />
          <Tooltip 
             contentStyle={{ 
              backgroundColor: "rgba(18, 18, 21, 0.9)", 
              backdropFilter: "blur(10px)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
              color: "#fff",
              fontSize: "12px"
            }}
            itemStyle={{ color: "#8b5cf6" }}
          />
          <Radar
            name="Engagement Score"
            dataKey="value"
            stroke="#8b5cf6"
            fill="#8b5cf6"
            fillOpacity={0.4}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
