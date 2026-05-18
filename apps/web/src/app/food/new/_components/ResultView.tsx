import { formatCalories, formatFlag } from "../../../../lib/food-analysis-format";
import type {
  CalorieRange,
  FoodAnalysis,
  FoodItem,
  UserCorrection,
} from "../../../../lib/food-analysis-types";
import { FoodItemRow } from "./FoodItemRow";
import { ImagePreview } from "./ImagePreview";

export function ResultView({
  analysis,
  assumptions,
  correctedTotal,
  corrections,
  correctionError,
  correctionLoading,
  editingItemId,
  hasAnyCorrection,
  previewFailed,
  previewUrl,
  file,
  onCancelEdit,
  onCommitCorrection,
  onStartEdit,
  onUndoCorrection,
}: {
  analysis: FoodAnalysis;
  assumptions: string[];
  correctedTotal: CalorieRange;
  corrections: Record<string, UserCorrection>;
  correctionError: { itemId: string; message: string } | null;
  correctionLoading: string | null;
  editingItemId: string | null;
  hasAnyCorrection: boolean;
  previewFailed: boolean;
  previewUrl: string | null;
  file: File | null;
  onCancelEdit: () => void;
  onCommitCorrection: (item: FoodItem, correctedGrams: number) => Promise<void>;
  onStartEdit: (itemId: string) => void;
  onUndoCorrection: (itemId: string) => void;
}) {
  const hasItems = analysis.items.length > 0;
  const headlineRange = formatCalories(correctedTotal);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-3">
          <span className="inline-flex rounded-full border border-stone-300 bg-stone-100 px-3 py-1 text-xs font-semibold text-stone-700">
            {hasAnyCorrection ? "Mock analysis — user corrected" : "Mock analysis"}
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
            // The compound key intentionally remounts rows when edit/display/correction state
            // changes, resetting local draft grams without a useEffect.
            <FoodItemRow
              applyError={
                correctionError?.itemId === item.item_id ? correctionError.message : null
              }
              correction={corrections[item.item_id] ?? null}
              isEditing={editingItemId === item.item_id}
              isSubmitting={correctionLoading === item.item_id}
              item={item}
              key={`${item.item_id}-${editingItemId === item.item_id ? "editing" : "display"}-${
                corrections[item.item_id]?.correction_id ?? "original"
              }`}
              onCancel={onCancelEdit}
              onCommit={(correctedGrams) => onCommitCorrection(item, correctedGrams)}
              onStartEdit={() => onStartEdit(item.item_id)}
              onUndo={() => onUndoCorrection(item.item_id)}
            />
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

export function LoadingResult() {
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

export function EmptyResult() {
  return (
    <div className="flex min-h-80 items-center justify-center text-center">
      <p className="max-w-sm text-sm leading-6 text-stone-600">
        Select a food photo to see a structured mock analysis here.
      </p>
    </div>
  );
}
