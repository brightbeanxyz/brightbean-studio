import { Tooltip, TooltipProps } from "recharts";
import { cn } from "@/lib/utils";

interface TinySparklineProps {
    data: number[];
    trend?: "up" | "down" | "neutral";
}

export function TinySparkline({ data, trend = "up" }: TinySparklineProps) {
    // A super simple SVG sparkline without the overhead of recharts for 6 tiny charts
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    
    // SVG viewBox standard 100x30
    const points = data.map((val, i) => {
        const x = (i / (data.length - 1)) * 100;
        const y = 30 - ((val - min) / range) * 30; // Invert Y
        return `${x},${y}`;
    }).join(" ");

    const color = trend === "up" ? "#10b981" : trend === "down" ? "#f87171" : "#a1a1aa";

    return (
        <svg viewBox="0 0 100 30" preserveAspectRatio="none" className="w-[60px] h-[24px] overflow-visible">
            <polyline
                fill="none"
                stroke={color}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
            />
            {/* Smooth area underneath */}
            <polyline
                fill={color}
                fillOpacity="0.1"
                stroke="none"
                points={`0,30 ${points} 100,30`}
            />
        </svg>
    )
}
