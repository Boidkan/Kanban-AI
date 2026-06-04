"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, initialData, moveCard, type BoardData } from "@/lib/kanban";
import { chatWithAI, fetchBoard, saveBoard, type AIConversationMessage } from "@/lib/api";

type KanbanBoardProps = {
  onLogout?: () => void;
};

export const KanbanBoard = ({ onLogout }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isAIThinking, setIsAIThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiError, setAIError] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<AIConversationMessage[]>([]);
  const username = "user";

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  useEffect(() => {
    let isMounted = true;

    const loadBoard = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetchBoard(username);
        if (isMounted) {
          setBoard(response.board);
        }
      } catch (loadError) {
        if (isMounted) {
          setBoard(initialData);
          setError(loadError instanceof Error ? loadError.message : "Failed to load board.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadBoard();
    return () => {
      isMounted = false;
    };
  }, []);

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const persistBoard = async (nextBoard: BoardData) => {
    setIsSaving(true);
    setError(null);
    try {
      await saveBoard(username, nextBoard);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save changes.");
    } finally {
      setIsSaving(false);
    }
  };

  const commitBoard = (nextBoard: BoardData) => {
    setBoard(nextBoard);
    void persistBoard(nextBoard);
  };

  const handleAIChatSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const question = chatInput.trim();
    if (!question) {
      return;
    }

    const nextConversation: AIConversationMessage[] = [
      ...messages,
      { role: "user", content: question },
    ];
    setMessages(nextConversation);
    setChatInput("");
    setAIError(null);
    setIsAIThinking(true);

    try {
      const response = await chatWithAI(username, question, nextConversation);
      setMessages((prev) => [...prev, { role: "assistant", content: response.message }]);
      if (response.board_updated) {
        setBoard(response.board);
      }
    } catch (chatError) {
      setAIError(chatError instanceof Error ? chatError.message : "AI request failed.");
    } finally {
      setIsAIThinking(false);
    }
  };

  const handleAIChatKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      const form = event.currentTarget.form;
      if (form) {
        form.requestSubmit();
      }
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!board || !over || active.id === over.id) {
      return;
    }

    const nextBoard = {
      ...board,
      columns: moveCard(board.columns, active.id as string, over.id as string),
    };
    commitBoard(nextBoard);
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!board) {
      return;
    }
    const nextBoard = {
      ...board,
      columns: board.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    };
    commitBoard(nextBoard);
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    if (!board) {
      return;
    }
    const id = createId("card");
    const nextBoard = {
      ...board,
      cards: {
        ...board.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: board.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    };
    commitBoard(nextBoard);
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (!board) {
      return;
    }
    const nextBoard = {
      ...board,
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => id !== cardId)
      ),
      columns: board.columns.map((column) =>
        column.id === columnId
          ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
          : column
      ),
    };
    commitBoard(nextBoard);
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (isLoading || !board) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-lg items-center px-6 py-10">
        <section className="w-full rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]">
          <p className="text-sm text-[var(--gray-text)]">Loading board...</p>
        </section>
      </main>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
              {isSaving ? (
                <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
                  Saving...
                </p>
              ) : null}
              {onLogout ? (
                <button
                  type="button"
                  onClick={onLogout}
                  className="mt-3 rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
                >
                  Log out
                </button>
              ) : null}
            </div>
          </div>
          {error ? (
            <p
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[3fr_1fr]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <aside className="flex min-h-[520px] flex-col rounded-3xl border border-[var(--stroke)] bg-white p-5 shadow-[var(--shadow)]">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
              AI Assistant
            </p>
            <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
              Board Chat
            </h2>
            <p className="mt-2 text-sm text-[var(--gray-text)]">
              Ask for planning help or board updates.
            </p>

            <div className="mt-4 flex-1 space-y-3 overflow-auto rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-3">
              {messages.length === 0 ? (
                <p className="text-sm text-[var(--gray-text)]">
                  Try: &quot;Summarize the board and suggest next actions.&quot;
                </p>
              ) : (
                messages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`rounded-xl px-3 py-2 text-sm ${
                      message.role === "user"
                        ? "ml-6 bg-[var(--secondary-purple)] text-white"
                        : "mr-6 bg-white text-[var(--navy-dark)]"
                    }`}
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-wide opacity-80">
                      {message.role}
                    </p>
                    <p className="mt-1 whitespace-pre-wrap">{message.content}</p>
                  </div>
                ))
              )}
              {isAIThinking ? (
                <p className="text-sm font-semibold text-[var(--primary-blue)]">AI is thinking...</p>
              ) : null}
            </div>

            {aiError ? (
              <p
                role="alert"
                className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {aiError}
              </p>
            ) : null}

            <form onSubmit={handleAIChatSubmit} className="mt-3 space-y-2">
              <label htmlFor="ai-chat-input" className="sr-only">
                Ask AI
              </label>
              <textarea
                id="ai-chat-input"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                onKeyDown={handleAIChatKeyDown}
                rows={3}
                placeholder="Ask AI about your board..."
                className="w-full resize-none rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
              />
              <button
                type="submit"
                disabled={isAIThinking}
                className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Send
              </button>
            </form>
          </aside>
        </div>
      </main>
    </div>
  );
};
