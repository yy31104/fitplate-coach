"use client";

import { type ChangeEvent, type FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { analyzeFoodMock, FoodAnalysisApiError } from "../../../lib/food-analysis-api";
import type { FoodAnalysis, FoodItem, SafetyFlag } from "../../../lib/food-analysis-types";
import {
  acceptedFoodImageTypes,
  acceptedFoodImageTypesLabel,
  foodPhotoMetadata,
  formatFileSize,
  validateFoodPhotoFile,
} from "../../../lib/food-analysis-validation";

const inputAccept = acceptedFoodImageTypes.join(",");

export default function NewFoodAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<FoodAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [inputKey, setInputKey] = useState(0);

  const previewUrl = usePreviewUrl(file);
  const assumptions = useMemo(() => collectAssumptions(analysis), [analysis]);
  const headlineRange = analysis ? formatCalories(analysis.total_calories) : "";

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFile = event.target.files?.[0] ?? null;
    setAnalysis(null);
    setError(null);
    setPreviewFailed(false);

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
    setInputKey((current) => current + 1);
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
                headlineRange={headlineRange}
                previewFailed={previewFailed}
                previewUrl={previewUrl}
                file={file}
              />
            ) : null}
            {!isLoading && !analysis ? <EmptyResult /> : null}
          </section>
        </form>
      </section>
    </main>
  );
}

function ResultView({
  analysis,
  assumptions,
  headlineRange,
  previewFailed,
  previewUrl,
  file,
}: {
  analysis: FoodAnalysis;
  assumptions: string[];
  headlineRange: string;
  previewFailed: boolean;
  previewUrl: string | null;
  file: File | null;
}) {
  const hasItems = analysis.items.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-3">
          <span className="inline-flex rounded-full border border-stone-300 bg-stone-100 px-3 py-1 text-xs font-semibold text-stone-700">
            Mock analysis
          </span>
          <div>
            <h2 className="text-2xl font-semibold">
              {hasItems ? "Food photo estimate" : "No food detected"}
            </h2>
            <p className="mt-1 text-3xl font-semibold text-emerald-900">{headlineRange}</p>
          </div>
        </div>
        {file ? (
          <div className="w-24 shrink-0">
            <ImagePreview
              compact
              file={file}
              previewFailed={previewFailed}
              previewUrl={previewUrl}
            />
          </div>
        ) : null}
      </div>

      {!hasItems ? (
        <p className="rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-700">
          No food was detected in this photo. Try a closer or clearer shot.
        </p>
      ) : (
        <div className="space-y-3">
          {analysis.items.map((item) => (
            <FoodItemRow item={item} key={item.item_id} />
          ))}
        </div>
      )}

      <div className="border-t border-stone-200 pt-4">
        <p className="text-sm text-stone-600">Total estimate</p>
        <p className="text-xl font-semibold">{headlineRange}</p>
      </div>

      <div className="space-y-2 border-t border-stone-200 pt-4">
        <h3 className="font-semibold">Assumptions</h3>
        <ul className="space-y-1 text-sm leading-6 text-stone-700">
          {assumptions.map((assumption) => (
            <li key={assumption}>- {assumption}</li>
          ))}
        </ul>
      </div>

      {analysis.safety_flags.length > 0 ? (
        <div className="space-y-2 border-t border-stone-200 pt-4">
          <h3 className="font-semibold">Safety flags</h3>
          <div className="flex flex-wrap gap-2">
            {analysis.safety_flags.map((flag) => (
              <span
                className="rounded-full border border-stone-300 bg-stone-100 px-3 py-1 text-xs font-medium text-stone-700"
                key={flag}
              >
                {formatFlag(flag)}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <p className="border-t border-stone-200 pt-4 text-sm leading-6 text-stone-600">
        Calorie estimates are for reflection only. This is not medical nutrition advice.
      </p>
    </div>
  );
}

function FoodItemRow({ item }: { item: FoodItem }) {
  return (
    <div className="rounded-md border border-stone-200 bg-stone-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-stone-950">{item.name}</p>
          <p className="mt-1 text-sm text-stone-600">
            {item.portion.description} · {formatCalories(item.calories)}
          </p>
        </div>
        <span className="rounded-full border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-700">
          {item.confidence} confidence
        </span>
      </div>
    </div>
  );
}

function ImagePreview({
  compact = false,
  file,
  onPreviewError,
  previewFailed,
  previewUrl,
}: {
  compact?: boolean;
  file: File;
  onPreviewError?: () => void;
  previewFailed: boolean;
  previewUrl: string | null;
}) {
  const canPreview = previewUrl && !previewFailed;

  return (
    <div
      className={`flex items-center justify-center overflow-hidden rounded-md border border-stone-200 bg-stone-100 ${
        compact ? "aspect-square" : "aspect-video"
      }`}
    >
      {canPreview ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt={`Preview of ${file.name}`}
          className="h-full w-full object-cover"
          src={previewUrl}
          onError={onPreviewError}
        />
      ) : (
        <div className="px-4 text-center text-sm leading-6 text-stone-600">
          <p className="font-medium text-stone-800">Preview unavailable</p>
          <p>{file.name}</p>
        </div>
      )}
    </div>
  );
}

function LoadingResult() {
  return (
    <div className="animate-pulse space-y-5">
      <div className="h-7 w-32 rounded-full bg-stone-200" />
      <div className="space-y-3">
        <div className="h-8 w-56 rounded bg-stone-200" />
        <div className="h-10 w-44 rounded bg-stone-200" />
      </div>
      <div className="space-y-3">
        <div className="h-16 rounded-md bg-stone-200" />
        <div className="h-16 rounded-md bg-stone-200" />
        <div className="h-16 rounded-md bg-stone-200" />
      </div>
    </div>
  );
}

function EmptyResult() {
  return (
    <div className="flex min-h-80 items-center justify-center text-center">
      <p className="max-w-sm text-sm leading-6 text-stone-600">
        Select a food photo to see a structured mock analysis here.
      </p>
    </div>
  );
}

function usePreviewUrl(file: File | null): string | null {
  const previewUrl = useMemo(() => {
    if (!file || file.type === "image/heic" || file.type === "image/heif") {
      return null;
    }

    return URL.createObjectURL(file);
  }, [file]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  return previewUrl;
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

function formatCalories(range: FoodAnalysis["total_calories"]): string {
  return `${range.min}-${range.max} kcal`;
}

function formatFlag(flag: SafetyFlag): string {
  return flag.replaceAll("_", " ");
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
