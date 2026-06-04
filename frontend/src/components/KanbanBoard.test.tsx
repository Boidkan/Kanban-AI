import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { fallbackBoard } from "@/lib/kanban";
import { chatWithAI, fetchBoard, saveBoard } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchBoard: vi.fn(),
  saveBoard: vi.fn(),
  chatWithAI: vi.fn(),
}));

const mockedFetchBoard = vi.mocked(fetchBoard);
const mockedSaveBoard = vi.mocked(saveBoard);
const mockedChatWithAI = vi.mocked(chatWithAI);

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    mockedChatWithAI.mockResolvedValue({
      model: "gpt-4o-mini",
      message: "No changes needed.",
      board: fallbackBoard,
      version: 1,
      board_updated: false,
    });
  });

  it("renders five columns", async () => {
    render(<KanbanBoard />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column and saves (debounced)", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
    await waitFor(() => expect(mockedSaveBoard).toHaveBeenCalled());
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
    await waitFor(() => expect(mockedSaveBoard).toHaveBeenCalled());
  });

  it("shows load error and keeps board usable", async () => {
    mockedFetchBoard.mockRejectedValueOnce(new Error("backend unavailable"));
    render(<KanbanBoard />);

    expect(await screen.findByRole("alert")).toHaveTextContent("backend unavailable");
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renders chat response and applies AI board update", async () => {
    const updatedBoard = {
      ...fallbackBoard,
      columns: fallbackBoard.columns.map((column, index) =>
        index === 0 ? { ...column, title: "AI Updated Column" } : column
      ),
    };
    mockedChatWithAI.mockResolvedValueOnce({
      model: "gpt-4o-mini",
      message: "I updated the first column title.",
      board: updatedBoard,
      version: 2,
      board_updated: true,
    });

    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);

    await userEvent.type(
      screen.getByPlaceholderText(/ask ai about your board/i),
      "Update the first column title."
    );
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText("I updated the first column title.")).toBeInTheDocument();
    const firstColumn = getFirstColumn();
    expect(within(firstColumn).getByLabelText("Column title")).toHaveValue(
      "AI Updated Column"
    );
  });
});
