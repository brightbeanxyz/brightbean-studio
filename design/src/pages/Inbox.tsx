import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Facebook, Youtube, MessageCircle, MessageSquare, Filter, Search, MoreVertical, Heart, Reply, ListFilter } from 'lucide-react';
import { cn } from '@/lib/utils';
import { EmptyState } from '@/components/ui/EmptyState';
import { Inbox as InboxIcon } from 'lucide-react';
import { useAppStore } from '@/store/AppContext';

const PLATFORMS = [
  { id: 'all', name: 'Tất cả', icon: null },
  { id: 'facebook', name: 'Facebook', icon: Facebook },
  { id: 'youtube', name: 'YouTube', icon: Youtube },
  { id: 'tiktok', name: 'TikTok', icon: MessageCircle },
];

export default function Inbox() {
  const { inboxMessages, replyToInboxMessage, updateInboxMessage } = useAppStore();
  const [activePlatform, setActivePlatform] = useState('all');
  const [activeType, setActiveType] = useState<'all' | 'inbox' | 'comment'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [replyBody, setReplyBody] = useState('');

  const safeMessages = Array.isArray(inboxMessages) ? inboxMessages : [];

  const filteredMessages = safeMessages.filter((msg) => {
    if (activePlatform !== 'all' && msg.platform !== activePlatform) return false;
    if (activeType !== 'all' && msg.type !== activeType) return false;
    const q = searchQuery.toLowerCase();
    if (q && !String(msg.content || '').toLowerCase().includes(q) && !String(msg.authorName || '').toLowerCase().includes(q)) return false;
    return true;
  });

  const selectedMessage = safeMessages.find((m) => m.id === selectedMessageId);

  const getPlatformIcon = (platformId: string) => {
    switch (platformId) {
      case 'facebook': return <Facebook className="w-4 h-4 text-[#1877F2]" />;
      case 'youtube': return <Youtube className="w-4 h-4 text-[#FF0000]" />;
      case 'tiktok': return <MessageCircle className="w-4 h-4 text-white" />;
      default: return null;
    }
  };

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col pt-4">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-accent-gold to-yellow-500 mb-1 flex items-center gap-2">Hộp Thư</h1>
          <p className="text-text-secondary text-sm">Quản lý và phản hồi tương tác từ mọi kênh</p>
        </div>
        <div className="relative flex-1 md:w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <input
            type="text"
            placeholder="Tìm kiếm tin nhắn..."
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-obsidian-800 border border-white/10 rounded-xl text-sm focus:outline-none focus:border-accent-gold/50 transition-colors"
          />
        </div>
      </div>

      <Card className="flex-1 overflow-hidden flex bg-obsidian-900/50">
        <div className="w-64 border-r border-white/5 flex flex-col">
          <div className="p-4 border-b border-white/5">
            <div className="text-xs font-semibold text-text-tertiary uppercase tracking-widest mb-3">Nền Tảng</div>
            <div className="space-y-1">
              {PLATFORMS.map((platform) => {
                const Icon = platform.icon;
                return (
                  <button key={platform.id} onClick={() => setActivePlatform(platform.id)} className={cn("w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors", activePlatform === platform.id ? "bg-white/10 text-white font-medium" : "text-text-secondary hover:bg-white/5 hover:text-text-primary")}>
                    {Icon ? <Icon className="w-4 h-4" /> : <div className="w-4 h-4 flex items-center justify-center shrink-0">·</div>}
                    {platform.name}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="p-4">
            <div className="text-xs font-semibold text-text-tertiary uppercase tracking-widest mb-3">Loại Tương Tác</div>
            {[
              ['all', 'Tất cả', ListFilter],
              ['inbox', 'Tin nhắn (Inbox)', MessageSquare],
              ['comment', 'Bình luận', MessageCircle],
            ].map(([id, label, Icon]: any) => (
              <button key={id} onClick={() => setActiveType(id)} className={cn("w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors", activeType === id ? "bg-white/10 text-white font-medium" : "text-text-secondary hover:bg-white/5 hover:text-text-primary")}>
                <Icon className="w-4 h-4" /> {label}
              </button>
            ))}
          </div>
        </div>

        <div className="w-80 border-r border-white/5 flex flex-col bg-obsidian-800/30">
          <div className="p-3 border-b border-white/5 flex items-center justify-between">
            <span className="text-sm font-medium">{filteredMessages.length} Hội thoại</span>
            <Filter className="w-4 h-4 text-text-tertiary" />
          </div>
          <div className="flex-1 overflow-y-auto">
            {filteredMessages.length === 0 ? (
              <div className="p-6 text-center text-text-tertiary text-sm">Không tìm thấy hội thoại nào</div>
            ) : (
              <div className="divide-y divide-white/5">
                {filteredMessages.map((msg) => (
                  <button
                    key={msg.id}
                    onClick={() => {
                      setSelectedMessageId(msg.id);
                      if (!msg.isRead) updateInboxMessage(msg.id, { status: 'open' });
                    }}
                    className={cn("w-full text-left p-4 hover:bg-white/[0.02] transition-colors relative", selectedMessageId === msg.id ? "bg-white/5" : "", !msg.isRead ? "bg-accent-blue/5" : "")}
                  >
                    {!msg.isRead && <div className="absolute left-0 top-0 bottom-0 w-1 bg-accent-blue rounded-r" />}
                    <div className="flex justify-between items-start mb-1">
                      <div className="flex items-center gap-2">
                        <img src={msg.authorAvatar} alt="avatar" className="w-6 h-6 rounded-full bg-obsidian-900 border border-white/10" />
                        <span className={cn("text-xs font-medium truncate max-w-[120px]", !msg.isRead ? "text-white" : "text-text-secondary")}>{msg.authorName}</span>
                      </div>
                      <span className="text-[10px] text-text-tertiary whitespace-nowrap">{msg.timestamp}</span>
                    </div>
                    <div className="text-xs text-text-tertiary mb-1 flex items-center gap-1.5 line-clamp-1">{getPlatformIcon(msg.platform)} {msg.channel}</div>
                    <p className={cn("text-sm line-clamp-2", !msg.isRead ? "text-text-primary font-medium" : "text-text-secondary")}>{msg.content}</p>
                    {msg.postTitle && <div className="mt-2 text-[10px] text-text-tertiary bg-obsidian-950 px-2 py-1 rounded inline-block truncate max-w-full border border-white/5">↳ {msg.postTitle}</div>}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col bg-obsidian-800/10 relative">
          {selectedMessage ? (
            <>
              <div className="p-4 border-b border-white/5 flex items-center justify-between bg-obsidian-800/20 backdrop-blur-sm relative z-10">
                <div className="flex items-center gap-3">
                  <img src={selectedMessage.authorAvatar} alt="avatar" className="w-10 h-10 rounded-full bg-obsidian-900 border border-white/10" />
                  <div>
                    <h3 className="font-medium text-white flex items-center gap-2">
                      {selectedMessage.authorName}
                      <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-white/5 text-text-secondary border border-white/10">{selectedMessage.type === 'inbox' ? 'Tin nhắn' : 'Bình luận'}</span>
                    </h3>
                    <div className="text-xs text-text-tertiary flex items-center gap-2 mt-0.5">{getPlatformIcon(selectedMessage.platform)} {selectedMessage.channel}</div>
                  </div>
                </div>
                <MoreVertical className="w-4 h-4 text-text-tertiary" />
              </div>
              <div className="flex-1 overflow-y-auto p-6 space-y-5">
                {selectedMessage.postTitle && (
                  <div className="p-3 rounded-xl bg-white/5 border border-white/10 flex flex-col gap-1">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wider font-semibold">Bình luận trên bài viết:</span>
                    <span className="text-sm text-text-primary">{selectedMessage.postTitle}</span>
                  </div>
                )}
                <div className="flex gap-4">
                  <img src={selectedMessage.authorAvatar} alt="avatar" className="w-8 h-8 rounded-full bg-obsidian-900 border border-white/10 shrink-0" />
                  <div>
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="font-medium text-white text-sm">{selectedMessage.authorName}</span>
                      <span className="text-[10px] text-text-tertiary">{selectedMessage.timestamp}</span>
                    </div>
                    <div className="bg-obsidian-800/50 border border-white/5 p-3 rounded-tr-xl rounded-br-xl rounded-bl-xl text-sm text-text-secondary w-fit inline-block">{selectedMessage.content}</div>
                    {selectedMessage.type === 'comment' && (
                      <div className="flex items-center gap-3 mt-2 text-xs text-text-tertiary">
                        <button className="hover:text-accent-gold transition-colors font-medium flex items-center gap-1"><Heart className="w-3.5 h-3.5" /> Thích</button>
                        <button className="hover:text-accent-blue transition-colors font-medium flex items-center gap-1"><Reply className="w-3.5 h-3.5" /> Phản hồi</button>
                      </div>
                    )}
                  </div>
                </div>
                {selectedMessage.replies?.map((reply: any) => (
                  <div key={reply.id} className="ml-12 rounded-xl bg-accent-blue/10 border border-accent-blue/20 p-3 text-sm text-text-primary">
                    <div className="text-xs text-text-tertiary mb-1">{reply.author}</div>
                    {reply.body}
                  </div>
                ))}
              </div>
              <div className="p-4 border-t border-white/5 bg-obsidian-800/30">
                <div className="relative">
                  <textarea value={replyBody} onChange={(event) => setReplyBody(event.target.value)} placeholder={`Trả lời ${selectedMessage.authorName}...`} className="w-full bg-obsidian-950 border border-white/10 rounded-xl p-3 text-sm focus:outline-none focus:border-accent-gold/50 transition-colors resize-none min-h-[100px]" />
                  <div className="absolute right-3 bottom-3 flex gap-2">
                    <button onClick={() => { if (replyBody.trim()) { replyToInboxMessage(selectedMessage.id, replyBody); setReplyBody(''); } }} className="px-4 py-1.5 bg-gradient-to-r from-accent-gold to-yellow-600 text-obsidian-950 font-medium text-sm rounded-lg hover:shadow-[0_0_15px_rgba(228,197,128,0.4)] transition-all">Gửi</button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState icon={InboxIcon} title="Chọn một đoạn chat" description="Vui lòng chọn một tin nhắn hoặc bình luận từ danh sách để xem và phản hồi." />
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
