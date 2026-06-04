import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanApp } from "@/components/KanbanApp";
import { fallbackBoard } from "@/lib/kanban";
import { fetchBoard, getToken, login, logout, saveBoard } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  login: vi.fn(),
  logout: vi.fn(),
  getToken: vi.fn(),
  fetchBoard: vi.fn(),
  saveBoard: vi.fn(),
  chatWithAI: vi.fn(),
}));

const mockedLogin = vi.mocked(login);
const mockedLogout = vi.mocked(logout);
const mockedGetToken = vi.mocked(getToken);
const mockedFetchBoard = vi.mocked(fetchBoard);
const mockedSaveBoard = vi.mocked(saveBoard);

const getUsernameInput = () => screen.getByLabelText(/username/i);
const getPasswordInput = () => screen.getByLabelText(/password/i);

describe("KanbanApp auth flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetToken.mockReturnValue(null);
    mockedLogin.mockImplementation(async (username: string, password: string) => {
      if (username === "user" && password === "password") {
        return { token: "test-token", username: "user" };
      }
      throw new Error("Invalid credentials.");
    });
    mockedLogout.mockResolvedValue();
    mockedFetchBoard.mockResolvedValue({
      username: "user",
      version: 1,
      board: fallbackBoard,
    });
    mockedSaveBoard.mockResolvedValue({
      username: "user",
      version: 2,
      board: fallbackBoard,
    });
  });

  it("shows login form before authentication", () => {
    render(<KanbanApp />);
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByText("Kanban Studio")).not.toBeInTheDocument();
  });

  it("blocks invalid credentials", async () => {
    render(<KanbanApp />);

    await userEvent.type(getUsernameInput(), "wrong");
    await userEvent.type(getPasswordInput(), "creds");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid credentials. Use user / password."
    );
    expect(screen.queryByText("Kanban Studio")).not.toBeInTheDocument();
  });

  it("logs in and logs out", async () => {
    render(<KanbanApp />);

    await userEvent.type(getUsernameInput(), "user");
    await userEvent.type(getPasswordInput(), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByRole("heading", { name: "Kanban Studio" })
    ).toBeInTheDocument();
    expect(mockedLogin).toHaveBeenCalledWith("user", "password");

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));

    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(mockedLogout).toHaveBeenCalled();
  });

  it("restores the session when a token is already stored", async () => {
    mockedGetToken.mockReturnValue("existing-token");
    render(<KanbanApp />);

    expect(
      await screen.findByRole("heading", { name: "Kanban Studio" })
    ).toBeInTheDocument();
  });
});
