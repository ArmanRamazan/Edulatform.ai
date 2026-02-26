import { useMutation } from "@tanstack/react-query";
import { ai as aiApi } from "@/lib/api";

export function useTutorChat(token: string | null) {
  return useMutation({
    mutationFn: (data: {
      lesson_id: string;
      message: string;
      lesson_content: string;
      session_id?: string;
    }) => aiApi.tutorChat(token!, data),
  });
}

export function useTutorFeedback(token: string | null) {
  return useMutation({
    mutationFn: (data: {
      session_id: string;
      message_index: number;
      rating: number;
    }) => aiApi.tutorFeedback(token!, data),
  });
}
