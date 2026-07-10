import { useCallback, useEffect, useRef, useState } from "react";
import { MoreVertical, Paperclip, Phone, Search, Send, Video } from "lucide-react";
import { chatApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useWebSocket } from "@/context/WebSocketContext";
import type { Conversation, Message } from "@/types";
import Avatar from "./Avatar";
import EmojiPicker from "./EmojiPicker";
import GroupAvatar from "./GroupAvatar";
import GroupInfoPanel from "./GroupInfoPanel";
import MessageBubble from "./MessageBubble";
import { formatLastSeen, getDisplayName, getOtherParticipant } from "@/utils/format";
import { isGroupAdmin } from "@/utils/group";

interface Props {
  conversation: Conversation;
  onRefreshList: () => void;
  onConversationUpdate: (conversation: Conversation) => void;
}

export default function ChatWindow({ conversation, onRefreshList, onConversationUpdate }: Props) {
  const { user } = useAuth();
  const { joinConversation, leaveConversation, sendTyping, markRead, onMessage, onTyping, onMessageDeleted, onMessageUpdated } = useWebSocket();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [typingUser, setTypingUser] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [showGroupInfo, setShowGroupInfo] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeout = useRef<ReturnType<typeof setTimeout>>();

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

  const canDeleteForEveryone = useCallback((msg: Message) => {
    if (msg.is_deleted) return false;
    if (msg.sender.id === user!.id) return true;
    return isGroupAdmin(conversation, user!.id);
  }, [user, conversation]);

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
    try {
      const res = await chatApi.sendMessage(conversation.id, form);
      appendMessage(res.data);
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
      appendMessage(res.data);
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
          <p className={other?.is_online ? "online-dot" : ""}>{statusText}</p>
        </div>
        <button type="button" className="icon-btn"><Search size={20} /></button>
        <button type="button" className="icon-btn"><Phone size={20} /></button>
        <button type="button" className="icon-btn"><Video size={20} /></button>
        <button
          type="button"
          className="icon-btn"
          onClick={() => conversation.is_group && setShowGroupInfo(true)}
        >
          <MoreVertical size={20} />
        </button>
      </div>

      {showGroupInfo && conversation.is_group && (
        <GroupInfoPanel
          conversation={conversation}
          currentUserId={user!.id}
          onClose={() => setShowGroupInfo(false)}
          onUpdated={onConversationUpdate}
          onRefreshList={onRefreshList}
        />
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
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {typingUser && (
        <div className="typing-indicator">{typingUser} is typing...</div>
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
            placeholder="Type a message"
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
  );
}
