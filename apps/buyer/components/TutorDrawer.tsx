"use client";

import { useState, useRef, useEffect } from "react";
import { useTutorChat, useTutorFeedback } from "@/hooks/use-tutor";
import { getErrorMessage } from "@/lib/errors";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

interface TutorDrawerProps {
  open: boolean;
  onClose: () => void;
  token: string;
  lessonId: string;
  lessonContent: string;
}

export function TutorDrawer({
  open,
  onClose,
  token,
  lessonId,
  lessonContent,
}: TutorDrawerProps) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [creditsRemaining, setCreditsRemaining] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const chatMutation = useTutorChat(token);
  const feedbackMutation = useTutorFeedback(token);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend() {
    const text = input.trim();
    if (!text || chatMutation.isPending) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");

    chatMutation.mutate(
      {
        lesson_id: lessonId,
        message: text,
        lesson_content: lessonContent,
        session_id: sessionId,
      },
      {
        onSuccess: (data) => {
          setSessionId(data.session_id);
          setCreditsRemaining(data.credits_remaining);
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: data.message },
          ]);
        },
        onError: (err) => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `Ошибка: ${getErrorMessage(err, "Попробуйте позже")}`,
            },
          ]);
        },
      }
    );
  }

  function handleFeedback(msgIndex: number, rating: number) {
    if (!sessionId) return;
    feedbackMutation.mutate({
      session_id: sessionId,
      message_index: msgIndex,
      rating,
    });
  }

  if (!open) return null;

  return (
    <div role="dialog" aria-modal="true" aria-label="AI-тьютор" className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-gray-200 bg-white shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">AI-тьютор</h3>
          {creditsRemaining !== null && (
            <p className="text-xs text-gray-500">
              Осталось вопросов: {creditsRemaining}
            </p>
          )}
        </div>
        <button
          onClick={onClose}
          aria-label="Закрыть"
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          &#10005;
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="text-center text-sm text-gray-400">
            <p className="mb-2">Задайте вопрос по уроку.</p>
            <p>AI-тьютор поможет разобраться через наводящие вопросы.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.role === "assistant" && sessionId && (
                <div className="mt-1 flex gap-1">
                  <button
                    onClick={() => handleFeedback(i, 1)}
                    className="text-xs text-gray-400 hover:text-green-600"
                    title="Полезно"
                    aria-label="Полезно"
                  >
                    &#9650;
                  </button>
                  <button
                    onClick={() => handleFeedback(i, -1)}
                    className="text-xs text-gray-400 hover:text-red-600"
                    title="Не полезно"
                    aria-label="Не полезно"
                  >
                    &#9660;
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        {chatMutation.isPending && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-500">
              Думаю...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Задайте вопрос..."
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            disabled={chatMutation.isPending}
          />
          <button
            type="submit"
            disabled={!input.trim() || chatMutation.isPending}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            &#10148;
          </button>
        </form>
      </div>
    </div>
  );
}
