import React, { useState, useMemo, useEffect } from "react";
import {
  ChevronDown,
  ChevronUp,
  Search,
  Filter,
  MoreHorizontal,
  CheckSquare,
  Square,
  Maximize2,
  Minimize2,
  ArrowUpDown,
  Download,
  Trash2,
  Edit3,
  Image as ImageIcon,
  MessageSquare,
  Share2,
  Bookmark,
  Users,
  ChevronRight,
  Activity,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "motion/react";
import { useAppStore } from "@/store/AppContext";
import { ContentDetailDrawer } from "./ContentDetailDrawer";

type SortConfig = {
  key: string | null;
  direction: "asc" | "desc";
};
type Density = "compact" | "comfortable";

export interface ContentDataTableProps {
  data?: any[];
  onSelect?: (id: string | null) => void;
  selectedId?: string | null;
}

export function ContentDataTable({ data: propData, onSelect, selectedId }: ContentDataTableProps) {
  const { groups } = useAppStore();
  const data = propData || [];

  const [search, setSearch] = useState("");
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    key: "date",
    direction: "desc",
  });
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [expandedId, setExpandedId] = useState<string | null>(null);
  
  // Use controlled state if provided, otherwise local state for detail drawer
  const [localSelectedRowId, setLocalSelectedRowId] = useState<string | null>(null);
  const selectedRowId = selectedId !== undefined ? selectedId : localSelectedRowId;
  const setSelectedRowId = onSelect || setLocalSelectedRowId;

  const [density, setDensity] = useState<Density>("comfortable");
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const itemsPerPage = 5;

  const handleSort = (key: string) => {
    let direction: "asc" | "desc" = "asc";
    if (sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }
    setSortConfig({ key, direction });
  };

  const sortedData = useMemo(() => {
    let sortableItems = [...data];
    if (sortConfig.key) {
      sortableItems.sort((a, b) => {
        const aVal = a[sortConfig.key!];
        const bVal = b[sortConfig.key!];
        
        if (aVal < bVal)
          return sortConfig.direction === "asc" ? -1 : 1;
        if (aVal > bVal)
          return sortConfig.direction === "asc" ? 1 : -1;
        return 0;
      });
    }

    if (search) {
      const lowerSearch = search.toLowerCase();
      sortableItems = sortableItems.filter(
        (item) =>
          item.title?.toLowerCase().includes(lowerSearch) ||
          item.channel?.toLowerCase().includes(lowerSearch),
      );
    }

    return sortableItems;
  }, [data, sortConfig, search]);

  const currentData = sortedData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage,
  );
  const totalPages = Math.ceil(sortedData.length / itemsPerPage);

  // Reset page when data changes or search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [data.length, search, sortConfig.key, sortConfig.direction]);

  const toggleSelectAll = () => {
    if (selectedIds.size === currentData.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(currentData.map((item) => item.id)));
    }
  };

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return num.toString();
  };

  const Th = ({
    children,
    sortKey,
    className,
    align = "left",
  }: {
    children: React.ReactNode;
    sortKey?: string;
    className?: string;
    align?: "left" | "right" | "center";
  }) => (
    <th
      className={cn(
        "px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-text-tertiary bg-surface-card border-b border-white/5 whitespace-nowrap sticky top-0 z-20",
        align === "right"
          ? "text-right"
          : align === "center"
            ? "text-center"
            : "text-left",
        sortKey
          ? "cursor-pointer hover:text-text-primary hover:bg-white/[0.02] transition-colors group"
          : "",
        className,
      )}
      onClick={() => sortKey && handleSort(sortKey)}
    >
      <div
        className={cn(
          "flex items-center gap-1.5",
          align === "right"
            ? "justify-end"
            : align === "center"
              ? "justify-center"
              : "justify-start",
        )}
      >
        {children}
        {sortKey && (
          <div className="flex flex-col opacity-0 group-hover:opacity-100 transition-opacity">
            <ChevronUp
              className={cn(
                "w-2 h-2 -mb-0.5",
                sortConfig.key === sortKey && sortConfig.direction === "asc"
                  ? "opacity-100 text-accent-blue"
                  : "opacity-50",
              )}
            />
            <ChevronDown
              className={cn(
                "w-2 h-2",
                sortConfig.key === sortKey && sortConfig.direction === "desc"
                  ? "opacity-100 text-accent-blue"
                  : "opacity-50",
              )}
            />
          </div>
        )}
      </div>
    </th>
  );

  return (
    <div className="flex flex-col w-full bg-obsidian-950 border border-white/10 rounded-2xl overflow-hidden shadow-card relative">
      {/* Table Toolbar */}
      <div className="flex items-center justify-between p-4 border-b border-white/5 bg-surface-card/50">
        <div className="flex items-center gap-4">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary group-focus-within:text-accent-blue transition-colors" />
            <input
              type="text"
              placeholder="Search content..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-1.5 bg-obsidian-900 border border-white/10 rounded-lg text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent-blue/50 focus:ring-1 focus:ring-accent-blue/50 w-64 transition-all"
            />
          </div>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-white/5 border border-white/5 transition-colors">
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>

        <div className="flex items-center gap-3">
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2 mr-4 animate-in fade-in slide-in-from-right-4">
              <span className="text-sm font-medium text-accent-blue">
                {selectedIds.size} selected
              </span>
              <div className="w-px h-4 bg-white/10"></div>
              <button className="p-1.5 text-text-secondary hover:text-white hover:bg-white/10 rounded-md transition-colors">
                <Edit3 className="w-4 h-4" />
              </button>
              <button className="p-1.5 text-text-secondary hover:text-white hover:bg-white/10 rounded-md transition-colors">
                <Download className="w-4 h-4" />
              </button>
              <button className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded-md transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          )}
          <button
            onClick={() =>
              setDensity(density === "compact" ? "comfortable" : "compact")
            }
            className="p-1.5 text-text-secondary hover:text-white hover:bg-white/5 rounded-md transition-colors border border-transparent hover:border-white/10"
            title={`Switch to ${density === "compact" ? "comfortable" : "compact"} density`}
          >
            {density === "compact" ? (
              <Maximize2 className="w-4 h-4" />
            ) : (
              <Minimize2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto relative min-h-[300px]">
        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-obsidian-950/50 backdrop-blur-sm z-50 flex items-center justify-center animate-in fade-in">
            <div className="w-8 h-8 rounded-full border-2 border-accent-blue/30 border-t-accent-blue animate-spin"></div>
          </div>
        )}

        <table className="w-full text-sm text-left">
          <thead>
            <tr>
              <th className="px-4 py-3 bg-surface-card border-b border-white/5 w-10 sticky left-0 z-30">
                <button
                  onClick={toggleSelectAll}
                  className="text-text-tertiary hover:text-text-primary transition-colors"
                >
                  {selectedIds.size === currentData.length &&
                  currentData.length > 0 ? (
                    <CheckSquare className="w-4 h-4 text-accent-blue" />
                  ) : (
                    <Square className="w-4 h-4" />
                  )}
                </button>
              </th>
              {/* Sticky first column header */}
              <Th
                sortKey="title"
                className="sticky left-10 z-30 shadow-[1px_0_0_rgba(255,255,255,0.05)] w-[300px]"
              >
                Content
              </Th>
              <Th sortKey="platform">Platform</Th>
              <Th sortKey="date">Date</Th>
              <Th sortKey="reach" align="right">
                Reach
              </Th>
              <Th sortKey="engagement" align="right">
                Engagement
              </Th>
              <Th sortKey="comments" align="right">
                Comments
              </Th>
              <Th sortKey="shares" align="right">
                Shares
              </Th>
              <Th sortKey="performanceScore" align="center">
                Score
              </Th>
              <Th align="center">Action</Th>
            </tr>
          </thead>
          <tbody>
            {currentData.length === 0 && !isLoading ? (
              <tr>
                <td
                  colSpan={10}
                  className="px-4 py-16 text-center text-text-tertiary"
                >
                  <div className="flex flex-col items-center justify-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
                      <Search className="w-5 h-5 text-text-tertiary" />
                    </div>
                    <p className="text-sm">No content matches your filters.</p>
                  </div>
                </td>
              </tr>
            ) : (
              currentData.map((row) => (
                <React.Fragment key={row.id}>
                  <tr
                    className={cn(
                      "group border-b border-white/[0.03] transition-colors hover:bg-white/[0.02]",
                      selectedIds.has(row.id) &&
                        "bg-accent-blue/5 hover:bg-accent-blue/10",
                      expandedId === row.id &&
                        "bg-white/[0.02] border-transparent",
                    )}
                  >
                    <td
                      className={cn(
                        "px-4 bg-obsidian-950 group-hover:bg-obsidian-900 transition-colors sticky left-0 z-10",
                        selectedIds.has(row.id) && "bg-obsidian-900",
                        density === "compact" ? "py-2" : "py-3",
                      )}
                    >
                      <button
                        onClick={() => toggleSelect(row.id)}
                        className="text-text-tertiary hover:text-text-primary transition-colors"
                      >
                        {selectedIds.has(row.id) ? (
                          <CheckSquare className="w-4 h-4 text-accent-blue" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>
                    </td>

                    {/* Content Column (Sticky) */}
                    <td
                      className={cn(
                        "px-4 bg-obsidian-950 group-hover:bg-obsidian-900 transition-colors sticky left-10 z-10 shadow-[1px_0_0_rgba(255,255,255,0.05)]",
                        selectedIds.has(row.id) && "bg-obsidian-900",
                        density === "compact" ? "py-2" : "py-3",
                      )}
                    >
                      <div className="flex items-center gap-3 w-[260px]">
                        <div
                          className={cn(
                            "rounded-lg overflow-hidden shrink-0 border border-white/10 bg-obsidian-900",
                            density === "compact" ? "w-8 h-8" : "w-10 h-10",
                          )}
                        >
                          {row.thumbnail ? (
                            <img
                              src={row.thumbnail}
                              alt=""
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <ImageIcon className="w-4 h-4 m-auto mt-2 text-text-tertiary" />
                          )}
                        </div>
                        <div className="flex flex-col overflow-hidden">
                          <button
                            onClick={() => setSelectedRowId(row.id)}
                            className="font-semibold text-left text-text-primary truncate group-hover:text-accent-blue transition-colors hover:underline"
                          >
                            {row.title}
                          </button>
                          <span className="text-[11px] text-text-tertiary truncate">
                            {row.channel}
                            {row.groupId && (
                              <>
                                <span className="mx-1">•</span>
                                {groups.find(g => g.id === row.groupId)?.name || 'Không có nhóm'}
                              </>
                            )}
                          </span>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="inline-flex items-center justify-center px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-widest bg-white/5 border border-white/10 text-white">
                        {row.platform}
                      </span>
                    </td>

                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="text-text-primary">
                          {new Date(row.date).toLocaleDateString("vi-VN")}
                        </span>
                        <span className="text-[11px] text-text-tertiary">
                          {new Date(row.date).toLocaleTimeString("vi-VN", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </td>

                    <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-text-primary">
                      {formatNumber(row.reach)}
                    </td>

                    <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-text-primary">
                      {formatNumber(row.engagement)}
                    </td>

                    <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-text-secondary">
                      {formatNumber(row.comments)}
                    </td>

                    <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-text-secondary">
                      {formatNumber(row.shares)}
                    </td>

                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-white/5 border border-white/5">
                        <Activity
                          className={cn(
                            "w-3.5 h-3.5",
                            row.performanceScore >= 90
                              ? "text-accent-emerald"
                              : row.performanceScore >= 70
                                ? "text-accent-gold"
                                : "text-text-tertiary",
                          )}
                        />
                        <span
                          className={cn(
                            "font-bold text-xs",
                            row.performanceScore >= 90
                              ? "text-accent-emerald"
                              : row.performanceScore >= 70
                                ? "text-accent-gold"
                                : "text-text-primary",
                          )}
                        >
                          {row.performanceScore}
                        </span>
                      </div>
                    </td>

                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => toggleExpand(row.id)}
                          className={cn(
                            "p-1.5 rounded-md hover:bg-white/10 transition-colors",
                            expandedId === row.id
                              ? "bg-white/10 text-white"
                              : "text-text-tertiary hover:text-text-primary",
                          )}
                        >
                          <ChevronDown
                            className={cn(
                              "w-4 h-4 transition-transform",
                              expandedId === row.id && "rotate-180",
                            )}
                          />
                        </button>
                        <button className="p-1.5 text-text-tertiary hover:text-text-primary hover:bg-white/10 rounded-md transition-colors">
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Expanded Row Content */}
                  <AnimatePresence>
                    {expandedId === row.id && (
                      <motion.tr
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="bg-white/[0.01] border-b border-white/[0.03]"
                      >
                        <td colSpan={10} className="p-0 overflow-hidden">
                          <div className="p-6 ml-10 border-l-2 border-accent-blue/30 h-full flex flex-col md:flex-row gap-6">
                            {/* Detailed Stats */}
                            <div className="flex-1 grid grid-cols-2 lg:grid-cols-4 gap-4">
                              <div className="bg-obsidian-900 border border-white/5 p-3 rounded-xl">
                                <div className="flex items-center gap-2 text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">
                                  <Bookmark className="w-3.5 h-3.5" /> Saves
                                </div>
                                <div className="text-xl font-bold text-white font-mono">
                                  {formatNumber(row.saves)}
                                </div>
                              </div>
                              <div className="bg-obsidian-900 border border-white/5 p-3 rounded-xl">
                                <div className="flex items-center gap-2 text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">
                                  <Users className="w-3.5 h-3.5" /> Thêm theo
                                  dõi
                                </div>
                                <div className="text-xl font-bold text-white font-mono">
                                  +{formatNumber(row.followersGained)}
                                </div>
                              </div>
                              <div className="bg-obsidian-900 border border-white/5 p-3 rounded-xl">
                                <div className="flex items-center gap-2 text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">
                                  <MessageSquare className="w-3.5 h-3.5" /> Tỉ
                                  lệ phản hồi
                                </div>
                                <div className="text-xl font-bold text-white font-mono">
                                  24.5%
                                </div>
                              </div>
                              <div className="bg-obsidian-900 border border-white/5 p-3 rounded-xl flex items-center justify-center">
                                <button
                                  onClick={() => setSelectedRowId(row.id)}
                                  className="flex items-center gap-2 text-sm font-medium text-accent-blue hover:text-accent-blue/80 transition-colors"
                                >
                                  Xem chi tiết{" "}
                                  <ChevronRight className="w-4 h-4" />
                                </button>
                              </div>
                            </div>
                          </div>
                        </td>
                      </motion.tr>
                    )}
                  </AnimatePresence>
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between p-4 border-t border-white/5 bg-surface-card/50">
        <div className="text-sm text-text-secondary">
          Showing{" "}
          <span className="font-medium text-white">
            {Math.min((currentPage - 1) * itemsPerPage + 1, sortedData.length)}
          </span>{" "}
          to{" "}
          <span className="font-medium text-white">
            {Math.min(currentPage * itemsPerPage, sortedData.length)}
          </span>{" "}
          of <span className="font-medium text-white">{sortedData.length}</span>{" "}
          results
        </div>
        <div className="flex items-center gap-2">
          <button
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((p) => p - 1)}
            className="px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 text-sm font-medium text-text-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <div className="flex items-center gap-1">
            {[...Array(totalPages)].map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentPage(i + 1)}
                className={cn(
                  "w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium transition-colors",
                  currentPage === i + 1
                    ? "bg-accent-blue text-white"
                    : "text-text-secondary hover:bg-white/5",
                )}
              >
                {i + 1}
              </button>
            ))}
          </div>
          <button
            disabled={currentPage === totalPages || totalPages === 0}
            onClick={() => setCurrentPage((p) => p + 1)}
            className="px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 text-sm font-medium text-text-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      </div>

      <ContentDetailDrawer
        isOpen={!!selectedRowId}
        onClose={() => setSelectedRowId(null)}
        contentId={selectedRowId}
      />
    </div>
  );
}
