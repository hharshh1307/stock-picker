"use client";

import { useState, useRef, useEffect } from "react";
import { useSession } from "next-auth/react";
import { api } from "@/lib/api";
import type { ChatMessage, ChatStreamEvent, ChatSuggestion } from "@/lib/types";
import { MessageBubble } from "./message-bubble";
import { ChatInput } from "./chat-input";
import { SuggestedQuestions } from "./suggested-questions";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, Loader2, RefreshCw } from "lucide-react";

interface ChatContainerProps {
  suggestions: ChatSuggestion[];
}

export function ChatContainer({ suggestions }: ChatContainerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (typeof window !== "undefined") {
      const saved = sessionStorage.getItem("stock_picker_chat");
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          console.error("Failed to parse saved chat", e);
        }
      }
    }
    return [];
  });
  const [isLoading, setIsLoading] = useState(false);
  const [currentToolCall, setCurrentToolCall] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { data: session } = useSession();

  // Get or create conversation ID
  const conversationIdRef = useRef<string>(
    typeof window !== "undefined"
      ? sessionStorage.getItem("stock_picker_conv_id") ||
        (() => {
          const id = crypto.randomUUID();
          sessionStorage.setItem("stock_picker_conv_id", id);
          return id;
        })()
      : "default"
  );
  const conversationId = conversationIdRef.current;

  // Load chat history from backend on mount
  useEffect(() => {
    const userId = (session?.user as any)?.id;
    if (userId && messages.length === 0) {
      fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/chat-history/${userId}/${conversationId}`)
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data) && data.length > 0) {
            setMessages(data.map(m => ({ role: m.role, content: m.content })));
          }
        })
        .catch(console.error);
    }
  }, [session, conversationId]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentToolCall]);

  // Persist messages
  useEffect(() => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("stock_picker_chat", JSON.stringify(messages));
    }
  }, [messages]);

  const handleClearChat = () => {
    setMessages([]);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("stock_picker_chat");
      sessionStorage.removeItem("stock_picker_conv_id");
      
      const userId = (session?.user as any)?.id;
      if (userId) {
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/chat-history/${userId}/${conversationId}`, {
          method: "DELETE"
        }).catch(console.error);
      }
      
      // Reset conversation ID on clear
      conversationIdRef.current = crypto.randomUUID();
      sessionStorage.setItem("stock_picker_conv_id", conversationIdRef.current);
    }
  };

  const handleSend = async (message: string) => {
    if (!message.trim() || isLoading) return;

    // Add user message
    const userMessage: ChatMessage = { role: "user", content: message };
    setMessages((prev) => [...prev, userMessage]);

    // Add placeholder assistant message
    const assistantMessage: ChatMessage = {
      role: "assistant",
      content: "",
      isStreaming: true,
    };
    setMessages((prev) => [...prev, assistantMessage]);

    setIsLoading(true);
    setCurrentToolCall(null);

    try {
      let fullContent = "";
      const userId = (session?.user as any)?.id;

      for await (const event of api.chat.streamChat(message, conversationId, userId)) {
        const typedEvent = event as ChatStreamEvent;

        if (typedEvent.type === "text" && typedEvent.content) {
          fullContent += typedEvent.content;
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastIdx = newMessages.length - 1;
            newMessages[lastIdx] = {
              ...newMessages[lastIdx],
              content: fullContent,
            };
            return newMessages;
          });
        } else if (typedEvent.type === "tool_call") {
          setCurrentToolCall(typedEvent.tool || null);
        } else if (typedEvent.type === "tool_result") {
          setCurrentToolCall(null);
        } else if (typedEvent.type === "error") {
          fullContent += `\n\n*Error: ${typedEvent.content}*`;
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastIdx = newMessages.length - 1;
            newMessages[lastIdx] = {
              ...newMessages[lastIdx],
              content: fullContent,
            };
            return newMessages;
          });
        } else if (typedEvent.type === "done") {
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastIdx = newMessages.length - 1;
            newMessages[lastIdx] = {
              ...newMessages[lastIdx],
              isStreaming: false,
            };
            return newMessages;
          });
        }
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => {
        const newMessages = [...prev];
        const lastIdx = newMessages.length - 1;
        newMessages[lastIdx] = {
          role: "assistant",
          content: "Sorry, I encountered an error. Please make sure the API server is running and try again.",
          isStreaming: false,
        };
        return newMessages;
      });
    } finally {
      setIsLoading(false);
      setCurrentToolCall(null);
    }
  };

  const handleSuggestionClick = (question: string) => {
    handleSend(question);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header Actions */}
      {messages.length > 0 && (
        <div className="flex justify-end px-4 pt-4 pb-0">
          <button
            onClick={handleClearChat}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-zinc-400 bg-zinc-800/50 hover:bg-zinc-800 hover:text-emerald-400 rounded-full transition-colors"
            title="Start a new conversation"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            New Chat
          </button>
        </div>
      )}

      {/* Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-12">
            <div className="rounded-full bg-emerald-500/10 p-4 mb-4">
              <Bot className="h-12 w-12 text-emerald-500" />
            </div>
            <h2 className="text-2xl font-semibold mb-2">Nifty Sage</h2>
            <p className="text-zinc-400 text-center max-w-md mb-8">
              Your AI-powered Indian stock market analyst. Ask me about stocks,
              sectors, trends, or get investment insights.
            </p>
            <SuggestedQuestions
              suggestions={suggestions}
              onSelect={handleSuggestionClick}
            />
          </div>
        ) : (
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}

            {/* Tool call indicator */}
            {currentToolCall && (
              <div className="flex items-center gap-2 text-sm text-zinc-400 pl-12">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Fetching {currentToolCall}...</span>
              </div>
            )}
          </div>
        )}
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-zinc-800 p-4">
        <div className="max-w-3xl mx-auto">
          <ChatInput onSend={handleSend} disabled={isLoading} />
        </div>
      </div>
    </div>
  );
}
