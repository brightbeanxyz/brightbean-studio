import React, { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  Building2,
  ChevronRight,
  ChevronDown,
  Check,
  Search,
  Plus,
  Pin,
  Activity,
  Facebook,
  Youtube,
  Command,
  Clock,
  Hash,
  X,
  Trash2,
  Edit2
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "motion/react";
import { useAppStore, GroupData } from "@/store/AppContext";

const platformIcons: Record<string, any> = {
  facebook: Facebook,
  youtube: Youtube,
  tiktok: Hash, // Using Hash as a fallback for TikTok if not available in Lucide
};

const GroupItem: React.FC<{
  group: GroupData;
  isSelected: boolean;
  onClick: () => void;
  onTogglePin?: (e: React.MouseEvent) => void;
}> = ({ group, isSelected, onClick, onTogglePin }) => {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left p-2.5 rounded-xl transition-all group/item flex items-start gap-3 relative overflow-hidden",
        isSelected
          ? "bg-accent-blue/10 border border-accent-blue/20 ring-1 ring-accent-blue/10"
          : "hover:bg-white/[0.04] border border-transparent hover:border-white/5",
      )}
    >
      {/* Selection Indicator Background Pulse */}
      {isSelected && (
        <div className="absolute inset-0 bg-gradient-to-r from-accent-blue/10 to-transparent opacity-50"></div>
      )}

      {/* selection tick */}
      {isSelected && (
        <div className="absolute top-1/2 -left-1 w-2 h-6 -translate-y-1/2 bg-accent-blue rounded-r-full shadow-glow-blue"></div>
      )}

      <div className="relative z-10 shrink-0 mt-0.5">
        <div
          className={cn(
            "w-10 h-10 rounded-xl flex items-center justify-center border shadow-soft-inset",
            isSelected
              ? "bg-accent-blue/20 border-accent-blue/30 text-accent-blue"
              : "bg-obsidian-900 border-white/10 text-text-tertiary group-hover/item:text-text-secondary",
          )}
        >
          <Building2 className="w-5 h-5" />
        </div>
        {/* Health Indicator */}
        <div
          className={cn(
            "absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full border-2 border-surface-elevated flex items-center justify-center",
            group.health === "healthy"
              ? "bg-accent-emerald text-accent-emerald border-none shadow-[0_0_8px_rgba(16,185,129,0.5)]"
              : group.health === "warning"
                ? "bg-accent-gold text-accent-gold border-none shadow-[0_0_8px_rgba(228,197,128,0.5)]"
                : "bg-red-500 text-red-500 border-none shadow-[0_0_8px_rgba(239,68,68,0.5)]",
          )}
        >
          {group.health === "error" && (
            <div className="w-1.5 h-[1px] bg-obsidian-950"></div>
          )}
        </div>
      </div>

      <div className="flex-1 min-w-0 relative z-10">
        <div className="flex items-center justify-between gap-2 mb-1">
          <span
            className={cn(
              "font-semibold text-sm truncate transition-colors",
              isSelected
                ? "text-white"
                : "text-text-primary group-hover/item:text-white",
            )}
          >
            {group.name}
          </span>
          {group.growth && (
            <span
              className={cn(
                "text-[10px] font-mono font-bold px-1.5 py-0.5 rounded shrink-0",
                group.growth.startsWith("+")
                  ? "text-accent-emerald bg-accent-emerald/10 border border-accent-emerald/20"
                  : "text-red-400 bg-red-400/10 border border-red-400/20",
              )}
            >
              {group.growth}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 text-[11px] font-medium text-text-tertiary mb-2">
          <span className="flex items-center gap-1">
            <Hash className="w-3 h-3" /> {group.channelsCount} kênh
          </span>
          <div className="w-[1px] h-3 bg-white/10"></div>
          <span className="flex items-center gap-1 text-text-secondary font-mono">
            {group.followers}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            {group.platforms.slice(0, 3).map((p) => {
              const Icon = platformIcons[p];
              return Icon ? (
                <Icon key={p} className="w-3 h-3 text-text-tertiary" />
              ) : null;
            })}
            {group.platforms.length > 3 && (
              <span className="text-[9px] font-mono text-text-tertiary bg-white/5 border border-white/5 px-1 py-0.5 rounded leading-none">
                +{group.platforms.length - 3}
              </span>
            )}
          </div>

          <div className="flex gap-1 opacity-0 group-hover/item:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onTogglePin?.(e);
              }}
              className={cn(
                "p-1 rounded text-text-tertiary hover:bg-white/10 hover:text-white transition-colors",
                group.isPinned && "text-accent-blue",
              )}
            >
              <Pin className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </button>
  );
};

interface GroupSwitcherProps {
  isSidebarCollapsed?: boolean;
}

export function GroupSwitcher({ isSidebarCollapsed }: GroupSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const { filters, setFilters, groups, updateGroup, addGroup, deleteGroup, addAlert, isManageGroupsModalOpen, setIsManageGroupsModalOpen } = useAppStore();
  const selectedGroupId = filters.group || "all";
  const popoverRef = useRef<HTMLDivElement>(null);
  
  const [newGroupName, setNewGroupName] = useState("");
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
  const [editingGroupName, setEditingGroupName] = useState("");

  const selectedGroup =
    groups.find((g) => g.id === selectedGroupId) || groups[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const filteredGroups = groups.filter((g) =>
    g.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );
  const pinnedGroups = filteredGroups.filter((g) => g.isPinned);
  const recentGroups = filteredGroups.filter((g) => !g.isPinned);

  const handleCreateGroup = () => {
    if (!newGroupName.trim()) return;
    addGroup({ name: newGroupName });
    setNewGroupName("");
    addAlert({ title: "Thành công", message: "Đã tạo nhóm kênh mới.", type: "success" });
  };

  const handleEditGroup = (id: string) => {
    if (!editingGroupName.trim()) return;
    updateGroup(id, { name: editingGroupName });
    setEditingGroupId(null);
    setEditingGroupName("");
    addAlert({ title: "Thành công", message: "Đã cập nhật tên nhóm.", type: "success" });
  };

  const handleDeleteGroup = (id: string, name: string) => {
    if (id === "all") {
      addAlert({ title: "Lỗi", message: "Không thể xóa Workspace mặc định.", type: "error" });
      return;
    }
    if (window.confirm(`Bạn có chắc chắn muốn xóa nhóm "${name}"?\nThao tác này không thể hoàn tác.`)) {
      deleteGroup(id);
      addAlert({ title: "Thành công", message: `Đã xóa nhóm ${name}.`, type: "success" });
    }
  };

  return (
    <div className="relative w-full" ref={popoverRef}>
      {/* Trigger Button */}
      <div
        className={cn(
          "flex items-center px-1 mb-8",
          isSidebarCollapsed ? "justify-center" : "gap-3",
        )}
      >
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-obsidian-800 to-obsidian-950 flex items-center justify-center border border-white/10 shadow-soft-inset shrink-0">
          <Activity className="w-5 h-5 text-accent-blue drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
        </div>
        {!isSidebarCollapsed && (
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="flex items-center justify-between flex-1 min-w-0 text-left group/trigger hover:bg-white/[0.02] p-1.5 -ml-1.5 rounded-lg border border-transparent hover:border-white/5 transition-all"
          >
            <div className="flex flex-col overflow-hidden px-1">
              <span className="font-semibold text-[15px] tracking-tight text-white leading-tight truncate group-hover/trigger:text-accent-blue transition-colors">
                {selectedGroup?.name || "Workspace"}
              </span>
              <span className="text-[10px] font-medium text-text-tertiary uppercase tracking-widest leading-none truncate mt-0.5">
                Workspace
              </span>
            </div>
            <div className="w-5 h-5 flex items-center justify-center rounded bg-transparent group-hover/trigger:bg-white/5 text-text-tertiary group-hover/trigger:text-text-primary transition-all shrink-0">
              <ChevronDown
                className={cn(
                  "w-3.5 h-3.5 transition-transform duration-300",
                  isOpen ? "rotate-180" : "rotate-0",
                )}
              />
            </div>
          </button>
        )}
      </div>

      {/* Popover */}
      <AnimatePresence>
        {isOpen && !isSidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="absolute top-12 left-0 w-[340px] bg-surface-elevated/95 backdrop-blur-3xl border border-border-default rounded-2xl shadow-elevated z-50 overflow-hidden flex flex-col max-h-[80vh]"
          >
            {/* Search Area */}
            <div className="p-3 border-b border-white/5 bg-surface-card/50">
              <div className="relative flex items-center bg-obsidian-950 border border-white/10 rounded-xl px-3 py-2 transition-colors focus-within:border-accent-blue/50 focus-within:ring-1 focus-within:ring-accent-blue/20">
                <Search className="w-4 h-4 text-text-tertiary shrink-0" />
                <input
                  type="text"
                  placeholder="Tìm nhóm kênh..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-transparent border-none outline-none text-sm text-text-primary px-2 w-full placeholder-text-tertiary font-medium"
                />
                <div className="font-mono text-[9px] bg-white/5 border border-white/5 px-1.5 py-0.5 rounded text-text-tertiary flex items-center gap-0.5 shrink-0">
                  <Command className="w-3 h-3" /> F
                </div>
              </div>
            </div>

            {/* List Body */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar p-2">
              {pinnedGroups.length > 0 && (
                <div className="mb-4">
                  <div className="px-2 mb-2 flex items-center gap-2">
                    <Pin className="w-3.5 h-3.5 text-text-tertiary" />
                    <span className="text-[10px] font-bold uppercase tracking-widest text-text-tertiary">
                      Ghim
                    </span>
                  </div>
                  <div className="space-y-1">
                    {pinnedGroups.map((group) => (
                      <GroupItem
                        key={group.id}
                        group={group}
                        isSelected={selectedGroupId === group.id}
                        onClick={() => {
                          setFilters({ group: group.id });
                          setIsOpen(false);
                        }}
                        onTogglePin={() => updateGroup(group.id, { isPinned: !group.isPinned })}
                      />
                    ))}
                  </div>
                </div>
              )}

              {recentGroups.length > 0 && (
                <div>
                  <div className="px-2 mb-2 flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-text-tertiary" />
                    <span className="text-[10px] font-bold uppercase tracking-widest text-text-tertiary">
                      Gần đây
                    </span>
                  </div>
                  <div className="space-y-1">
                    {recentGroups.map((group) => (
                      <GroupItem
                        key={group.id}
                        group={group}
                        isSelected={selectedGroupId === group.id}
                        onClick={() => {
                          setFilters({ group: group.id });
                          setIsOpen(false);
                        }}
                        onTogglePin={() => updateGroup(group.id, { isPinned: !group.isPinned })}
                      />
                    ))}
                  </div>
                </div>
              )}

              {filteredGroups.length === 0 && (
                <div className="py-8 text-center flex flex-col items-center">
                  <Search className="w-8 h-8 text-text-tertiary opacity-50 mb-3" />
                  <span className="text-sm font-medium text-text-secondary">
                    Không tìm thấy nhóm kênh
                  </span>
                  <span className="text-xs text-text-tertiary mt-1">
                    Sử dụng từ khóa khác để tìm kiếm
                  </span>
                </div>
              )}
            </div>

            {/* Footer Action */}
            <div className="p-3 border-t border-white/5 bg-surface-card/80 flex flex-col gap-2">
              <button 
                 onClick={() => {
                   setIsOpen(false);
                   setIsManageGroupsModalOpen(true);
                 }}
                 className="w-full flex items-center justify-center gap-2 py-2 mb-1 rounded-xl hover:bg-white/10 text-sm font-medium text-text-secondary hover:text-white transition-colors"
              >
                Quản Lý & Thuộc Tính Nhóm
              </button>
              <button 
                 onClick={() => {
                    setIsOpen(false);
                    setIsManageGroupsModalOpen(true);
                 }}
                 className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-dashed border-accent-blue/30 text-accent-blue hover:border-accent-blue/80 hover:bg-accent-blue/10 text-sm font-semibold transition-colors group"
              >
                <Plus className="w-4 h-4" />
                Tạo Nhóm Mới
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Manage Groups Modal */}
      {typeof document !== 'undefined' && createPortal(
        <AnimatePresence>
          {isManageGroupsModalOpen && (
             <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-obsidian-950/80 backdrop-blur-sm p-4">
               <motion.div 
                 initial={{ opacity: 0, scale: 0.95 }}
                 animate={{ opacity: 1, scale: 1 }}
                 exit={{ opacity: 0, scale: 0.95 }}
                 className="bg-obsidian-900 border border-white/10 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
               >
                <div className="p-5 border-b border-white/5 flex items-center justify-between bg-obsidian-950/50">
                  <div>
                    <h2 className="text-xl font-bold text-white mb-1">Quản Lý Nhóm Kênh</h2>
                    <p className="text-sm text-text-secondary">Tạo, chỉnh sửa hoặc xóa các nhóm kênh trong Workspace.</p>
                  </div>
                  <button onClick={() => setIsManageGroupsModalOpen(false)} className="p-2 text-text-tertiary hover:text-white bg-white/5 rounded-xl hover:bg-white/10 transition-colors">
                    <X className="w-5 h-5"/>
                  </button>
                </div>
                
                <div className="p-5 border-b border-white/5 bg-obsidian-800/30">
                  <div className="flex gap-3 items-end">
                    <div className="flex-1">
                      <label className="block text-xs font-semibold text-text-tertiary uppercase tracking-widest mb-2">Tên Nhóm Mới</label>
                      <input 
                        type="text" 
                        value={newGroupName}
                        onChange={(e) => setNewGroupName(e.target.value)}
                        placeholder="Nhập tên nhóm kênh..." 
                        onKeyDown={(e) => e.key === 'Enter' && handleCreateGroup()}
                        className="w-full bg-obsidian-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-blue transition-colors text-white"
                      />
                    </div>
                    <button 
                       onClick={handleCreateGroup}
                       disabled={!newGroupName.trim()}
                       className="px-6 py-2.5 bg-accent-blue text-white rounded-xl text-sm font-bold shadow-glow-blue hover:bg-blue-600 transition-all disabled:opacity-50 flex items-center gap-2 h-[42px]"
                    >
                      <Plus className="w-4 h-4"/> Thêm
                    </button>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
                  <div className="space-y-2">
                    {groups.map(group => (
                       <div key={group.id} className="flex items-center justify-between p-4 rounded-xl border border-white/5 bg-obsidian-950/30 hover:bg-obsidian-950/60 transition-colors">
                         <div className="flex flex-col gap-1 flex-1 mr-4">
                           {editingGroupId === group.id ? (
                             <input 
                               type="text" 
                               value={editingGroupName}
                               onChange={(e) => setEditingGroupName(e.target.value)}
                               onKeyDown={(e) => e.key === 'Enter' && handleEditGroup(group.id)}
                               className="w-full bg-obsidian-950 border border-accent-blue/50 rounded-lg px-3 py-1.5 text-sm focus:outline-none text-white"
                               autoFocus
                             />
                           ) : (
                             <div className="font-bold text-white text-sm flex items-center gap-2">
                               {group.id === 'all' && <Pin className="w-3.5 h-3.5 text-accent-gold" />}
                               {group.name}
                             </div>
                           )}
                           <div className="text-xs text-text-tertiary">
                             {group.channelsCount} kênh kết nối
                           </div>
                         </div>
                         <div className="flex items-center gap-2">
                           {editingGroupId === group.id ? (
                             <>
                               <button onClick={() => handleEditGroup(group.id)} className="px-3 py-1.5 bg-accent-blue text-white rounded-lg text-xs font-semibold hover:bg-blue-600 transition-colors">
                                 Lưu
                               </button>
                               <button onClick={() => setEditingGroupId(null)} className="px-3 py-1.5 bg-white/5 text-text-secondary rounded-lg text-xs font-semibold hover:bg-white/10 hover:text-white transition-colors">
                                 Hủy
                               </button>
                             </>
                           ) : (
                             <>
                               <button 
                                 onClick={() => {
                                   setEditingGroupId(group.id);
                                   setEditingGroupName(group.name);
                                 }}
                                 className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                               >
                                 <Edit2 className="w-4 h-4" />
                               </button>
                               {group.id !== 'all' && (
                                 <>
                                   <button onClick={() => updateGroup(group.id, { isPinned: !group.isPinned })} className={cn("p-2 rounded-lg transition-colors", group.isPinned ? "text-accent-gold bg-accent-gold/10 hover:bg-white/10" : "text-text-tertiary hover:text-white hover:bg-white/10")} title={group.isPinned ? "Bỏ yêu thích" : "Thêm vào yêu thích"}><Pin className="w-4 h-4" /></button>
                                 <button onClick={() => handleDeleteGroup(group.id, group.name)} className="p-2 text-text-tertiary hover:text-danger hover:bg-danger/10 rounded-lg transition-colors">
                                   <Trash2 className="w-4 h-4" />
                                 </button>
                                 </>
                               )}
                             </>
                           )}
                         </div>
                       </div>
                    ))}
                  </div>
                </div>
             </motion.div>
           </div>
        )}
        </AnimatePresence>
      , document.body)}
    </div>
  );
}
