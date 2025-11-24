/**
 * Format distance in various units
 */
export function formatDistance(meters: number, unit: "km" | "mi" = "km"): string {
  if (unit === "km") {
    const km = meters / 1000;
    return `${km.toFixed(1)} km`;
  } else {
    const miles = meters / 1609.34;
    return `${miles.toFixed(1)} mi`;
  }
}

/**
 * Format time duration in seconds to human-readable format
 */
export function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else {
    return `${minutes}m`;
  }
}

/**
 * Format elevation in meters
 */
export function formatElevation(meters: number): string {
  return `${Math.round(meters)} m`;
}