export type Card = {
  id: string;
  title: string;
  details: string;
};

export type Column = {
  id: string;
  title: string;
  cardIds: string[];
};

export type BoardData = {
  columns: Column[];
  cards: Record<string, Card>;
};

export const initialData: BoardData = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-discovery", title: "Discovery", cardIds: ["card-3", "card-4"] },
    { id: "col-progress", title: "In Progress", cardIds: ["card-5", "card-6"] },
    { id: "col-review", title: "Review", cardIds: ["card-7", "card-8"] },
    { id: "col-done", title: "Done", cardIds: ["card-9", "card-10"] },
  ],
  cards: {
    "card-1": {
      id: "card-1",
      title: "Part 1 - Detailed planning",
      details: "Finalize checklist plan and get user sign-off before execution.",
    },
    "card-2": {
      id: "card-2",
      title: "Part 2 - Scaffold Docker + FastAPI",
      details: "Prepare container, backend skeleton, and cross-platform run scripts.",
    },
    "card-3": {
      id: "card-3",
      title: "Part 3 - Serve static frontend",
      details: "Build Next.js assets and serve the Kanban app at root path.",
    },
    "card-4": {
      id: "card-4",
      title: "Part 4 - Fake sign-in flow",
      details: "Gate board access with MVP credentials and add logout behavior.",
    },
    "card-5": {
      id: "card-5",
      title: "Part 5 - Database modeling",
      details: "Document SQLite schema and JSON board storage strategy.",
    },
    "card-6": {
      id: "card-6",
      title: "Part 6 - Backend board APIs",
      details: "Implement read/write routes with validation and DB auto-bootstrap.",
    },
    "card-7": {
      id: "card-7",
      title: "Part 7 - Frontend API integration",
      details: "Wire Kanban interactions to backend persistence with loading states.",
    },
    "card-8": {
      id: "card-8",
      title: "Part 8 - AI connectivity",
      details: "Verify OpenAI connectivity with deterministic 2+2 check endpoint.",
    },
    "card-9": {
      id: "card-9",
      title: "Part 9 - Structured AI updates",
      details: "Return validated assistant response plus optional board update payload.",
    },
    "card-10": {
      id: "card-10",
      title: "Part 10 - Sidebar AI chat",
      details: "Ship chat sidebar and refresh board automatically on AI updates.",
    },
  },
};

const isColumnId = (columns: Column[], id: string) =>
  columns.some((column) => column.id === id);

const findColumnId = (columns: Column[], id: string) => {
  if (isColumnId(columns, id)) {
    return id;
  }
  return columns.find((column) => column.cardIds.includes(id))?.id;
};

export const moveCard = (
  columns: Column[],
  activeId: string,
  overId: string
): Column[] => {
  const activeColumnId = findColumnId(columns, activeId);
  const overColumnId = findColumnId(columns, overId);

  if (!activeColumnId || !overColumnId) {
    return columns;
  }

  const activeColumn = columns.find((column) => column.id === activeColumnId);
  const overColumn = columns.find((column) => column.id === overColumnId);

  if (!activeColumn || !overColumn) {
    return columns;
  }

  const isOverColumn = isColumnId(columns, overId);

  if (activeColumnId === overColumnId) {
    if (isOverColumn) {
      const nextCardIds = activeColumn.cardIds.filter(
        (cardId) => cardId !== activeId
      );
      nextCardIds.push(activeId);
      return columns.map((column) =>
        column.id === activeColumnId
          ? { ...column, cardIds: nextCardIds }
          : column
      );
    }

    const oldIndex = activeColumn.cardIds.indexOf(activeId);
    const newIndex = activeColumn.cardIds.indexOf(overId);

    if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) {
      return columns;
    }

    const nextCardIds = [...activeColumn.cardIds];
    nextCardIds.splice(oldIndex, 1);
    nextCardIds.splice(newIndex, 0, activeId);

    return columns.map((column) =>
      column.id === activeColumnId
        ? { ...column, cardIds: nextCardIds }
        : column
    );
  }

  const activeIndex = activeColumn.cardIds.indexOf(activeId);
  if (activeIndex === -1) {
    return columns;
  }

  const nextActiveCardIds = [...activeColumn.cardIds];
  nextActiveCardIds.splice(activeIndex, 1);

  const nextOverCardIds = [...overColumn.cardIds];
  if (isOverColumn) {
    nextOverCardIds.push(activeId);
  } else {
    const overIndex = overColumn.cardIds.indexOf(overId);
    const insertIndex = overIndex === -1 ? nextOverCardIds.length : overIndex;
    nextOverCardIds.splice(insertIndex, 0, activeId);
  }

  return columns.map((column) => {
    if (column.id === activeColumnId) {
      return { ...column, cardIds: nextActiveCardIds };
    }
    if (column.id === overColumnId) {
      return { ...column, cardIds: nextOverCardIds };
    }
    return column;
  });
};

export const createId = (prefix: string) => {
  const randomPart = Math.random().toString(36).slice(2, 8);
  const timePart = Date.now().toString(36);
  return `${prefix}-${randomPart}${timePart}`;
};
