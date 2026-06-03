# Frontend agent guide

This file describes the existing frontend codebase and the conventions to follow when editing it.

## What exists today

- Framework: Next.js App Router with React + TypeScript.
- Styling: Tailwind CSS utility classes with CSS variables defined in `src/app/globals.css`.
- Core UI: Single-page Kanban board rendered at `/` via `src/app/page.tsx`.
- Interaction model: Client-side state managed in `src/components/KanbanBoard.tsx`.
- Drag and drop: `@dnd-kit` (`DndContext`, sortable items, droppable columns).
- Test setup:
  - Unit/component tests: Vitest + Testing Library.
  - Browser integration tests: Playwright.

## File map

- `src/app/layout.tsx`: Global HTML shell, fonts, metadata.
- `src/app/page.tsx`: Entry point for the board page.
- `src/app/globals.css`: Theme tokens and global styles.
- `src/lib/kanban.ts`: Board types, seed data, card-move algorithm, ID generation.
- `src/components/KanbanBoard.tsx`: Top-level board state + drag handlers.
- `src/components/KanbanColumn.tsx`: Column rendering, title edit, card list, add form.
- `src/components/KanbanCard.tsx`: Sortable card rendering + delete action.
- `src/components/NewCardForm.tsx`: Inline add-card UX.
- `src/components/KanbanCardPreview.tsx`: Drag overlay card preview.
- `src/components/*.test.tsx`, `src/lib/*.test.ts`: Unit/component coverage.
- `tests/*.spec.ts`: End-to-end browser scenarios.

## Current behavior contract

- There are five fixed columns in seed data, but titles are editable.
- Cards can be added, removed, and moved within/across columns.
- Board state is currently in-memory only and resets on reload.
- Drag-and-drop behavior depends on stable IDs and `data-testid` hooks used by tests.

## Coding conventions for this frontend

- Keep components small and focused; prefer explicit props over implicit context.
- Keep shared domain logic in `src/lib/` and UI state orchestration in components.
- Preserve TypeScript types for board entities (`Card`, `Column`, `BoardData`) and update tests when contracts change.
- Use existing color tokens (`--accent-yellow`, `--primary-blue`, `--secondary-purple`, `--navy-dark`, `--gray-text`) instead of ad hoc colors.
- Prefer readable utility class composition and avoid unnecessary abstraction layers.
- Use deterministic selectors (`data-testid`) for elements covered by tests.
- When changing behavior, update both unit/component tests and e2e tests that verify user-visible flows.

## Testing workflow

- Unit/component: `npm run test:unit`
- End-to-end: `npm run test:e2e`
- Full suite: `npm run test:all`

Keep tests aligned with behavior changes; do not leave stale assertions.

## Future backend integration guidance

When moving from local state to API-backed persistence:

- Introduce a small API client layer (for example `src/lib/api.ts`) for HTTP calls instead of scattering fetch logic across components.
- Keep mapping between backend payloads and frontend `BoardData` explicit and typed.
- Handle loading and error states in `KanbanBoard` with minimal UI noise.
- Preserve optimistic UX only when rollback behavior is clearly defined; otherwise prefer confirm-then-render for MVP simplicity.
- Keep drag-and-drop and editing interactions unchanged from the user perspective while swapping state source.
- Add integration tests for persisted board behavior (reload retains state).

## Future AI sidebar integration guidance

When chat functionality is added:

- Isolate chat UI into dedicated components (for example `src/components/chat/*`).
- Treat AI responses as typed backend contracts; do not parse freeform text in the browser.
- Apply board updates from AI responses through one board-update path to avoid state drift.
- Ensure chat loading/error states are visible but unobtrusive.
- Add tests for both "assistant message only" and "assistant message + board update" responses.

## Guardrails

- Keep the frontend simple and avoid over-engineering.
- Do not introduce extra features beyond the current part's scope.
- Prefer root-cause fixes with tests over speculative defensive code.
