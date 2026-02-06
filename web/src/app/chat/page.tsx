import { api } from "@/lib/api";
import { ChatContainer } from "@/components/chat/chat-container";

export const dynamic = "force-dynamic";

async function getSuggestions() {
  try {
    return await api.chat.getSuggestions();
  } catch (error) {
    console.error("Failed to fetch suggestions:", error);
    return [
      { question: "Should I invest in RELIANCE?", category: "stock_analysis" },
      { question: "Compare TCS vs INFY", category: "comparison" },
      { question: "Which sectors are trending?", category: "market" },
      { question: "What are the top gaining stocks?", category: "market" },
    ];
  }
}

export default async function ChatPage() {
  const suggestions = await getSuggestions();

  return (
    <div className="h-screen">
      <ChatContainer suggestions={suggestions} />
    </div>
  );
}
