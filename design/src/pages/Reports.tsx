import { Download, Eye, Users } from "lucide-react";
import { useAppStore } from "@/store/AppContext";
import { KPICard } from "@/components/ui/KPICard";
import { Card } from "@/components/ui/Card";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from "recharts";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-obsidian-950 border border-white/10 p-3 rounded-lg shadow-elevated">
      <p className="text-text-secondary text-xs mb-1">{label}</p>
      {payload.map((entry: any, index: number) => (
        <p key={index} className="text-sm font-medium" style={{ color: entry.color }}>{entry.name}: {Number(entry.value || 0).toLocaleString()}</p>
      ))}
    </div>
  );
};

export default function Reports() {
  const { reports, addAlert } = useAppStore();
  const kpis = reports?.kpis || [];
  const compact = reports?.compact || [];
  const viewsData = reports?.viewsData || [];
  const platformData = reports?.platformData || [];

  const handleDownload = () => {
    const payload = JSON.stringify({ kpis, viewsData, platformData }, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "social-marketing-report.json";
    link.click();
    URL.revokeObjectURL(url);
    addAlert({ title: "Hoàn tất", message: "Đã xuất báo cáo JSON.", type: "info" });
  };

  return (
    <div className="flex flex-col gap-6 pb-20">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-accent-blue to-accent-emerald mb-1">Báo Cáo Toàn Diện</h1>
          <p className="text-sm text-text-secondary">Báo cáo đa kênh được tổng hợp từ dữ liệu workspace hiện tại.</p>
        </div>
        <button onClick={handleDownload} className="flex items-center gap-2 px-4 py-2 bg-obsidian-800 text-white border border-white/10 rounded-xl hover:bg-white/5 transition-colors shadow-elevated font-medium text-sm">
          <Download className="w-4 h-4" /> Xuất Báo Cáo
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((item: any) => (
          <div key={item.title}>
            <KPICard title={item.title} value={item.value} delta={item.delta || 0} sparklineData={item.sparklineData || []} />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="xl:col-span-2 p-6 flex flex-col h-[400px]">
          <h3 className="font-semibold text-text-primary mb-6 flex items-center gap-2"><Eye className="w-4 h-4 text-accent-blue" /> Lượt Xem & Tương Tác</h3>
          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={viewsData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff10" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#888" }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#888" }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: "12px", paddingTop: "20px" }} />
                <Area type="monotone" dataKey="views" name="Lượt Xem" stroke="#3b82f6" strokeWidth={2} fill="#3b82f633" />
                <Area type="monotone" dataKey="engagement" name="Tương Tác" stroke="#10b981" strokeWidth={2} fill="#10b98133" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-6 flex flex-col h-[400px]">
          <h3 className="font-semibold text-text-primary mb-6 flex items-center gap-2"><Users className="w-4 h-4 text-accent-gold" /> Phân Bổ Nền Tảng</h3>
          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={platformData} layout="vertical" margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal vertical={false} stroke="#ffffff10" />
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#888" }} width={80} />
                <Tooltip cursor={{ fill: "#ffffff05" }} content={<CustomTooltip />} />
                <Bar dataKey="value" name="Lượt Tiếp Cận" fill="#ef4444" radius={[0, 4, 4, 0]} barSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {compact.map((item: any) => (
          <div key={item.title}>
            <KPICard mode="compact" title={item.title} value={item.value} delta={item.delta || 0} />
          </div>
        ))}
      </div>
    </div>
  );
}
