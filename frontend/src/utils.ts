export function formatBytes(value: number | null | undefined): string {
  if (value == null) {
    return "Unknown";
  }
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "Unknown";
  }
  return `${Math.max(0, Math.min(100, value)).toFixed(0)}%`;
}

export function titleCase(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }
  return value
    .split(/[_/-]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}
