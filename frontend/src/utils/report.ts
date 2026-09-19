import { authApi } from "@/api/client";
import type { User } from "@/types";
import { getDisplayName } from "@/utils/format";

export const REPORT_REASONS = [
  { value: "spam", label: "Spam" },
  { value: "harassment", label: "Harassment" },
  { value: "inappropriate", label: "Inappropriate content" },
  { value: "fake", label: "Fake account" },
  { value: "other", label: "Other" },
] as const;

export type ReportReason = (typeof REPORT_REASONS)[number]["value"];

/** Ask for a reason + optional details. Returns null when cancelled or invalid. */
export function promptReportInput(user: User): { reason: ReportReason; details: string } | null {
  const reasonLabels = REPORT_REASONS.map((r, i) => `${i + 1}. ${r.label}`).join("\n");
  const choice = window.prompt(
    `Report ${getDisplayName(user)}?\n\nEnter reason number:\n${reasonLabels}`,
    "1"
  );
  if (!choice) return null;
  const reason = REPORT_REASONS[Number(choice) - 1]?.value;
  if (!reason) {
    alert("Invalid reason.");
    return null;
  }
  const details = window.prompt("Optional details (leave blank to skip):") || "";
  return { reason, details };
}

/**
 * Prompt for a reason and submit the report.
 * Pass `conversationId` to link the report to a chat (1:1 or group).
 */
export async function reportUser(user: User, conversationId?: number): Promise<boolean> {
  const input = promptReportInput(user);
  if (!input) return false;
  try {
    await authApi.reportUser(user.id, { ...input, conversation_id: conversationId });
    alert("Report submitted. Thank you.");
    return true;
  } catch (e) {
    console.error(e);
    alert("Failed to submit report.");
    return false;
  }
}
