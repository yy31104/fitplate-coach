"use client";

import { useEffect, useMemo } from "react";

export function ImagePreview({
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

export function usePreviewUrl(file: File | null): string | null {
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
