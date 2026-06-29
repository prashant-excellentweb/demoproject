import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, MoreVertical, Paperclip, Phone, Search, Send, Smile, Video } from "lucide-react";
import { chatApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useWebSocket } from "@/context/WebSocketContext";
import type { Conversation, Message } from "@/types";
import Avatar from "./Avatar";
import MessageBubble from "./MessageBubble";
import { formatLastSeen, getDisplayName, getOtherParticipant } from "@/utils/format";

interface Props {
  conversation: Conversation;
  onBack?: () => void;
  onRefreshList: () => void;
}

export default function ChatWindow({ conversation, onBack, onRefreshList }: Props) {
  const { user } = useAuth();
  const { joinConversation, leaveConversation, sendTyping, markRead, onMessage, onTyping } = useWebSocket();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [typingUser, setTypingUser] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingTimeout = useRef<ReturnType<typeof setTimeout>>();

  const other = conversation.is_group
    ? null
    : getOtherParticipant(conversation, user!.id);

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

  useEffect(() => {
    loadMessages();
    joinConversation(conversation.id);
    return () => leaveConversation();
  }, [conversation.id, joinConversation, leaveConversation, loadMessages]);

  useEffect(() => {
    const unsubMsg = onMessage((msg) => {
      if (msg.conversation === conversation.id) {
        setMessages((prev) => {
          if (prev.some((m) => m.id === msg.id)) return prev;
          return [...prev, msg];
        });
        markRead(conversation.id);
        onRefreshList();
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
    return () => { unsubMsg(); unsubTyping(); };
  }, [conversation.id, onMessage, onTyping, markRead, onRefreshList]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!text.trim() || sending) return;
    setSending(true);
    const form = new FormData();
    form.append("content", text.trim());
    form.append("message_type", "text");
    try {
      const res = await chatApi.sendMessage(conversation.id, form);
      setMessages((prev) => [...prev, res.data]);
      setText("");
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
    try {
      const res = await chatApi.sendMessage(conversation.id, form);
      setMessages((prev) => [...prev, res.data]);
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
        {onBack && (
          <button className="icon-btn" onClick={onBack}>
            <ArrowLeft size={22} />
          </button>
        )}
        {other ? <Avatar user={other} size={40} /> : <div className="avatar">G</div>}
        <div className="chat-header-info" style={{ flex: 1 }}>
          <h3>{chatName}</h3>
          <p className={other?.is_online ? "online-dot" : ""}>{statusText}</p>
        </div>
        <button className="icon-btn"><Search size={20} /></button>
        <button className="icon-btn"><Phone size={20} /></button>
        <button className="icon-btn"><Video size={20} /></button>
        <button className="icon-btn"><MoreVertical size={20} /></button>
      </div>

      <div className="messages-area">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isSent={msg.sender.id === user!.id}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {typingUser && (
        <div className="typing-indicator">{typingUser} is typing...</div>
      )}

      <div className="message-input-area">
        <button className="icon-btn"><Smile size={24} /></button>
        <button className="attach-btn" onClick={() => fileInputRef.current?.click()}>
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
            placeholder="Type a message"
            value={text}
            onChange={(e) => handleTextChange(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
        </div>
        <button className="send-btn" onClick={handleSend} disabled={!text.trim() || sending}>
          <Send size={20} />
        </button>
      </div>
    </div>
  );
}
