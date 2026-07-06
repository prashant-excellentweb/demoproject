import { useEffect, useRef } from "react";
import EmojiPickerLib, { Theme, type EmojiClickData } from "emoji-picker-react";
import { Smile } from "lucide-react";

interface Props {
  onSelect: (emoji: string) => void;
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
}

export default function EmojiPicker({ onSelect, open, onToggle, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, onClose]);

  const handleEmojiClick = (emojiData: EmojiClickData) => {
    onSelect(emojiData.emoji);
  };

  return (
    <div ref={ref} className="emoji-picker-wrap">
      <button type="button" className="icon-btn" title="Emoji" onClick={onToggle}>
        <Smile size={24} />
      </button>
      {open && (
        <div className="emoji-picker-popup">
          <EmojiPickerLib
            theme={Theme.LIGHT}
            onEmojiClick={handleEmojiClick}
            width={320}
            height={400}
            searchPlaceholder="Search emoji"
            previewConfig={{ showPreview: false }}
          />
        </div>
      )}
    </div>
  );
}
