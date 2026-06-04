import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanApp } from "@/components/KanbanApp";
import { initialData } from "@/lib/kanban";
import { fetchBoard, saveBoard } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchBoard: vi.fn(),
  saveBoard: vi.fn(),
}));

const mockedFetchBoard = vi.mocked(fetchBoard);
const mockedSaveBoard = vi.mocked(saveBoard);

const getUsernameInput = () => screen.getByLabelText(/username/i);
const getPasswordInput = () => screen.getByLabelText(/password/i);

describe("KanbanApp auth flow", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockedFetchBoard.mockResolvedValue({
      username: "user",
      version: 1,
      board: initialData,
    });
    mockedSaveBoard.mockResolvedValue({
      username: "user",
      version: 2,
      board: initialData,
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

    expect(screen.getByRole("alert")).toHaveTextContent(
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
    expect(window.localStorage.getItem("pm-authenticated")).toBe("true");

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));

    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(window.localStorage.getItem("pm-authenticated")).toBeNull();
  });
});
