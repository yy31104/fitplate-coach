import {
  type FoodAnalysis,
  type FoodAnalyzeMockRequest,
  type FoodCorrectionMockRequest,
  type UserCorrection,
  isFoodAnalysis,
  isUserCorrection,
} from "./food-analysis-types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type FoodAnalysisApiErrorCode =
  | "invalid_file_type"
  | "file_too_large"
  | "empty_file"
  | "analysis_failed"
  | "correction_failed"
  | "invalid_response";

export class FoodAnalysisApiError extends Error {
  constructor(message: string, public readonly code: FoodAnalysisApiErrorCode) {
    super(message);
    this.name = "FoodAnalysisApiError";
  }
}

export async function analyzeFoodMock(
  metadata: FoodAnalyzeMockRequest,
): Promise<FoodAnalysis> {
  const response = await fetch(`${apiBaseUrl}/api/v0/food/analyze/mock`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(metadata),
  });

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw toApiError(body);
  }

  if (!isFoodAnalysis(body)) {
    throw new FoodAnalysisApiError("Analysis unavailable. Please try again.", "invalid_response");
  }

  return body;
}

export async function submitFoodAnalyzeUpload(file: File): Promise<FoodAnalysis> {
  const formData = new FormData();
  formData.append("image", file);

  const response = await fetch(`${apiBaseUrl}/api/v0/food/analyze`, {
    method: "POST",
    body: formData,
  });

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw toApiError(body);
  }

  if (!isFoodAnalysis(body)) {
    throw new FoodAnalysisApiError("Analysis unavailable. Please try again.", "invalid_response");
  }

  return body;
}

export async function submitFoodCorrectionMock(
  request: FoodCorrectionMockRequest,
): Promise<UserCorrection> {
  const response = await fetch(`${apiBaseUrl}/api/v0/food/corrections/mock`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw toApiError(body, "Correction failed. Please try again.", "correction_failed");
  }

  if (!isUserCorrection(body)) {
    throw new FoodAnalysisApiError("Correction failed. Please try again.", "invalid_response");
  }

  return body;
}

function toApiError(
  body: unknown,
  fallbackMessage = "Analysis unavailable. Please try again.",
  fallbackCode: FoodAnalysisApiErrorCode = "analysis_failed",
): FoodAnalysisApiError {
  if (
    typeof body === "object" &&
    body !== null &&
    "code" in body &&
    "message" in body &&
    typeof body.code === "string" &&
    typeof body.message === "string"
  ) {
    if (
      body.code === "invalid_file_type" ||
      body.code === "file_too_large" ||
      body.code === "empty_file" ||
      body.code === "analysis_failed" ||
      body.code === "correction_failed"
    ) {
      return new FoodAnalysisApiError(body.message, body.code);
    }
  }

  return new FoodAnalysisApiError(fallbackMessage, fallbackCode);
}
