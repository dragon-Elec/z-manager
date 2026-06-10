// Shared utility functions for Z-Manager frontend

/**
 * Format bytes to human readable string (e.g. 4.0 GiB)
 */
export function formatSize(size: number): string {
  let s = size;
  for (const unit of ['B', 'KiB', 'MiB', 'GiB', 'TiB']) {
    if (Math.abs(s) < 1024.0) {
      return `${s.toFixed(1)} ${unit}`;
    }
    s /= 1024.0;
  }
  return `${s.toFixed(1)} PiB`;
}

/**
 * Format bytes to clean size string (e.g. 2G)
 */
export function formatBytesToSizeString(bytes: number): string {
  if (bytes <= 0) return '1G';
  const gb = bytes / (1024 ** 3);
  if (gb >= 1) return `${Math.round(gb)}G`;
  const mb = bytes / (1024 ** 2);
  return `${Math.round(mb)}M`;
}
