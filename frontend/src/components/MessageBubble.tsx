import { Check, CheckCheck, FileText, Paperclip, Send, Smile, X } from "lucide-react";
import type { Message } from "@/types";
import { formatFileSize, formatMessageTime, getDisplayName } from "@/utils/format";

interface Props {
  message: Message;
  isSent: boolean;
  showSenderName?: boolean;
}

export default function MessageBubble({ message, isSent, showSenderName = false }: Props) {
  const renderContent = () => {
    switch (message.message_type) {
      case "image":
        return (
          <div className="message-media">
            <img src={message.file_url || ""} alt={message.file_name} loading="lazy" />
            {message.content && <p className="message-text">{message.content}</p>}
          </div>
        );
      case "video":
        return (
          <div className="message-media">
            <video src={message.file_url || ""} controls />
            {message.content && <p className="message-text">{message.content}</p>}
          </div>
        );
      case "pdf":
      case "document":
        return (
          <div className="message-file">
            <FileText size={32} color="#128c7e" />
            <div>
              <a href={message.file_url || "#"} target="_blank" rel="noopener noreferrer">
                {message.file_name || "Document"}
              </a>
              <div style={{ fontSize: 11, color: "var(--wa-text-secondary)" }}>
                {formatFileSize(message.file_size)}
              </div>
            </div>
          </div>
        );
      case "audio":
        return (
          <audio src={message.file_url || ""} controls style={{ width: "100%", minWidth: 200 }} />
        );
      default:
        return <p className="message-text">{message.content}</p>;
    }
  };

  return (
    <div className={`message-row ${isSent ? "sent" : "received"}`}>
      <div className="message-bubble">
        {showSenderName && !isSent && (
          <div className="message-sender-name">{getDisplayName(message.sender)}</div>
        )}
        {renderContent()}
        <div className="message-meta">
          <span className="message-time">{formatMessageTime(message.created_at)}</span>
          {isSent && (
            message.is_read ? <CheckCheck size={14} color="#53bdeb" /> : <Check size={14} color="#8696a0" />
          )}
        </div>
      </div>
    </div>
  );
}
