import type { User } from "@/types";

export type MentionCandidate = {
  id: number | "everyone";
  display_name: string;
};

export function findMentionTrigger(
  text: string,
  cursor: number
): { start: number; query: string } | null {
  const before = text.slice(0, cursor);
  const at = before.lastIndexOf("@");
  if (at < 0) return null;
  if (at > 0 && !/\s/.test(before[at - 1])) return null;
  const query = before.slice(at + 1);
  if (query.includes(" ") || query.includes("\n")) return null;
  return { start: at, query };
}

export function getMentionCandidates(
  participants: User[],
  currentUserId: number,
  query: string
): MentionCandidate[] {
  const q = query.trim().toLowerCase();
  const people = participants
    .filter((p) => p.id !== currentUserId)
    .filter((p) => {
      if (!q) return true;
      const name = (p.display_name || "").toLowerCase();
      return name.includes(q) || p.phone_number.includes(q);
    })
    .map((p) => ({
      id: p.id,
      display_name: p.display_name || p.phone_number,
    }));

  const showEveryone = !q || "everyone".startsWith(q) || "all".startsWith(q);
  if (showEveryone) {
    return [{ id: "everyone", display_name: "everyone" }, ...people];
  }
  return people;
}
