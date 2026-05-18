import {
  type FoodAnalysis,
  type FoodAnalyzeMockRequest,
  isFoodAnalysis,
} from "./food-analysis-types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class FoodAnalysisApiError extends Error {
  constructor(
    message: string,
    public readonly code:
      | "invalid_file_type"
      | "file_too_large"
      | "empty_file"
      | "analysis_failed"
      | "invalid_response",
  ) {
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

function toApiError(body: unknown): FoodAnalysisApiError {
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
      body.code === "analysis_failed"
    ) {
      return new FoodAnalysisApiError(body.message, body.code);
    }
  }

  return new FoodAnalysisApiError("Analysis unavailable. Please try again.", "analysis_failed");
}
