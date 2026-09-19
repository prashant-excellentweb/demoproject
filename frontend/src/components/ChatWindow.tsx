import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Flag, MoreVertical, Paperclip, Phone, Search, Send, Video, X } from "lucide-react";
import { chatApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useWebSocket } from "@/context/WebSocketContext";
import type { Conversation, Message, MessageQuote, MessageSearchHit } from "@/types";
import Avatar from "./Avatar";
import EmojiPicker from "./EmojiPicker";
import ForwardPicker from "./ForwardPicker";
import GroupAvatar from "./GroupAvatar";
import GroupInfoPanel from "./GroupInfoPanel";
import MessageBubble from "./MessageBubble";
import { formatLastSeen, getDisplayName, getOtherParticipant, getQuotePreview, toMessageQuote } from "@/utils/format";
import { isGroupAdmin } from "@/utils/group";
import { reportUser } from "@/utils/report";

interface Props {
  conversation: Conversation;
  onRefreshList: () => void;
  onConversationUpdate: (conversation: Conversation) => void;
  focusMessageId?: number | null;
}

export default function ChatWindow({ conversation, onRefreshList, onConversationUpdate, focusMessageId = null }: Props) {
  const { user } = useAuth();
  const { joinConversation, leaveConversation, sendTyping, markRead, onMessage, onTyping, onMessageDeleted, onMessageUpdated } = useWebSocket();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [replyTo, setReplyTo] = useState<MessageQuote | null>(null);
  const [draftHydrated, setDraftHydrated] = useState(false);
  const [forwarding, setForwarding] = useState<Message | null>(null);
  const [typingUser, setTypingUser] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [showGroupInfo, setShowGroupInfo] = useState(false);
  const [headerMenuOpen, setHeaderMenuOpen] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchHits, setSearchHits] = useState<MessageSearchHit[]>([]);
  const [searchIndex, setSearchIndex] = useState(0);
  const [searching, setSearching] = useState(false);
  const [highlightId, setHighlightId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const headerMenuRef = useRef<HTMLDivElement>(null);
  const typingTimeout = useRef<ReturnType<typeof setTimeout>>();
  const skipDraftSave = useRef(true);

  const appendMessage = useCallback((msg: Message) => {
    setMessages((prev) => {
      if (prev.some((m) => m.id === msg.id)) return prev;
      return [...prev, msg];
    });
  }, []);

  const replaceMessage = useCallback((msg: Message) => {
    setMessages((prev) => prev.map((m) => (m.id === msg.id ? msg : m)));
  }, []);

  const handleDeleteMessage = useCallback(async (msg: Message, deleteFor: "me" | "everyone") => {
    const res = await chatApi.deleteMessage(conversation.id, msg.id, deleteFor);
    if (deleteFor === "me" || res.data?.hidden) {
      setMessages((prev) => prev.filter((m) => m.id !== msg.id));
    } else {
      replaceMessage({ ...msg, ...res.data, is_deleted: true } as Message);
    }
    onRefreshList();
  }, [conversation.id, replaceMessage, onRefreshList]);

  const handleReactToMessage = useCallback(async (msg: Message, emoji: string) => {
    const res = await chatApi.reactToMessage(conversation.id, msg.id, emoji);
    replaceMessage(res.data);
  }, [conversation.id, replaceMessage]);

  const handleEditMessage = useCallback(async (msg: Message, content: string) => {
    const res = await chatApi.editMessage(conversation.id, msg.id, content);
    replaceMessage(res.data);
    onRefreshList();
  }, [conversation.id, replaceMessage, onRefreshList]);

  const canDeleteForEveryone = useCallback((msg: Message) => {
    if (msg.is_deleted) return false;
    if (msg.sender.id === user!.id) return true;
    return isGroupAdmin(conversation, user!.id);
  }, [user, conversation]);

  const other = conversation.is_group
    ? null
    : getOtherParticipant(conversation, user!.id);

  const handleUnblock = useCallback(async () => {
    try {
      const res = await chatApi.blockConversation(conversation.id, "unblock");
      onConversationUpdate(res.data);
      onRefreshList();
    } catch (e) {
      console.error(e);
    }
  }, [conversation.id, onConversationUpdate, onRefreshList]);

  const handleReportUser = useCallback(async () => {
    if (!other || reporting) return;
    setHeaderMenuOpen(false);
    setReporting(true);
    try {
      await reportUser(other, conversation.id);
    } finally {
      setReporting(false);
    }
  }, [other, reporting, conversation.id]);

  const isBlocked = conversation.is_blocked === true;

  const chatName = conversation.is_group
    ? conversation.group_name
    : other
      ? getDisplayName(other)
      : "Chat";

  const loadMessages = useCallback(() => {
    chatApi.getMessages(conversation.id).then((res) => {
      setMessages(res.data);
      markRead(conversation.id);
    });
  }, [conversation.id, markRead]);

  const messagesRef = useRef<Message[]>([]);
  messagesRef.current = messages;

  const jumpToMessage = useCallback(async (messageId: number) => {
    setHighlightId(messageId);
    if (!messagesRef.current.some((m) => m.id === messageId)) {
      try {
        const res = await chatApi.getMessages(conversation.id, { around: messageId });
        setMessages(res.data);
        markRead(conversation.id);
      } catch (e) {
        console.error(e);
        return;
      }
    }
    window.setTimeout(() => {
      document.getElementById(`msg-${messageId}`)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }, 50);
  }, [conversation.id, markRead]);

  useEffect(() => {
    joinConversation(conversation.id);
    if (!focusMessageId) {
      loadMessages();
    }
    return () => leaveConversation();
  }, [conversation.id, joinConversation, leaveConversation, loadMessages]);

  useEffect(() => {
    if (!focusMessageId) return;
    jumpToMessage(focusMessageId);
  }, [focusMessageId, conversation.id, jumpToMessage]);

  useEffect(() => {
    setSearchOpen(false);
    setSearchQuery("");
    setSearchHits([]);
    setSearchIndex(0);
    setHighlightId(focusMessageId ?? null);
  }, [conversation.id]);

  useEffect(() => {
    if (!searchOpen) return;
    const q = searchQuery.trim();
    if (q.length < 2) {
      setSearchHits([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    const timer = window.setTimeout(() => {
      chatApi
        .searchMessages(conversation.id, q)
        .then((res) => {
          const hits = res.data.results || [];
          setSearchHits(hits);
          setSearchIndex(0);
          if (hits[0]) jumpToMessage(hits[0].id);
        })
        .catch(console.error)
        .finally(() => setSearching(false));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchQuery, searchOpen, conversation.id]);

  useEffect(() => {
    setDraftHydrated(false);
    setText("");
    setReplyTo(null);
    let cancelled = false;
    chatApi
      .getDraft(conversation.id)
      .then((res) => {
        if (cancelled) return;
        const draft = res.data;
        if (draft?.content) setText(draft.content);
        if (draft?.reply_to && !draft.reply_to.is_deleted) setReplyTo(draft.reply_to);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) {
          skipDraftSave.current = true;
          setDraftHydrated(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [conversation.id]);

  useEffect(() => {
    if (!draftHydrated || isBlocked) return;
    if (skipDraftSave.current) {
      skipDraftSave.current = false;
      return;
    }
    const handle = window.setTimeout(() => {
      chatApi
        .saveDraft(conversation.id, {
          content: text,
          reply_to_id: replyTo?.id ?? null,
        })
        .then(() => onRefreshList())
        .catch(() => {});
    }, 500);
    return () => window.clearTimeout(handle);
  }, [text, replyTo, draftHydrated, conversation.id, isBlocked]);

  const goToSearchIndex = useCallback((next: number) => {
    if (searchHits.length === 0) return;
    const wrapped = (next + searchHits.length) % searchHits.length;
    setSearchIndex(wrapped);
    jumpToMessage(searchHits[wrapped].id);
  }, [searchHits, jumpToMessage]);

  const handleReply = useCallback((msg: Message) => {
    setReplyTo(toMessageQuote(msg));
    textareaRef.current?.focus();
  }, []);

  const clearReply = useCallback(() => setReplyTo(null), []);

  useEffect(() => {
    if (!headerMenuOpen) return;
    const onDocClick = (e: MouseEvent) => {
      if (headerMenuRef.current && !headerMenuRef.current.contains(e.target as Node)) {
        setHeaderMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [headerMenuOpen]);

  useEffect(() => {
    const unsubMsg = onMessage((msg) => {
      if (msg.conversation === conversation.id) {
        if (msg.is_deleted) {
          replaceMessage(msg);
        } else {
          appendMessage(msg);
          markRead(conversation.id);
        }
        onRefreshList();
      }
    });
    const unsubDeleted = onMessageDeleted((msg) => {
      if (msg.conversation === conversation.id) {
        replaceMessage(msg);
        onRefreshList();
      }
    });
    const unsubUpdated = onMessageUpdated((msg) => {
      if (msg.conversation === conversation.id) {
        replaceMessage(msg);
      }
    });
    const unsubTyping = onTyping((data) => {
      if (data.is_typing) {
        setTypingUser(data.user_name);
        clearTimeout(typingTimeout.current);
        typingTimeout.current = setTimeout(() => setTypingUser(null), 3000);
      } else {
        setTypingUser(null);
      }
    });
    return () => { unsubMsg(); unsubDeleted(); unsubUpdated(); unsubTyping(); };
  }, [conversation.id, onMessage, onMessageDeleted, onMessageUpdated, onTyping, markRead, onRefreshList, appendMessage, replaceMessage]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const insertEmoji = (emoji: string) => {
    setText((prev) => prev + emoji);
    textareaRef.current?.focus();
  };

  const handleSend = async () => {
    if (!text.trim() || sending) return;
    setSending(true);
    setEmojiOpen(false);
    const form = new FormData();
    form.append("content", text.trim());
    form.append("message_type", "text");
    if (replyTo) form.append("reply_to_id", String(replyTo.id));
    try {
      const res = await chatApi.sendMessage(conversation.id, form);
      appendMessage(res.data);
      setText("");
      setReplyTo(null);
      onRefreshList();
    } catch (e) {
      console.error(e);
    } finally {
      setSending(false);
    }
  };

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSending(true);
    const form = new FormData();
    form.append("file", file);
    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    let type = "document";
    if (["jpg", "jpeg", "png", "gif", "webp"].includes(ext)) type = "image";
    else if (["mp4", "webm", "mov"].includes(ext)) type = "video";
    else if (ext === "pdf") type = "pdf";
    form.append("message_type", type);
    if (replyTo) form.append("reply_to_id", String(replyTo.id));
    try {
      const res = await chatApi.sendMessage(conversation.id, form);
      appendMessage(res.data);
      setReplyTo(null);
      onRefreshList();
    } catch (err) {
      console.error(err);
    } finally {
      setSending(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextChange = (val: string) => {
    setText(val);
    sendTyping(val.length > 0);
  };

  const statusText = other
    ? formatLastSeen(other.last_seen, other.is_online)
    : `${conversation.participants.length} participants`;

  return (
    <div className="chat-window">
      <div className="chat-header">
        {other ? (
          <Avatar user={other} size={40} />
        ) : (
          <GroupAvatar
            name={conversation.group_name}
            imageUrl={conversation.group_avatar_url}
            size={40}
          />
        )}
        <div
          className="chat-header-info"
          style={{ flex: 1, cursor: conversation.is_group ? "pointer" : "default" }}
          onClick={() => conversation.is_group && setShowGroupInfo(true)}
        >
          <h3>{chatName}</h3>
          {(isBlocked || statusText) && (
            <p className={other?.is_online && !isBlocked ? "online-dot" : ""}>
              {isBlocked ? "Blocked" : statusText}
            </p>
          )}
        </div>
        <button
          type="button"
          className={`icon-btn${searchOpen ? " active" : ""}`}
          title="Search in chat"
          onClick={() => setSearchOpen((o) => !o)}
        >
          <Search size={20} />
        </button>
        <button type="button" className="icon-btn"><Phone size={20} /></button>
        <button type="button" className="icon-btn"><Video size={20} /></button>
        <div className="chat-header-menu-wrap" ref={headerMenuRef}>
          <button
            type="button"
            className="icon-btn"
            onClick={() => {
              if (conversation.is_group) {
                setShowGroupInfo(true);
              } else {
                setHeaderMenuOpen((o) => !o);
              }
            }}
          >
            <MoreVertical size={20} />
          </button>
          {headerMenuOpen && other && (
            <div className="chat-header-menu">
              <button type="button" onClick={handleReportUser} disabled={reporting}>
                <Flag size={16} />
                Report user
              </button>
            </div>
          )}
        </div>
      </div>

      {searchOpen && (
        <div className="inchat-search-bar">
          <Search size={16} />
          <input
            autoFocus
            placeholder="Search in this chat"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.shiftKey) {
                e.preventDefault();
                goToSearchIndex(searchIndex + 1);
              } else if (e.key === "Enter") {
                e.preventDefault();
                goToSearchIndex(searchIndex - 1);
              } else if (e.key === "Escape") {
                setSearchOpen(false);
              }
            }}
          />
          <span className="inchat-search-count">
            {searching
              ? "…"
              : searchQuery.trim().length < 2
                ? "Type 2+ letters"
                : searchHits.length
                  ? `${searchIndex + 1} / ${searchHits.length}`
                  : "No matches"}
          </span>
          <button
            type="button"
            className="icon-btn"
            title="Older match"
            disabled={!searchHits.length}
            onClick={() => goToSearchIndex(searchIndex + 1)}
          >
            <ChevronUp size={18} />
          </button>
          <button
            type="button"
            className="icon-btn"
            title="Newer match"
            disabled={!searchHits.length}
            onClick={() => goToSearchIndex(searchIndex - 1)}
          >
            <ChevronDown size={18} />
          </button>
          <button type="button" className="icon-btn" title="Close search" onClick={() => setSearchOpen(false)}>
            <X size={18} />
          </button>
        </div>
      )}

      {forwarding && (
        <ForwardPicker
          sourceConversationId={conversation.id}
          message={forwarding}
          onClose={() => setForwarding(null)}
          onForwarded={onRefreshList}
        />
      )}

      {showGroupInfo && conversation.is_group && (
        <GroupInfoPanel
          conversation={conversation}
          currentUserId={user!.id}
          onClose={() => setShowGroupInfo(false)}
          onUpdated={onConversationUpdate}
          onRefreshList={onRefreshList}
        />
      )}

      {isBlocked && (
        <div className="blocked-banner">
          <span>You blocked this chat.</span>
          <button type="button" onClick={handleUnblock}>Unblock</button>
        </div>
      )}

      <div className="messages-area">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isSent={msg.sender.id === user!.id}
            showSenderName={conversation.is_group}
            canDeleteForEveryone={canDeleteForEveryone(msg)}
            onDelete={handleDeleteMessage}
            onReact={handleReactToMessage}
            onReply={handleReply}
            onForward={setForwarding}
            onEdit={isBlocked ? undefined : handleEditMessage}
            highlighted={highlightId === msg.id}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {typingUser && (
        <div className="typing-indicator">{typingUser} is typing...</div>
      )}

      {!isBlocked ? (
        <div className="composer">
          {replyTo && (
            <div className="reply-banner">
              <div className="reply-banner-body">
                <span className="reply-banner-name">Replying to {replyTo.sender_name}</span>
                <span className="reply-banner-text">
                  {replyTo.is_deleted ? "This message was deleted" : getQuotePreview(replyTo)}
                </span>
              </div>
              <button type="button" className="icon-btn" title="Cancel reply" onClick={clearReply}>
                <X size={18} />
              </button>
            </div>
          )}
          <div className="message-input-area">
            <EmojiPicker
              open={emojiOpen}
              onToggle={() => setEmojiOpen((o) => !o)}
              onClose={() => setEmojiOpen(false)}
              onSelect={insertEmoji}
            />
            <button type="button" className="attach-btn" onClick={() => fileInputRef.current?.click()}>
              <Paperclip size={22} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              hidden
              accept="image/*,video/*,.pdf,.doc,.docx,.txt,.xls,.xlsx"
              onChange={handleFile}
            />
            <div className="message-input-wrapper">
              <textarea
                ref={textareaRef}
                placeholder={replyTo ? "Type a reply" : "Type a message"}
                value={text}
                onChange={(e) => handleTextChange(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />
            </div>
            <button type="button" className="send-btn" onClick={handleSend} disabled={!text.trim() || sending}>
              <Send size={20} />
            </button>
          </div>
        </div>
      ) : (
        <div className="message-input-area blocked-input">
          <p>Unblock this chat to send messages.</p>
        </div>
      )}
    </div>
  );
}
