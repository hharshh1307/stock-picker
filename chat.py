"""CLI Chat Interface for the Financial Expert Agent."""

import sys

from agent import FinancialExpertAgent
from agent_prompts import GREETING_MESSAGE
from data_store import DataStore
from utils import setup_logger

logger = setup_logger(__name__, "chat.log")


def print_colored(text: str, color: str = "default") -> None:
    """Print colored text to terminal."""
    colors = {
        "green": "\033[92m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
        "default": "\033[0m",
        "bold": "\033[1m",
    }
    reset = "\033[0m"
    print(f"{colors.get(color, '')}{text}{reset}")


def run_chat(model: str = "gemini-2.5-flash", db_path: str | None = None) -> None:
    """Run the interactive chat session."""
    print_colored("\n" + "=" * 60, "cyan")
    print_colored("  NIFTY SAGE - AI Stock Market Analyst", "bold")
    print_colored("=" * 60 + "\n", "cyan")

    # Initialize
    store = DataStore(db_path=db_path)

    # Check for API key
    import os
    from dotenv import load_dotenv
    load_dotenv()

    if not os.getenv("GEMINI_API_KEY"):
        print_colored("Error: GEMINI_API_KEY not found in environment.", "red")
        print_colored("Please create a .env file with your GEMINI_API_KEY:", "yellow")
        print_colored("  echo 'GEMINI_API_KEY=AIzaSy...' > .env", "default")
        store.close()
        return

    try:
        agent = FinancialExpertAgent(store, model=model)
        print_colored(f"Using model: {model}", "cyan")
        print()
        print(GREETING_MESSAGE)
        print()
        print_colored("Type 'quit' or 'exit' to end the session.", "yellow")
        print_colored("Type 'clear' to start a new conversation.", "yellow")
        print_colored("-" * 60, "cyan")

        while True:
            try:
                print()
                user_input = input("\033[92mYou: \033[0m").strip()

                if not user_input:
                    continue

                if user_input.lower() in ("quit", "exit", "q"):
                    print_colored("\nGoodbye! Happy investing! 📈", "green")
                    break

                if user_input.lower() == "clear":
                    agent.reset_conversation()
                    print_colored("Conversation cleared. Starting fresh!", "yellow")
                    continue

                if user_input.lower() == "help":
                    print(GREETING_MESSAGE)
                    continue

                # Stream the response
                print()
                print_colored("Nifty Sage: ", "blue")

                full_response = ""
                for chunk in agent.stream_response_sync(user_input):
                    chunk_type = chunk.get("type")

                    if chunk_type == "text":
                        content = chunk.get("content", "")
                        print(content, end="", flush=True)
                        full_response += content

                    elif chunk_type == "tool_call":
                        tool_name = chunk.get("tool", "")
                        print_colored(f"\n  [Calling {tool_name}...]", "magenta")

                    elif chunk_type == "tool_result":
                        tool_name = chunk.get("tool", "")
                        print_colored(f"  [Got {tool_name} data]", "magenta")

                    elif chunk_type == "error":
                        print_colored(f"\nError: {chunk.get('content', 'Unknown error')}", "red")

                print()  # Newline after response

            except KeyboardInterrupt:
                print_colored("\n\nInterrupted. Type 'quit' to exit.", "yellow")
                continue

    except Exception as e:
        logger.error(f"Chat error: {e}")
        print_colored(f"\nError: {e}", "red")

    finally:
        store.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Nifty Sage CLI Chat")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model to use")
    parser.add_argument("--db", help="Path to SQLite database")
    args = parser.parse_args()

    run_chat(model=args.model, db_path=args.db)
