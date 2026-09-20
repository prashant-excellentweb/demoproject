import type { ReactElement } from "react";
import type { Message } from "@/types";

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

interface Props {
  content: string;
  mentions?: Message["mentions"];
  mentionEveryone?: boolean;
}

export default function MentionText({ content, mentions = [], mentionEveryone = false }: Props) {
  const names = mentions
    .map((m) => m.display_name.trim())
    .filter(Boolean);
  const firstNames = names
    .map((name) => name.split(/\s+/)[0])
    .filter(Boolean);
  const specials = mentionEveryone ? ["everyone", "all"] : [];
  const tokens = Array.from(new Set([...names, ...firstNames, ...specials])).sort(
    (a, b) => b.length - a.length
  );

  if (!content || tokens.length === 0) {
    return <>{content}</>;
  }

  const pattern = new RegExp(`@(?:${tokens.map(escapeRegExp).join("|")})`, "gi");
  const parts: Array<string | ReactElement> = [];
  let last = 0;
  let key = 0;
  for (const match of content.matchAll(pattern)) {
    const start = match.index ?? 0;
    if (start > last) parts.push(content.slice(last, start));
    parts.push(
      <span key={`m-${key++}`} className="mention-token">
        {match[0]}
      </span>
    );
    last = start + match[0].length;
  }
  if (last < content.length) parts.push(content.slice(last));
  return <>{parts}</>;
}
