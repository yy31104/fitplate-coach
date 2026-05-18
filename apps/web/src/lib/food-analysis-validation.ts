import type { FoodAnalyzeMockRequest } from "./food-analysis-types";

export const maxFoodPhotoSizeBytes = 10 * 1024 * 1024;

export const acceptedFoodImageTypes = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
] as const;

export const acceptedFoodImageTypesLabel = "JPEG, PNG, WebP, and HEIC";

export type FileValidationResult =
  | { ok: true }
  | { ok: false; code: "invalid_file_type" | "file_too_large" | "empty_file"; message: string };

export function validateFoodPhotoFile(file: File): FileValidationResult {
  if (!acceptedFoodImageTypes.includes(file.type as (typeof acceptedFoodImageTypes)[number])) {
    return {
      ok: false,
      code: "invalid_file_type",
      message: `Only ${acceptedFoodImageTypesLabel} images are supported.`,
    };
  }

  if (file.size === 0) {
    return {
      ok: false,
      code: "empty_file",
      message: "The selected file appears to be empty.",
    };
  }

  if (file.size > maxFoodPhotoSizeBytes) {
    return {
      ok: false,
      code: "file_too_large",
      message: `Photo must be under 10 MB. This file is ${formatFileSize(file.size)}.`,
    };
  }

  return { ok: true };
}

export function foodPhotoMetadata(file: File): FoodAnalyzeMockRequest {
  return {
    filename: file.name,
    content_type: file.type,
    size_bytes: file.size,
    last_modified_ms: file.lastModified,
  };
}

export function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(sizeBytes / 1024))} KB`;
  }

  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}
