export function uniqueSuffix(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  const ts =
    now.getUTCFullYear().toString() +
    pad(now.getUTCMonth() + 1) +
    pad(now.getUTCDate()) +
    pad(now.getUTCHours()) +
    pad(now.getUTCMinutes());
  const rand = Math.random().toString(16).slice(2, 8);
  return `${ts}-${rand}`;
}

export function uniqueSlug(prefix: string): string {
  return `${prefix}-${uniqueSuffix()}`.toLowerCase();
}

export function uniqueTitle(prefix: string): string {
  return `${prefix} ${uniqueSuffix()}`;
}
