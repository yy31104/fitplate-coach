import { expect, test, type Page } from "@playwright/test";

const MOCK_ANALYSIS = {
  analysis_id: "analysis-001",
  schema_version: "food_analysis.v1",
  mode: "mock",
  analyzed_at: "2026-05-18T12:00:00Z",
  items_count: 1,
  items: [
    {
      item_id: "item-001",
      name: "Chicken breast",
      portion: {
        description: "~150g",
        grams_estimate: 150,
        assumptions: ["Portion estimated from visible plate size."],
      },
      calories: {
        min: 180,
        max: 220,
        point_estimate: 200,
      },
      calorie_density_kcal_per_gram: 1.33,
      confidence: "medium",
    },
  ],
  total_calories: {
    min: 180,
    max: 220,
    point_estimate: 200,
  },
  uncertainty_notes: ["Cooking method is assumed to be standard."],
  safety_flags: [],
  user_corrections: [],
};

const MOCK_CORRECTION = {
  correction_id: "correction-001",
  item_id: "item-001",
  original_name: "Chicken breast",
  corrected_name: "Chicken breast",
  original_grams: 150,
  corrected_grams: 250,
  original_calories: {
    min: 180,
    max: 220,
    point_estimate: 200,
  },
  corrected_calories: {
    min: 300,
    max: 400,
    point_estimate: 350,
  },
  correction_timestamp: "2026-05-18T12:01:00Z",
  correction_source: "user",
};

const JPEG_FILE = {
  name: "lunch.jpg",
  mimeType: "image/jpeg",
  buffer: Buffer.from([0xff, 0xd8, 0xff, 0xd9]),
};

const UPLOAD_SENTINEL = "fitplate-upload-sentinel";

test("page renders the file selection UI", async ({ page }) => {
  await page.goto("/food/new");

  await expect(page.getByRole("heading", { name: "Select a food photo to estimate calories." })).toBeVisible();
  await expect(page.getByText("Choose a photo")).toBeVisible();
  await expect(page.getByText("JPEG, PNG, WebP, and HEIC. Maximum 10 MB.")).toBeVisible();
  await expect(page.getByText("Select a food photo to see a structured mock analysis here.")).toBeVisible();
});

test("selecting an invalid file type shows the inline validation error and does not show Analyze", async ({
  page,
}) => {
  await page.goto("/food/new");

  await page.locator("#food-photo").setInputFiles({
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("not an image"),
  });

  await expect(page.getByText("Only JPEG, PNG, WebP, and HEIC images are supported.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Analyze" })).toHaveCount(0);
});

test("selecting a valid JPEG and clicking Analyze shows a mock result", async ({ page }) => {
  await mockFoodEndpoints(page);
  await page.goto("/food/new");

  await page.locator("#food-photo").setInputFiles(JPEG_FILE);
  await page.getByRole("button", { name: "Analyze" }).click();

  await expect(page.getByRole("heading", { name: "Food photo estimate" })).toBeVisible();
  await expect(page.getByText("Mock analysis", { exact: true })).toBeVisible();
  await expect(page.getByText("Chicken breast")).toBeVisible();
  await expect(page.getByText("~150g · 180-220 kcal")).toBeVisible();
});

test("clicking Edit opens the grams input with Apply and Cancel", async ({ page }) => {
  await mockFoodEndpoints(page);
  await page.goto("/food/new");

  await page.locator("#food-photo").setInputFiles(JPEG_FILE);
  await page.getByRole("button", { name: "Analyze" }).click();
  await page.getByRole("button", { name: "Edit" }).click();

  await expect(page.getByLabel("Portion in grams")).toHaveValue("150");
  await expect(page.getByRole("button", { name: "Apply" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
});

test("applying a correction updates the display with a corrected badge and user-corrected status", async ({
  page,
}) => {
  await mockFoodEndpoints(page);
  await page.goto("/food/new");

  await page.locator("#food-photo").setInputFiles(JPEG_FILE);
  await page.getByRole("button", { name: "Analyze" }).click();
  await page.getByRole("button", { name: "Edit" }).click();
  await page.getByLabel("Portion in grams").fill("250");
  await page.getByRole("button", { name: "Apply" }).click();

  await expect(page.getByText("Mock analysis — user corrected")).toBeVisible();
  await expect(page.getByText("corrected", { exact: true })).toBeVisible();
  await expect(page.getByText("~250g · 300-400 kcal")).toBeVisible();
  await expect(page.getByText("Original: 150g")).toBeVisible();
});

test("upload transport sends multipart file bytes and displays analysis", async ({ page }) => {
  const uploadRequest: UploadRequestCapture = { hit: false };
  await mockFoodEndpoints(page);
  await mockUploadEndpoint(page, uploadRequest);
  await page.goto("/food/new");

  await page.locator("#food-photo").setInputFiles({
    name: "meal.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from(`fake-jpeg-${UPLOAD_SENTINEL}`),
  });
  await page
    .getByRole("checkbox", { name: "Send image bytes to backend (upload transport)" })
    .check();
  await page.getByRole("button", { name: "Analyze" }).click();

  await expect(page.getByRole("heading", { name: "Food photo estimate" })).toBeVisible();
  expect(uploadRequest.hit).toBe(true);
  expect(uploadRequest.method).toBe("POST");
  expect(uploadRequest.contentType).toContain("multipart/form-data");
  expect(uploadRequest.body?.toString("utf8")).toContain(UPLOAD_SENTINEL);
  await expect(page.getByText("Chicken breast")).toBeVisible();
});

type UploadRequestCapture = {
  hit: boolean;
  method?: string;
  contentType?: string;
  body?: Buffer;
};

async function mockFoodEndpoints(page: Page) {
  await page.route("**/api/v0/food/analyze/mock", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ANALYSIS),
    });
  });

  await page.route("**/api/v0/food/corrections/mock", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_CORRECTION),
    });
  });
}

async function mockUploadEndpoint(page: Page, capture: UploadRequestCapture) {
  await page.route("**/api/v0/food/analyze", async (route) => {
    const request = route.request();
    capture.hit = true;
    capture.method = request.method();
    capture.contentType = request.headers()["content-type"];
    capture.body = request.postDataBuffer() ?? undefined;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ANALYSIS),
    });
  });
}
