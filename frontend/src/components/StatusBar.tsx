import { useEffect, useState } from "react";
import { storiesApi } from "@/api/client";
import type { StatusFeed } from "@/types";
import Avatar from "./Avatar";
import { getDisplayName } from "@/utils/format";

interface Props {
  onViewStatus: (userId: number, statuses: StatusFeed["contacts"][0]["statuses"], startIndex?: number) => void;
  onCreateStatus: () => void;
}

export default function StatusBar({ onViewStatus, onCreateStatus }: Props) {
  const [feed, setFeed] = useState<StatusFeed | null>(null);

  useEffect(() => {
    storiesApi.getFeed().then((res) => setFeed(res.data)).catch(console.error);
  }, []);

  if (!feed) return null;

  return (
    <div className="status-bar">
      <div className="status-item add-status" onClick={onCreateStatus}>
        <div className="status-ring">
          <div className="status-ring-inner">
            <div className="status-avatar">+</div>
          </div>
        </div>
        <span className="status-name">Add status</span>
      </div>

      {feed.my_statuses.length > 0 && (
        <div
          className="status-item"
          onClick={() => onViewStatus(-1, feed.my_statuses)}
        >
          <div className="status-ring">
            <div className="status-ring-inner">
              <Avatar user={feed.my_statuses[0].user} size={48} className="status-avatar" />
            </div>
          </div>
          <span className="status-name">My status</span>
        </div>
      )}

      {feed.contacts.map((group) => (
        <div
          key={group.user.id}
          className="status-item"
          onClick={() => onViewStatus(group.user.id, group.statuses)}
        >
          <div className={`status-ring ${group.has_unviewed ? "" : "viewed"}`}>
            <div className="status-ring-inner">
              <Avatar user={group.user} size={48} className="status-avatar" />
            </div>
          </div>
          <span className="status-name">{getDisplayName(group.user)}</span>
        </div>
      ))}
    </div>
  );
}
