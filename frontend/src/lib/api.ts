import type { BoardData } from "@/lib/kanban";

type BoardResponse = {
  username: string;
  version: number;
  board: BoardData;
};

export type AIConversationMessage = {
  role: "user" | "assistant";
  content: string;
};

type AIChatResponse = {
  model: string;
  message: string;
  board: BoardData;
  version: number;
  board_updated: boolean;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

const createUrl = (path: string) => `${API_BASE_URL}${path}`;

const parseErrorMessage = async (response: Response) => {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed with status ${response.status}.`;
  } catch {
    return `Request failed with status ${response.status}.`;
  }
};

export const fetchBoard = async (username: string): Promise<BoardResponse> => {
  const response = await fetch(createUrl(`/api/board/${username}`), {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as BoardResponse;
};

export const saveBoard = async (
  username: string,
  board: BoardData
): Promise<BoardResponse> => {
  const response = await fetch(createUrl(`/api/board/${username}`), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ board }),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as BoardResponse;
};

export const chatWithAI = async (
  username: string,
  question: string,
  conversation: AIConversationMessage[]
): Promise<AIChatResponse> => {
  const response = await fetch(createUrl(`/api/ai/board/${username}`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ question, conversation }),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as AIChatResponse;
};
