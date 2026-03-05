"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/Header";
import { useAuth } from "@/hooks/use-auth";
import {
  useConversations,
  useMessages,
  useSendMessage,
  useMarkMessageRead,
} from "@/hooks/use-messages";
import type { ConversationPreview, DirectMessage } from "@/lib/api";

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (isToday) {
    return d.toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" });
  }
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
  return d.toLocaleDateString("ru", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
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
      className={`w-full border-b border-gray-100 px-4 py-3 text-left transition-colors hover:bg-gray-50 ${
        isActive ? "bg-blue-50" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-gray-900">
            {conv.other_user_id.slice(0, 8)}...
          </p>
          <p className="mt-0.5 truncate text-xs text-gray-500">
            {conv.last_message_content}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="whitespace-nowrap text-[10px] text-gray-400">
            {formatTime(conv.last_message_at)}
          </span>
          {conv.unread_count > 0 && (
            <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-blue-600 px-1.5 text-[10px] font-bold text-white">
              {conv.unread_count}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

function MessageBubble({
  msg,
  isMine,
}: {
  msg: DirectMessage;
  isMine: boolean;
}) {
  return (
    <div className={`flex ${isMine ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[70%] rounded-2xl px-4 py-2 ${
          isMine
            ? "rounded-br-md bg-blue-600 text-white"
            : "rounded-bl-md bg-gray-100 text-gray-900"
        }`}
      >
        <p className="whitespace-pre-wrap break-words text-sm">{msg.content}</p>
        <p
          className={`mt-1 text-right text-[10px] ${
            isMine ? "text-blue-200" : "text-gray-400"
          }`}
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
  const { data: conversations, isLoading: convsLoading } =
    useConversations(token);
  const sendMessage = useSendMessage(token);
  const markRead = useMarkMessageRead(token);

  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [newRecipientId, setNewRecipientId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(0);

  // If ?to= param is present, find or create conversation
  useEffect(() => {
    if (!toUserId || !conversations) return;
    const existing = conversations.items.find(
      (c) => c.other_user_id === toUserId,
    );
    if (existing) {
      setSelectedConvId(existing.conversation_id);
      setNewRecipientId(null);
    } else {
      setSelectedConvId(null);
      setNewRecipientId(toUserId);
    }
  }, [toUserId, conversations]);

  const { data: messagesData } = useMessages(token, selectedConvId);

  // Mark unread messages as read when viewing a conversation
  useEffect(() => {
    if (!messagesData || !user) return;
    const unread = messagesData.items.filter(
      (m) => !m.is_read && m.sender_id !== user.id,
    );
    for (const m of unread) {
      markRead.mutate(m.id);
    }
  }, [messagesData, user]); // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom when messages change
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
    const conv = conversations.items.find(
      (c) => c.conversation_id === selectedConvId,
    );
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
      <>
        <Header />
        <main className="mx-auto max-w-6xl px-4 py-6">
          <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
        </main>
      </>
    );
  }

  if (!user || !token) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-6xl px-4 py-6">
          <p className="text-gray-500">
            Войдите в аккаунт, чтобы просматривать сообщения.
          </p>
        </main>
      </>
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
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-6">
        <h1 className="mb-4 text-2xl font-bold">Сообщения</h1>
        <div className="flex h-[calc(100vh-200px)] min-h-[500px] overflow-hidden rounded-lg border border-gray-200 bg-white">
          {/* Left panel — conversation list */}
          <div className="w-1/3 border-r border-gray-200 overflow-y-auto">
            {convsLoading ? (
              <div className="space-y-3 p-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 animate-pulse rounded bg-gray-100" />
                ))}
              </div>
            ) : !conversations?.items.length && !newRecipientId ? (
              <div className="p-6 text-center text-sm text-gray-400">
                Нет сообщений
              </div>
            ) : (
              <>
                {newRecipientId &&
                  !conversations?.items.find(
                    (c) => c.other_user_id === newRecipientId,
                  ) && (
                    <button
                      className="w-full border-b border-gray-100 bg-blue-50 px-4 py-3 text-left"
                    >
                      <p className="text-sm font-medium text-blue-700">
                        Новый диалог
                      </p>
                      <p className="mt-0.5 text-xs text-blue-500">
                        {newRecipientId.slice(0, 8)}...
                      </p>
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
          <div className="flex w-2/3 flex-col">
            {!isActiveChat ? (
              <div className="flex flex-1 items-center justify-center p-6">
                <p className="text-center text-sm text-gray-400">
                  Нет сообщений. Начните диалог с преподавателем на странице его
                  профиля.
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
                          <div className="h-px flex-1 bg-gray-200" />
                          <span className="text-xs text-gray-400">
                            {formatDateSeparator(group.date)}
                          </span>
                          <div className="h-px flex-1 bg-gray-200" />
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
                <div className="border-t border-gray-200 p-3">
                  <div className="flex gap-2">
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value.slice(0, 2000))}
                      onKeyDown={handleKeyDown}
                      placeholder="Введите сообщение..."
                      rows={1}
                      className="flex-1 resize-none rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
                    />
                    <button
                      onClick={handleSend}
                      disabled={
                        !input.trim() ||
                        input.trim().length > 2000 ||
                        sendMessage.isPending
                      }
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {sendMessage.isPending ? "..." : "Отправить"}
                    </button>
                  </div>
                  {input.length > 1900 && (
                    <p className="mt-1 text-xs text-gray-400">
                      {input.length}/2000
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </>
  );
}

export default function MessagesPage() {
  return (
    <Suspense
      fallback={
        <>
          <Header />
          <main className="mx-auto max-w-6xl px-4 py-6">
            <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
          </main>
        </>
      }
    >
      <MessagesContent />
    </Suspense>
  );
}
