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

type LoginResponse = {
  token: string;
  username: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const TOKEN_STORAGE_KEY = "pm-auth-token";

const createUrl = (path: string) => `${API_BASE_URL}${path}`;

export const getToken = (): string | null => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
};

const setToken = (token: string | null) => {
  if (typeof window === "undefined") {
    return;
  }
  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
};

const authHeaders = (): Record<string, string> => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const parseErrorMessage = async (response: Response) => {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed with status ${response.status}.`;
  } catch {
    return `Request failed with status ${response.status}.`;
  }
};

export const login = async (
  username: string,
  password: string
): Promise<LoginResponse> => {
  const response = await fetch(createUrl("/api/auth/login"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  const payload = (await response.json()) as LoginResponse;
  setToken(payload.token);
  return payload;
};

export const logout = async (): Promise<void> => {
  try {
    await fetch(createUrl("/api/auth/logout"), {
      method: "POST",
      headers: authHeaders(),
    });
  } finally {
    setToken(null);
  }
};

export const fetchBoard = async (): Promise<BoardResponse> => {
  const response = await fetch(createUrl("/api/board"), {
    method: "GET",
    headers: { Accept: "application/json", ...authHeaders() },
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as BoardResponse;
};

export const saveBoard = async (
  board: BoardData,
  expectedVersion?: number
): Promise<BoardResponse> => {
  const response = await fetch(createUrl("/api/board"), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ board, expected_version: expectedVersion ?? null }),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as BoardResponse;
};

export const chatWithAI = async (
  question: string,
  conversation: AIConversationMessage[]
): Promise<AIChatResponse> => {
  const response = await fetch(createUrl("/api/ai/board"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ question, conversation }),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as AIChatResponse;
};
