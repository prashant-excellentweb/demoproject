import type { User } from "@/types";
import { getInitials } from "@/utils/format";

interface AvatarProps {
  user: User;
  size?: number;
  className?: string;
}

export default function Avatar({ user, size = 50, className = "avatar" }: AvatarProps) {
  const content = user.avatar_url ? (
    <img
      src={user.avatar_url}
      alt={user.display_name || user.phone_number}
      className={className}
      style={{ width: size, height: size }}
    />
  ) : (
    <div className={className} style={{ width: size, height: size, fontSize: size * 0.36 }}>
      {getInitials(user)}
    </div>
  );

  if (!user.is_online) return content;

  return (
    <span className="avatar-wrap" style={{ width: size, height: size }}>
      {content}
      <span className="avatar-online-dot" aria-label="online" />
    </span>
  );
}
