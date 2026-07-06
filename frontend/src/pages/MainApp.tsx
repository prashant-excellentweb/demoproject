import { useCallback, useEffect, useState } from "react";
import type { Conversation, Status } from "@/types";
import ChatList from "@/components/ChatList";
import ChatWindow from "@/components/ChatWindow";
import CreateStatusModal from "@/components/CreateStatusModal";
import NewChatModal from "@/components/NewChatModal";
import NewGroupModal from "@/components/NewGroupModal";
import ProfilePanel from "@/components/ProfilePanel";
import StatusViewer from "@/components/StatusViewer";
import { useWebSocket } from "@/context/WebSocketContext";
import { chatApi } from "@/api/client";

export default function MainApp() {
  const { onMessage } = useWebSocket();
  const [activeConv, setActiveConv] = useState<Conversation | null>(null);
  const [showProfile, setShowProfile] = useState(false);
  const [showNewChat, setShowNewChat] = useState(false);
  const [showNewGroup, setShowNewGroup] = useState(false);
  const [showCreateStatus, setShowCreateStatus] = useState(false);
  const [statusView, setStatusView] = useState<{ userId: number; statuses: Status[] } | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = () => setRefreshKey((k) => k + 1);

  const handleConversationsChange = useCallback((convs: Conversation[]) => {
    if (convs.length === 0) {
      setActiveConv(null);
      return;
    }
    setActiveConv((current) => {
      if (!current) return convs[0];
      const updated = convs.find((c) => c.id === current.id);
      return updated ?? convs[0];
    });
  }, []);

  const handleNewChatCreated = (conversation?: Conversation) => {
    refresh();
    if (conversation) {
      setActiveConv(conversation);
      return;
    }
    chatApi.getConversations().then((res) => {
      if (res.data.length > 0) {
        setActiveConv(res.data[0]);
      }
    });
  };

  const handleNewGroupCreated = (conversation: Conversation) => {
    refresh();
    setActiveConv(conversation);
  };

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
    <div className="app-container chat-open">
      <ChatList
        activeId={activeConv?.id ?? null}
        onSelect={setActiveConv}
        onNewChat={() => setShowNewChat(true)}
        onNewGroup={() => setShowNewGroup(true)}
        onProfile={() => setShowProfile(true)}
        onCreateStatus={() => setShowCreateStatus(true)}
        onViewStatus={(userId, statuses) => setStatusView({ userId, statuses })}
        refreshKey={refreshKey}
        onConversationsChange={handleConversationsChange}
      />

      {activeConv ? (
        <ChatWindow
          conversation={activeConv}
          onRefreshList={refresh}
          onConversationUpdate={setActiveConv}
        />
      ) : (
        <div className="chat-window-empty">
          <h2>No chats yet</h2>
          <p>Start a conversation or create a group with friends.</p>
          <div style={{ display: "flex", gap: 12, marginTop: 20, flexWrap: "wrap", justifyContent: "center" }}>
            <button type="button" className="btn-primary" style={{ width: "auto", padding: "12px 32px" }} onClick={() => setShowNewChat(true)}>
              New chat
            </button>
            <button type="button" className="btn-secondary" style={{ width: "auto", padding: "12px 32px" }} onClick={() => setShowNewGroup(true)}>
              New group
            </button>
          </div>
        </div>
      )}

      {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}
      {showNewChat && (
        <NewChatModal
          onClose={() => setShowNewChat(false)}
          onChatCreated={handleNewChatCreated}
        />
      )}
      {showNewGroup && (
        <NewGroupModal
          onClose={() => setShowNewGroup(false)}
          onGroupCreated={handleNewGroupCreated}
        />
      )}
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
