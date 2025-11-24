/**
 * Polyline decoding utility for Strava activities
 */

/**
 * Decodes an encoded polyline string into a series of coordinates
 * @param encoded The encoded polyline string from Strava
 * @returns Array of [latitude, longitude] coordinate pairs
 */
export function decodePolyline(encoded: string): [number, number][] {
    if (!encoded || encoded.length === 0) {
      return [];
    }
  
    // For mock testing data
    if (encoded === 'mock_polyline_data') {
      return [
        [51.5074, -0.1278], // London
        [48.8566, 2.3522],  // Paris
        [41.9028, 12.4964], // Rome
        [40.4168, -3.7038], // Madrid
        [52.5200, 13.4050]  // Berlin
      ];
    }
  
    const points: [number, number][] = [];
    let index = 0;
    const len = encoded.length;
    let lat = 0;
    let lng = 0;
  
    while (index < len) {
      let b;
      let shift = 0;
      let result = 0;
  
      do {
        b = encoded.charCodeAt(index++) - 63; // 63 is the ASCII value of '?'
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20); // Continue while the 6th bit is set (value >= 32)
  
      const dlat = ((result & 1) !== 0 ? ~(result >> 1) : (result >> 1));
      lat += dlat;
  
      shift = 0;
      result = 0;
  
      do {
        b = encoded.charCodeAt(index++) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
  
      const dlng = ((result & 1) !== 0 ? ~(result >> 1) : (result >> 1));
      lng += dlng;
  
      // Division by 1e5 to convert the integer values to actual coordinates
      // Strava (and Google) use 5 decimal places of precision
      points.push([lat / 1e5, lng / 1e5]);
    }
  
    return points;
  }