import { useEffect, useState } from "react";
import type { Conversation, Status } from "@/types";
import ChatList from "@/components/ChatList";
import ChatWindow from "@/components/ChatWindow";
import CreateStatusModal from "@/components/CreateStatusModal";
import NewChatModal from "@/components/NewChatModal";
import ProfilePanel from "@/components/ProfilePanel";
import StatusViewer from "@/components/StatusViewer";
import { useWebSocket } from "@/context/WebSocketContext";
import { chatApi } from "@/api/client";

export default function MainApp() {
  const { onMessage } = useWebSocket();
  const [activeConv, setActiveConv] = useState<Conversation | null>(null);
  const [showProfile, setShowProfile] = useState(false);
  const [showNewChat, setShowNewChat] = useState(false);
  const [showCreateStatus, setShowCreateStatus] = useState(false);
  const [statusView, setStatusView] = useState<{ userId: number; statuses: Status[] } | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = () => setRefreshKey((k) => k + 1);

  // If a message arrives for a chat that is open, refresh that conversation object
  useEffect(() => {
    return onMessage((msg) => {
      if (activeConv && msg.conversation === activeConv.id) {
        chatApi.getConversations().then((res) => {
          const updated = res.data.find((c: Conversation) => c.id === activeConv.id);
          if (updated) setActiveConv(updated);
        });
      }
    });
  }, [activeConv, onMessage]);

  return (
    <div className={`app-container ${activeConv ? "chat-open" : ""}`}>
      <ChatList
        activeId={activeConv?.id ?? null}
        onSelect={setActiveConv}
        onNewChat={() => setShowNewChat(true)}
        onProfile={() => setShowProfile(true)}
        onCreateStatus={() => setShowCreateStatus(true)}
        onViewStatus={(userId, statuses) => setStatusView({ userId, statuses })}
        refreshKey={refreshKey}
      />

      {activeConv ? (
        <ChatWindow
          conversation={activeConv}
          onBack={() => setActiveConv(null)}
          onRefreshList={refresh}
        />
      ) : (
        <div className="chat-window-empty">
          <h2>ChatApp Web</h2>
          <p>
            Send and receive messages, share photos, videos, and documents.
            Create status updates and connect with friends — all from your browser.
          </p>
        </div>
      )}

      {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}
      {showNewChat && <NewChatModal onClose={() => setShowNewChat(false)} onChatCreated={refresh} />}
      {showCreateStatus && (
        <CreateStatusModal onClose={() => setShowCreateStatus(false)} onCreated={refresh} />
      )}
      {statusView && (
        <StatusViewer
          userId={statusView.userId}
          statuses={statusView.statuses}
          onClose={() => { setStatusView(null); refresh(); }}
        />
      )}
    </div>
  );
}
