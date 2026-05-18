"use client";

import { type ChangeEvent, type FormEvent, useMemo, useState } from "react";
import Link from "next/link";

import { analyzeFoodMock, FoodAnalysisApiError } from "../../../lib/food-analysis-api";
import {
  buildCorrectedTotal,
  recomputeCalorieRange,
} from "../../../lib/food-analysis-correction";
import type { FoodAnalysis, FoodItem, UserCorrection } from "../../../lib/food-analysis-types";
import {
  acceptedFoodImageTypes,
  acceptedFoodImageTypesLabel,
  foodPhotoMetadata,
  formatFileSize,
  validateFoodPhotoFile,
} from "../../../lib/food-analysis-validation";
import { ImagePreview, usePreviewUrl } from "./_components/ImagePreview";
import { EmptyResult, LoadingResult, ResultView } from "./_components/ResultView";

const inputAccept = acceptedFoodImageTypes.join(",");

export default function NewFoodAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<FoodAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [inputKey, setInputKey] = useState(0);
  const [corrections, setCorrections] = useState<Record<string, UserCorrection>>({});
  const [editingItemId, setEditingItemId] = useState<string | null>(null);

  const previewUrl = usePreviewUrl(file);
  const assumptions = useMemo(() => collectAssumptions(analysis), [analysis]);
  const correctedTotal = useMemo(
    () => buildCorrectedTotal(analysis?.items ?? [], corrections),
    [analysis, corrections],
  );
  const hasAnyCorrection = Object.keys(corrections).length > 0;

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFile = event.target.files?.[0] ?? null;
    setAnalysis(null);
    setError(null);
    setPreviewFailed(false);
    setCorrections({});
    setEditingItemId(null);

    if (!selectedFile) {
      setFile(null);
      return;
    }

    const validation = validateFoodPhotoFile(selectedFile);
    if (!validation.ok) {
      setFile(null);
      setError(validation.message);
      event.currentTarget.value = "";
      return;
    }

    setFile(selectedFile);
  }

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!file || isLoading) {
      return;
    }

    const validation = validateFoodPhotoFile(file);
    if (!validation.ok) {
      setError(validation.message);
      return;
    }

    setIsLoading(true);
    setError(null);
    setCorrections({});
    setEditingItemId(null);

    try {
      const [result] = await Promise.all([
        analyzeFoodMock(foodPhotoMetadata(file)),
        delay(450),
      ]);
      setAnalysis(result);
    } catch (caughtError) {
      setAnalysis(null);
      setError(errorMessageFor(caughtError, file));
    } finally {
      setIsLoading(false);
    }
  }

  function handleReset() {
    setFile(null);
    setAnalysis(null);
    setError(null);
    setPreviewFailed(false);
    setCorrections({});
    setEditingItemId(null);
    setInputKey((current) => current + 1);
  }

  function handleStartEdit(itemId: string) {
    setEditingItemId(itemId);
  }

  function handleCommitCorrection(item: FoodItem, correctedGrams: number) {
    const correctedCalories = recomputeCalorieRange(
      correctedGrams,
      item.calorie_density_kcal_per_gram,
      item.confidence,
    );

    const correction: UserCorrection = {
      correction_id: crypto.randomUUID(),
      item_id: item.item_id,
      original_name: item.name,
      corrected_name: item.name,
      original_grams: item.portion.grams_estimate,
      corrected_grams: correctedGrams,
      original_calories: item.calories,
      corrected_calories: correctedCalories,
      correction_timestamp: new Date().toISOString(),
      correction_source: "user",
    };

    setCorrections((current) => ({
      ...current,
      [item.item_id]: correction,
    }));
    setEditingItemId(null);
  }

  function handleCancelEdit() {
    setEditingItemId(null);
  }

  function handleUndoCorrection(itemId: string) {
    setCorrections((current) => {
      const next = { ...current };
      delete next[itemId];
      return next;
    });
    setEditingItemId((current) => (current === itemId ? null : current));
  }

  return (
    <main className="min-h-screen bg-[#f7f4ef] px-5 py-6 text-stone-950 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-5xl space-y-8">
        <header className="space-y-3">
          <Link className="text-sm font-medium text-emerald-800" href="/">
            FitPlate Coach
          </Link>
          <div className="max-w-3xl space-y-3">
            <p className="text-sm font-semibold tracking-[0.18em] text-stone-600 uppercase">
              Food photo mock analysis
            </p>
            <h1 className="text-3xl font-semibold sm:text-4xl">
              Select a food photo to estimate calories.
            </h1>
            <p className="text-base leading-7 text-stone-700">
              This milestone sends file metadata only. Image bytes are not uploaded or stored.
            </p>
          </div>
        </header>

        <form className="grid gap-6 lg:grid-cols-[22rem_1fr]" onSubmit={handleAnalyze}>
          <section className="space-y-4 rounded-lg border border-stone-300 bg-white p-5 shadow-sm">
            <div className="space-y-2">
              <label
                className="flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-stone-400 bg-stone-50 px-4 py-8 text-center transition hover:bg-stone-100"
                htmlFor="food-photo"
              >
                <span className="text-base font-semibold text-stone-950">
                  Choose a photo
                </span>
                <span className="mt-2 text-sm leading-6 text-stone-600">
                  {acceptedFoodImageTypesLabel}. Maximum 10 MB.
                </span>
              </label>
              <input
                key={inputKey}
                id="food-photo"
                className="sr-only"
                type="file"
                accept={inputAccept}
                disabled={isLoading}
                onChange={handleFileChange}
              />
              {error ? (
                <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-stone-800">
                  {error}
                </p>
              ) : null}
            </div>

            {file ? (
              <div className="space-y-4">
                <ImagePreview
                  file={file}
                  previewFailed={previewFailed}
                  previewUrl={previewUrl}
                  onPreviewError={() => setPreviewFailed(true)}
                />
                <div className="space-y-1 text-sm text-stone-700">
                  <p className="font-medium text-stone-950">{file.name}</p>
                  <p>{formatFileSize(file.size)}</p>
                  <p>{file.type || "Image type unavailable"}</p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <button
                    className="rounded-md bg-emerald-800 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-stone-400"
                    disabled={isLoading}
                    type="submit"
                  >
                    {isLoading ? "Analyzing..." : "Analyze"}
                  </button>
                  <button
                    className="text-sm font-medium text-emerald-800 disabled:text-stone-400"
                    disabled={isLoading}
                    type="button"
                    onClick={handleReset}
                  >
                    Choose different photo
                  </button>
                </div>
              </div>
            ) : null}
          </section>

          <section className="min-h-96 rounded-lg border border-stone-300 bg-white p-5 shadow-sm">
            {isLoading ? <LoadingResult /> : null}
            {!isLoading && analysis ? (
              <ResultView
                analysis={analysis}
                assumptions={assumptions}
                correctedTotal={correctedTotal}
                corrections={corrections}
                editingItemId={editingItemId}
                hasAnyCorrection={hasAnyCorrection}
                previewFailed={previewFailed}
                previewUrl={previewUrl}
                file={file}
                onCancelEdit={handleCancelEdit}
                onCommitCorrection={handleCommitCorrection}
                onStartEdit={handleStartEdit}
                onUndoCorrection={handleUndoCorrection}
              />
            ) : null}
            {!isLoading && !analysis ? <EmptyResult /> : null}
          </section>
        </form>
      </section>
    </main>
  );
}

function collectAssumptions(analysis: FoodAnalysis | null): string[] {
  if (!analysis) {
    return [];
  }

  return Array.from(
    new Set([
      ...analysis.uncertainty_notes,
      ...analysis.items.flatMap((item) => item.portion.assumptions),
    ]),
  );
}

function errorMessageFor(error: unknown, file: File): string {
  if (error instanceof FoodAnalysisApiError) {
    if (error.code === "file_too_large") {
      return `Photo must be under 10 MB. This file is ${formatFileSize(file.size)}.`;
    }

    if (error.code === "invalid_file_type") {
      return `Only ${acceptedFoodImageTypesLabel} images are supported.`;
    }

    if (error.code === "empty_file") {
      return "The selected file appears to be empty.";
    }
  }

  return "Analysis unavailable. Please try again.";
}

function delay(milliseconds: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}
