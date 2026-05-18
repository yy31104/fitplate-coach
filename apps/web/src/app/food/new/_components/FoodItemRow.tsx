"use client";

import { useState } from "react";

import { formatCalories } from "../../../../lib/food-analysis-format";
import type { FoodItem, UserCorrection } from "../../../../lib/food-analysis-types";

export function FoodItemRow({
  applyError,
  correction,
  isEditing,
  isSubmitting,
  item,
  onCancel,
  onCommit,
  onStartEdit,
  onUndo,
}: {
  applyError: string | null;
  correction: UserCorrection | null;
  isEditing: boolean;
  isSubmitting: boolean;
  item: FoodItem;
  onCancel: () => void;
  onCommit: (correctedGrams: number) => Promise<void>;
  onStartEdit: () => void;
  onUndo: () => void;
}) {
  const effectiveGrams = correction?.corrected_grams ?? item.portion.grams_estimate;
  const effectiveCalories = correction?.corrected_calories ?? item.calories;
  const portionDescription = correction ? `~${effectiveGrams}g` : item.portion.description;
  const initialDraftGrams = String(effectiveGrams);
  const [draftGrams, setDraftGrams] = useState(initialDraftGrams);
  const [inputError, setInputError] = useState<string | null>(
    validateGramInput(initialDraftGrams).error,
  );

  function handleDraftChange(value: string) {
    setDraftGrams(value);
    setInputError(validateGramInput(value).error);
  }

  function handleApply() {
    if (isSubmitting) {
      return;
    }

    const validation = validateGramInput(draftGrams);
    setInputError(validation.error);

    if (!validation.correctedGrams) {
      return;
    }

    void onCommit(validation.correctedGrams);
  }

  if (isEditing) {
    return (
      <div className="rounded-md border border-stone-200 bg-stone-50 p-3">
        <div className="space-y-3">
          <p className="font-medium text-stone-950">{item.name}</p>
          <div className="flex flex-wrap items-end gap-3">
            <label
              className="min-w-36 flex-1 text-sm text-stone-700"
              htmlFor={`grams-${item.item_id}`}
            >
              <span className="font-medium text-stone-800">Portion in grams</span>
              <input
                id={`grams-${item.item_id}`}
                className="mt-1 w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-950"
                inputMode="decimal"
                type="text"
                value={draftGrams}
                onChange={(event) => handleDraftChange(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    handleApply();
                  }
                }}
              />
            </label>
            <button
              className="rounded-md bg-emerald-800 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-stone-400"
              disabled={Boolean(inputError) || isSubmitting}
              type="button"
              onClick={handleApply}
            >
              {isSubmitting ? "Applying..." : "Apply"}
            </button>
            <button
              className="px-2 py-2 text-sm font-medium text-emerald-800"
              type="button"
              onClick={onCancel}
            >
              Cancel
            </button>
          </div>
          {inputError ? <p className="text-sm text-stone-700">{inputError}</p> : null}
          {!inputError && applyError ? (
            <p className="text-sm text-red-700" role="alert">
              {applyError}
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-stone-200 bg-stone-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-stone-950">{item.name}</p>
            {correction ? (
              <span className="rounded-full border border-stone-300 bg-white px-2 py-0.5 text-xs font-medium text-stone-700">
                corrected
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-sm text-stone-600">
            {portionDescription} · {formatCalories(effectiveCalories)}
          </p>
          {correction ? (
            <p className="mt-1 text-xs text-stone-500">
              Original: {item.portion.grams_estimate}g
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <span className="rounded-full border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-700">
            {item.confidence} confidence
          </span>
          <button
            className="text-sm font-medium text-emerald-800"
            type="button"
            onClick={onStartEdit}
          >
            Edit
          </button>
          {correction ? (
            <button
              className="text-sm font-medium text-emerald-800"
              type="button"
              onClick={onUndo}
            >
              Undo
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function validateGramInput(value: string): { correctedGrams: number | null; error: string | null } {
  const trimmedValue = value.trim();

  if (!trimmedValue) {
    return {
      correctedGrams: null,
      error: "Please enter a portion in grams.",
    };
  }

  const numericValue = Number(trimmedValue);

  if (!Number.isFinite(numericValue)) {
    return {
      correctedGrams: null,
      error: "Please enter a valid number.",
    };
  }

  const correctedGrams = Math.round(numericValue);

  if (numericValue <= 0 || correctedGrams < 1) {
    return {
      correctedGrams: null,
      error: "Portion must be at least 1g.",
    };
  }

  if (numericValue > 2000) {
    return {
      correctedGrams: null,
      error: "Portion seems too large. Please check your value.",
    };
  }

  return {
    correctedGrams,
    error: null,
  };
}
