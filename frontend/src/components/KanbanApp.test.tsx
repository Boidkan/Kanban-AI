import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanApp } from "@/components/KanbanApp";
import { fallbackBoard } from "@/lib/kanban";
import { fetchBoard, getToken, login, logout, register, saveBoard } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  getToken: vi.fn(),
  fetchBoard: vi.fn(),
  saveBoard: vi.fn(),
  chatWithAI: vi.fn(),
}));

const mockedLogin = vi.mocked(login);
const mockedLogout = vi.mocked(logout);
const mockedRegister = vi.mocked(register);
const mockedGetToken = vi.mocked(getToken);
const mockedFetchBoard = vi.mocked(fetchBoard);
const mockedSaveBoard = vi.mocked(saveBoard);

const getUsernameInput = () => screen.getByLabelText(/username/i);
const getPasswordInput = () => screen.getByLabelText(/password/i);
const getToggle = () => screen.getByTestId("auth-mode-toggle");

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
    mockedRegister.mockResolvedValue({ token: "new-token", username: "alice" });
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

  it("toggles between sign in and create account", async () => {
    render(<KanbanApp />);
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();

    await userEvent.click(getToggle());

    expect(screen.getByRole("heading", { name: "Create account" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();

    await userEvent.click(getToggle());
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("creates an account and lands on the board", async () => {
    render(<KanbanApp />);
    await userEvent.click(getToggle());

    await userEvent.type(getUsernameInput(), "alice");
    await userEvent.type(getPasswordInput(), "supersecret");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(
      await screen.findByRole("heading", { name: "Kanban Studio" })
    ).toBeInTheDocument();
    expect(mockedRegister).toHaveBeenCalledWith("alice", "supersecret");
  });

  it("shows the server error when registration fails", async () => {
    mockedRegister.mockRejectedValueOnce(new Error("Username is already taken."));
    render(<KanbanApp />);
    await userEvent.click(getToggle());

    await userEvent.type(getUsernameInput(), "user");
    await userEvent.type(getPasswordInput(), "supersecret");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Username is already taken."
    );
    expect(screen.queryByText("Kanban Studio")).not.toBeInTheDocument();
  });

  it("blocks an invalid registration before calling the API", async () => {
    render(<KanbanApp />);
    await userEvent.click(getToggle());

    await userEvent.type(getUsernameInput(), "alice");
    await userEvent.type(getPasswordInput(), "short");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Password must be at least 8 characters."
    );
    expect(mockedRegister).not.toHaveBeenCalled();
  });
});
