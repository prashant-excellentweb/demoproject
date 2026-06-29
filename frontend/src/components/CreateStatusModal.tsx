import { useRef, useState } from "react";
import { X } from "lucide-react";
import { storiesApi } from "@/api/client";

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

const COLORS = ["#075E54", "#128C7E", "#25D366", "#34B7F1", "#EA0038", "#FF5722", "#9C27B0", "#607D8B"];

export default function CreateStatusModal({ onClose, onCreated }: Props) {
  const [type, setType] = useState<"text" | "image" | "video">("text");
  const [content, setContent] = useState("");
  const [color, setColor] = useState(COLORS[0]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    setLoading(true);
    const form = new FormData();
    form.append("status_type", type);
    if (type === "text") {
      form.append("content", content);
      form.append("background_color", color);
    } else if (file) {
      form.append("media", file);
    } else {
      setLoading(false);
      return;
    }
    try {
      await storiesApi.createStatus(form);
      onCreated();
      onClose();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3>Create Status</h3>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="create-status-form">
          <div className="status-type-btns">
            {(["text", "image", "video"] as const).map((t) => (
              <button
                key={t}
                className={`status-type-btn ${type === t ? "active" : ""}`}
                onClick={() => setType(t)}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {type === "text" && (
            <>
              <textarea
                placeholder="What's on your mind?"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={4}
                style={{ padding: 12, borderRadius: 8, border: "1px solid var(--wa-border)", fontSize: 15 }}
              />
              <div>
                <label style={{ fontSize: 13, color: "var(--wa-text-secondary)", marginBottom: 8, display: "block" }}>
                  Background Color
                </label>
                <div className="color-picker-row">
                  {COLORS.map((c) => (
                    <button
                      key={c}
                      className={`color-swatch ${color === c ? "active" : ""}`}
                      style={{ background: c }}
                      onClick={() => setColor(c)}
                    />
                  ))}
                </div>
              </div>
            </>
          )}

          {(type === "image" || type === "video") && (
            <div>
              <input
                ref={fileRef}
                type="file"
                accept={type === "image" ? "image/*" : "video/*"}
                hidden
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <button
                className="btn-primary"
                onClick={() => fileRef.current?.click()}
                style={{ background: "var(--wa-input-bg)", color: "var(--wa-text)" }}
              >
                {file ? file.name : `Choose ${type}`}
              </button>
            </div>
          )}

          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={loading || (type === "text" ? !content.trim() : !file)}
          >
            {loading ? "Posting..." : "Post Status"}
          </button>
        </div>
      </div>
    </div>
  );
}
