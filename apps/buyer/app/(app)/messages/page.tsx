"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { SendHorizontal, MessageSquare } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import {
  useConversations,
  useMessages,
  useSendMessage,
  useMarkMessageRead,
} from "@/hooks/use-messages";
import type { ConversationPreview, DirectMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (isToday) return d.toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("ru", { day: "numeric", month: "short" });
}

function formatDateSeparator(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (isToday) return "Сегодня";
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday =
    d.getFullYear() === yesterday.getFullYear() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getDate() === yesterday.getDate();
  if (isYesterday) return "Вчера";
  return d.toLocaleDateString("ru", { day: "numeric", month: "long", year: "numeric" });
}

function getDateKey(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function ConversationItem({
  conv,
  isActive,
  onClick,
}: {
  conv: ConversationPreview;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full border-b border-border px-4 py-3 text-left transition-colors hover:bg-muted/30",
        isActive && "bg-primary/8 border-l-2 border-l-primary",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {conv.other_user_id.slice(0, 8)}...
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {conv.last_message_content}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="whitespace-nowrap text-[10px] text-muted-foreground/50">
            {formatTime(conv.last_message_at)}
          </span>
          {conv.unread_count > 0 && (
            <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary px-1.5 text-[10px] font-bold text-primary-foreground">
              {conv.unread_count}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

function MessageBubble({ msg, isMine }: { msg: DirectMessage; isMine: boolean }) {
  return (
    <div className={`flex ${isMine ? "justify-end" : "justify-start"}`}>
      <div
        className={cn(
          "max-w-[70%] rounded-2xl px-4 py-2",
          isMine
            ? "rounded-br-md bg-primary text-primary-foreground"
            : "rounded-bl-md border border-border bg-card text-foreground",
        )}
      >
        <p className="whitespace-pre-wrap break-words text-sm">{msg.content}</p>
        <p
          className={cn(
            "mt-1 text-right text-[10px]",
            isMine ? "text-primary-foreground/60" : "text-muted-foreground/50",
          )}
        >
          {new Date(msg.created_at).toLocaleTimeString("ru", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}

function MessagesContent() {
  const searchParams = useSearchParams();
  const toUserId = searchParams.get("to");

  const { user, token, loading: authLoading } = useAuth();
  const { data: conversations, isLoading: convsLoading } = useConversations(token);
  const sendMessage = useSendMessage(token);
  const markRead = useMarkMessageRead(token);

  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [newRecipientId, setNewRecipientId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(0);

  useEffect(() => {
    if (!toUserId || !conversations) return;
    const existing = conversations.items.find((c) => c.other_user_id === toUserId);
    if (existing) {
      setSelectedConvId(existing.conversation_id);
      setNewRecipientId(null);
    } else {
      setSelectedConvId(null);
      setNewRecipientId(toUserId);
    }
  }, [toUserId, conversations]);

  const { data: messagesData } = useMessages(token, selectedConvId);

  useEffect(() => {
    if (!messagesData || !user) return;
    const unread = messagesData.items.filter((m) => !m.is_read && m.sender_id !== user.id);
    for (const m of unread) markRead.mutate(m.id);
  }, [messagesData, user]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const count = messagesData?.items.length ?? 0;
    if (count !== prevMessageCountRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      prevMessageCountRef.current = count;
    }
  }, [messagesData]);

  function handleSend() {
    const content = input.trim();
    if (!content || content.length > 2000) return;
    const recipientId = newRecipientId ?? getRecipientFromConv();
    if (!recipientId) return;
    sendMessage.mutate(
      { recipient_id: recipientId, content },
      {
        onSuccess: (msg) => {
          setInput("");
          if (newRecipientId) {
            setSelectedConvId(msg.conversation_id);
            setNewRecipientId(null);
          }
        },
      },
    );
  }

  function getRecipientFromConv(): string | null {
    if (!selectedConvId || !conversations) return null;
    const conv = conversations.items.find((c) => c.conversation_id === selectedConvId);
    return conv?.other_user_id ?? null;
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function selectConversation(conv: ConversationPreview) {
    setSelectedConvId(conv.conversation_id);
    setNewRecipientId(null);
  }

  if (authLoading) {
    return (
      <div className="h-[calc(100vh-8rem)] rounded-xl border border-border bg-card">
        <div className="flex h-full items-center justify-center">
          <div className="relative h-6 w-32 overflow-hidden rounded bg-secondary">
            <div className="absolute inset-0 animate-shimmer" />
          </div>
        </div>
      </div>
    );
  }

  if (!user || !token) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <MessageSquare
          className="h-10 w-10 text-muted-foreground/30"
          aria-hidden="true"
          strokeWidth={1.5}
        />
        <p className="text-sm text-muted-foreground">
          Войдите в аккаунт, чтобы просматривать сообщения.
        </p>
      </div>
    );
  }

  const messages = messagesData?.items ?? [];
  const isActiveChat = selectedConvId || newRecipientId;

  // Group messages by date
  const groupedMessages: { date: string; messages: DirectMessage[] }[] = [];
  let lastDateKey = "";
  for (const msg of messages) {
    const dk = getDateKey(msg.created_at);
    if (dk !== lastDateKey) {
      groupedMessages.push({ date: msg.created_at, messages: [msg] });
      lastDateKey = dk;
    } else {
      groupedMessages[groupedMessages.length - 1].messages.push(msg);
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] min-h-[500px] overflow-hidden rounded-xl border border-border">
      {/* Left panel — conversation list */}
      <div className="w-1/3 overflow-y-auto border-r border-border bg-card/50">
        <div className="border-b border-border px-4 py-3">
          <h1 className="text-base font-semibold text-foreground">Сообщения</h1>
        </div>
        {convsLoading ? (
          <div className="space-y-2 p-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="relative h-14 overflow-hidden rounded-lg bg-secondary">
                <div className="absolute inset-0 animate-shimmer" />
              </div>
            ))}
          </div>
        ) : !conversations?.items.length && !newRecipientId ? (
          <div className="flex flex-col items-center gap-2 p-8 text-center">
            <MessageSquare
              className="h-8 w-8 text-muted-foreground/30"
              aria-hidden="true"
              strokeWidth={1.5}
            />
            <p className="text-xs text-muted-foreground">Нет сообщений</p>
          </div>
        ) : (
          <>
            {newRecipientId &&
              !conversations?.items.find((c) => c.other_user_id === newRecipientId) && (
                <button className="w-full border-b border-border bg-primary/8 px-4 py-3 text-left">
                  <p className="text-sm font-medium text-primary">Новый диалог</p>
                  <p className="mt-0.5 text-xs text-primary/60">{newRecipientId.slice(0, 8)}...</p>
                </button>
              )}
            {conversations?.items.map((conv) => (
              <ConversationItem
                key={conv.conversation_id}
                conv={conv}
                isActive={selectedConvId === conv.conversation_id}
                onClick={() => selectConversation(conv)}
              />
            ))}
          </>
        )}
      </div>

      {/* Right panel — messages */}
      <div className="flex w-2/3 flex-col bg-background">
        {!isActiveChat ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
            <MessageSquare
              className="h-10 w-10 text-muted-foreground/20"
              aria-hidden="true"
              strokeWidth={1.5}
            />
            <p className="text-sm text-muted-foreground">
              Нет сообщений. Начните диалог с участником на странице его профиля.
            </p>
          </div>
        ) : (
          <>
            {/* Messages list */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-3">
                {groupedMessages.map((group) => (
                  <div key={group.date}>
                    <div className="my-3 flex items-center gap-3">
                      <div className="h-px flex-1 bg-border" />
                      <span className="text-xs text-muted-foreground/50">
                        {formatDateSeparator(group.date)}
                      </span>
                      <div className="h-px flex-1 bg-border" />
                    </div>
                    <div className="space-y-2">
                      {group.messages.map((msg) => (
                        <MessageBubble
                          key={msg.id}
                          msg={msg}
                          isMine={msg.sender_id === user.id}
                        />
                      ))}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input */}
            <div className="border-t border-border p-3">
              <div className="flex items-end gap-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value.slice(0, 2000))}
                  onKeyDown={handleKeyDown}
                  placeholder="Введите сообщение... (Enter — отправить, Shift+Enter — новая строка)"
                  rows={1}
                  aria-label="Написать сообщение"
                  className={cn(
                    "flex-1 resize-none rounded-xl border bg-card px-3 py-2 text-sm text-foreground",
                    "placeholder:text-muted-foreground/50",
                    "border-border focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20",
                    "transition-colors duration-150",
                  )}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || input.trim().length > 2000 || sendMessage.isPending}
                  aria-label="Отправить"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-all hover:bg-primary/90 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <SendHorizontal className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
              {input.length > 1900 && (
                <p className="mt-1 text-right text-xs text-muted-foreground/60">
                  {input.length}/2000
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function MessagesPage() {
  return (
    <Suspense
      fallback={
        <div className="relative h-[calc(100vh-8rem)] overflow-hidden rounded-xl border border-border bg-card">
          <div className="absolute inset-0 animate-shimmer" />
        </div>
      }
    >
      <MessagesContent />
    </Suspense>
  );
}
