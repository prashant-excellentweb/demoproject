import type { User } from "@/types";
import { getInitials } from "@/utils/format";

interface AvatarProps {
  user: User;
  size?: number;
  className?: string;
}

export default function Avatar({ user, size = 50, className = "avatar" }: AvatarProps) {
  if (user.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={user.display_name || user.phone_number}
        className={className}
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <div className={className} style={{ width: size, height: size, fontSize: size * 0.36 }}>
      {getInitials(user)}
    </div>
  );
}
