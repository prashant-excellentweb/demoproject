import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Trash2, X } from "lucide-react";
import { storiesApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import type { Status } from "@/types";
import Avatar from "./Avatar";
import { getDisplayName } from "@/utils/format";

interface Props {
  userId: number;
  statuses: Status[];
  startIndex?: number;
  onClose: () => void;
}

const STATUS_DURATION = 5000;

export default function StatusViewer({ userId, statuses, startIndex = 0, onClose }: Props) {
  const { user } = useAuth();
  const [currentIndex, setCurrentIndex] = useState(startIndex);
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const isOwn = userId === -1 || statuses[0]?.user.id === user?.id;

  const current = statuses[currentIndex];

  useEffect(() => {
    if (!current || isOwn) return;
    storiesApi.viewStatus(current.id).catch(console.error);
  }, [current, isOwn]);

  useEffect(() => {
    setProgress(0);
    const start = Date.now();
    timerRef.current = setInterval(() => {
      const elapsed = Date.now() - start;
      const pct = (elapsed / STATUS_DURATION) * 100;
      if (pct >= 100) {
        if (currentIndex < statuses.length - 1) {
          setCurrentIndex((i) => i + 1);
        } else {
          onClose();
        }
      } else {
        setProgress(pct);
      }
    }, 50);
    return () => clearInterval(timerRef.current);
  }, [currentIndex, statuses.length, onClose]);

  if (!current) return null;

  const bgColor = current.status_type === "text" ? current.background_color : "#000";

  const handleDelete = async () => {
    await storiesApi.deleteStatus(current.id);
    if (statuses.length === 1) {
      onClose();
    } else {
      setCurrentIndex(0);
    }
  };

  return (
    <div className="status-viewer" style={{ background: bgColor }}>
      <div className="status-progress-bars">
        {statuses.map((_, i) => (
          <div key={i} className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{
                width: i < currentIndex ? "100%" : i === currentIndex ? `${progress}%` : "0%",
              }}
            />
          </div>
        ))}
      </div>

      <div className="status-viewer-header">
        <button className="icon-btn" onClick={onClose} style={{ color: "white" }}>
          <X size={24} />
        </button>
        <Avatar user={current.user} size={36} />
        <div style={{ flex: 1, color: "white" }}>
          <div style={{ fontWeight: 500 }}>{getDisplayName(current.user)}</div>
          <div style={{ fontSize: 12, opacity: 0.8 }}>
            {new Date(current.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </div>
        </div>
        {isOwn && (
          <button className="icon-btn" onClick={handleDelete} style={{ color: "white" }}>
            <Trash2 size={20} />
          </button>
        )}
      </div>

      <div
        className="status-viewer-content"
        onClick={(e) => {
          const x = e.clientX;
          if (x < window.innerWidth / 2) {
            if (currentIndex > 0) setCurrentIndex((i) => i - 1);
          } else {
            if (currentIndex < statuses.length - 1) setCurrentIndex((i) => i + 1);
            else onClose();
          }
        }}
      >
        {current.status_type === "text" && (
          <p className="status-text-content">{current.content}</p>
        )}
        {current.status_type === "image" && (
          <div className="status-media-content">
            <img src={current.media_url || ""} alt="Status" />
          </div>
        )}
        {current.status_type === "video" && (
          <div className="status-media-content">
            <video src={current.media_url || ""} autoPlay muted />
          </div>
        )}
      </div>
    </div>
  );
}
