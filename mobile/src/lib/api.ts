import { File, UploadType } from 'expo-file-system';
import type { Condition, ShotType } from './data';

// Matches backend/models/schemas.py ShootingAnalysisResponse.
// Kept as a plain mirror, not re-exported from the backend — there's no
// shared type layer between Python and TS here.
export interface ShootingAnalysisResponse {
  success: boolean;
  shot_type: string | null;
  condition: string | null;
  kicking_foot: string | null;
  contact_frame: number | null;
  technique_score: number | null;
  measured: Record<string, unknown> | null;
  breakdown: Record<string, unknown> | null;
  power_grade: number | null;
  power_speed_kmh: number | null;
  processing_time: string | null;
  error: string | null;
}

// Set EXPO_PUBLIC_API_BASE_URL to your backend's LAN address for on-device
// testing — localhost on the device refers to the device itself, not your dev
// machine. Falls back to the emulator loopback (10.0.2.2 is the Android
// emulator's alias for the host); a physical device needs the real LAN IP.
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://10.0.2.2:8000';

export async function uploadShotForAnalysis(
  localFileUri: string,
  shotType: ShotType,
  condition: Condition,
): Promise<ShootingAnalysisResponse> {
  const file = new File(localFileUri);
  const result = await file.upload(`${API_BASE_URL}/api/v1/analyse/shooting`, {
    httpMethod: 'POST',
    uploadType: UploadType.MULTIPART,
    fieldName: 'file',
    mimeType: 'video/mp4',
    parameters: { shot_type: shotType, condition },
  });

  if (result.status < 200 || result.status >= 300) {
    throw new Error(`Upload failed (${result.status}): ${result.body}`);
  }

  return JSON.parse(result.body) as ShootingAnalysisResponse;
}
