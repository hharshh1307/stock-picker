"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";
import type { ChatMessage, ChatStreamEvent, ChatSuggestion } from "@/lib/types";
import { MessageBubble } from "./message-bubble";
import { ChatInput } from "./chat-input";
import { SuggestedQuestions } from "./suggested-questions";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, Loader2 } from "lucide-react";

interface ChatContainerProps {
  suggestions: ChatSuggestion[];
}

export function ChatContainer({ suggestions }: ChatContainerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentToolCall, setCurrentToolCall] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentToolCall]);

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

      for await (const event of api.chat.streamChat(message)) {
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
