import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from "recharts";

interface PlatformMixChartProps {
  data: { name: string; value: number; fill: string }[];
  centerValue?: string;
  centerLabel?: string;
}

export function PlatformMixChart({ data, centerValue, centerLabel }: PlatformMixChartProps) {
  return (
    <div className="relative flex h-[300px] w-full flex-col items-center justify-center">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(18, 18, 21, 0.9)",
              backdropFilter: "blur(10px)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "12px",
              boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
              color: "#fff",
            }}
            itemStyle={{ color: "#fff" }}
            formatter={(value: number) => [value.toLocaleString(), "Reach"]}
          />
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            innerRadius="60%"
            outerRadius="85%"
            stroke="rgba(0,0,0,0)"
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Pie>
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            wrapperStyle={{ fontSize: "12px", color: "#a1a1aa" }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute left-1/2 top-[42%] -translate-x-1/2 -translate-y-1/2 text-center">
        <div className="text-3xl font-bold tracking-tight text-text-primary">{centerValue || data.length}</div>
        <div className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary">{centerLabel || "Nền tảng"}</div>
      </div>
    </div>
  );
}
