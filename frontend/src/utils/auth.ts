import type { User } from "@/types";

export function needsProfileSetup(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.profile_setup_complete === false) return true;
  if (user.profile_setup_complete === true) return false;
  return !user.display_name?.trim();
}
