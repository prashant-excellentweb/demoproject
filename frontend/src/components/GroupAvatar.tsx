interface Props {
  name: string;
  imageUrl?: string | null;
  size?: number;
}

export default function GroupAvatar({ name, imageUrl, size = 50 }: Props) {
  if (imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={name}
        className="avatar"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <div className="avatar group-avatar" style={{ width: size, height: size, fontSize: size * 0.36 }}>
      {name.trim().slice(0, 1).toUpperCase() || "G"}
    </div>
  );
}
