function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

export function Timestamp({ iso }: { iso: string }) {
  return (
    <time className="nx-tabular" dateTime={iso} title={iso} style={{ color: "var(--nx-ink-4)", fontSize: 12 }}>
      {formatTime(iso)}
    </time>
  );
}
