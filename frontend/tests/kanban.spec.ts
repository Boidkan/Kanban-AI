import { expect, test, type Page } from "@playwright/test";

type Card = { id: string; title: string; details: string };
type Column = { id: string; title: string; cardIds: string[] };
type BoardData = { columns: Column[]; cards: Record<string, Card> };

const initialBoard: BoardData = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-discovery", title: "Discovery", cardIds: ["card-3"] },
    { id: "col-progress", title: "In Progress", cardIds: ["card-4", "card-5"] },
    { id: "col-review", title: "Review", cardIds: ["card-6"] },
    { id: "col-done", title: "Done", cardIds: ["card-7", "card-8"] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "Align roadmap themes", details: "Draft themes." },
    "card-2": {
      id: "card-2",
      title: "Gather customer signals",
      details: "Review support tags.",
    },
    "card-3": {
      id: "card-3",
      title: "Prototype analytics view",
      details: "Sketch dashboard layout.",
    },
    "card-4": { id: "card-4", title: "Refine status language", details: "Standardize labels." },
    "card-5": { id: "card-5", title: "Design card layout", details: "Improve spacing." },
    "card-6": { id: "card-6", title: "QA micro-interactions", details: "Verify states." },
    "card-7": { id: "card-7", title: "Ship marketing page", details: "Assets delivered." },
    "card-8": { id: "card-8", title: "Close onboarding sprint", details: "Release notes." },
  },
};

const cloneBoard = (board: BoardData): BoardData => JSON.parse(JSON.stringify(board));

const setupBoardApiMock = async (page: Page) => {
  let board = cloneBoard(initialBoard);
  let version = 1;
  const registered = new Set(["user"]);

  await page.route("**/api/auth/login", async (route) => {
    const body = route.request().postDataJSON() as { username?: string };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ token: "e2e-token", username: body.username ?? "user" }),
    });
  });

  await page.route("**/api/auth/register", async (route) => {
    const body = route.request().postDataJSON() as { username?: string };
    const username = (body.username ?? "").trim();
    if (registered.has(username)) {
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Username is already taken." }),
      });
      return;
    }
    registered.add(username);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ token: "e2e-token", username }),
    });
  });

  await page.route("**/api/auth/logout", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok" }),
    });
  });

  await page.route("**/api/board", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ username: "user", version, board }),
      });
      return;
    }

    if (method === "PUT") {
      const payload = route.request().postDataJSON() as { board: BoardData };
      board = payload.board;
      version += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ username: "user", version, board }),
      });
      return;
    }

    await route.fallback();
  });

  await page.route("**/api/ai/board", async (route) => {
    const payload = route.request().postDataJSON() as {
      question: string;
      conversation: { role: "user" | "assistant"; content: string }[];
    };
    const shouldUpdate = payload.question.toLowerCase().includes("rename");

    if (shouldUpdate) {
      board = {
        ...board,
        columns: board.columns.map((column, index) =>
          index === 0 ? { ...column, title: "AI Renamed Backlog" } : column
        ),
      };
      version += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          model: "gpt-4o-mini",
          message: "I renamed the first column.",
          board,
          version,
          board_updated: true,
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        model: "gpt-4o-mini",
        message: "No board changes needed.",
        board,
        version,
        board_updated: false,
      }),
    });
  });
};

const login = async (page: Page) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
};

test("requires sign in before board is shown", async ({ page }) => {
  await setupBoardApiMock(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).not.toBeVisible();
});

test("loads the kanban board", async ({ page }) => {
  await setupBoardApiMock(page);
  await login(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await setupBoardApiMock(page);
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await setupBoardApiMock(page);
  await login(page);
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
  await page.reload();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});

test("supports AI chat flow with board update", async ({ page }) => {
  await setupBoardApiMock(page);
  await login(page);

  await page
    .getByPlaceholder("Ask AI about your board...")
    .fill("Rename the first column to show AI update.");
  await page.getByRole("button", { name: /send/i }).click();

  await expect(page.getByText("I renamed the first column.")).toBeVisible();
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await expect(firstColumn.getByLabel("Column title")).toHaveValue("AI Renamed Backlog");
});

test("registers a new account, logs out, and logs back in", async ({ page }) => {
  await setupBoardApiMock(page);
  await page.goto("/");

  await page.getByTestId("auth-mode-toggle").click();
  await expect(page.getByRole("heading", { name: "Create account" })).toBeVisible();
  await page.getByLabel("Username").fill("newuser");
  await page.getByLabel("Password").fill("supersecret");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();

  await page.getByLabel("Username").fill("newuser");
  await page.getByLabel("Password").fill("supersecret");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
});

test("shows an error when registering a taken username", async ({ page }) => {
  await setupBoardApiMock(page);
  await page.goto("/");

  await page.getByTestId("auth-mode-toggle").click();
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("supersecret");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByText("Username is already taken.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Create account" })).toBeVisible();
});
