import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { messaging } from "@/lib/api";

export function useConversations(token: string | null) {
  return useQuery({
    queryKey: ["conversations", "me"],
    queryFn: () => messaging.getConversations(token!, { limit: 50 }),
    enabled: !!token,
    refetchInterval: 10000,
  });
}

export function useUnreadCount(token: string | null) {
  const { data } = useConversations(token);
  if (!data) return 0;
  return data.items.reduce((sum, c) => sum + c.unread_count, 0);
}

export function useMessages(token: string | null, conversationId: string | null) {
  return useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => messaging.getMessages(token!, conversationId!, { limit: 100 }),
    enabled: !!token && !!conversationId,
    refetchInterval: 10000,
  });
}

export function useSendMessage(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { recipient_id: string; content: string }) =>
      messaging.sendMessage(token!, data),
    onSuccess: (msg) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({ queryKey: ["messages", msg.conversation_id] });
    },
  });
}

export function useMarkMessageRead(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (messageId: string) => messaging.markRead(token!, messageId),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
