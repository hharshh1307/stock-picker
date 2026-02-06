"use client";

import { Button } from "@/components/ui/button";
import { MessageCircle } from "lucide-react";
import type { ChatSuggestion } from "@/lib/types";

interface SuggestedQuestionsProps {
  suggestions: ChatSuggestion[];
  onSelect: (question: string) => void;
}

export function SuggestedQuestions({ suggestions, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="w-full max-w-2xl">
      <h3 className="text-sm font-medium text-zinc-400 mb-3 flex items-center gap-2">
        <MessageCircle className="h-4 w-4" />
        Suggested questions
      </h3>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion, index) => (
          <Button
            key={index}
            variant="outline"
            size="sm"
            onClick={() => onSelect(suggestion.question)}
            className="bg-zinc-800/50 border-zinc-700 hover:bg-zinc-800 hover:border-zinc-600 text-sm"
          >
            {suggestion.question}
          </Button>
        ))}
      </div>
    </div>
  );
}
