import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { studyGroups } from "@/lib/api";

export function useCourseGroups(courseId: string) {
  return useQuery({
    queryKey: ["study-groups", "course", courseId],
    queryFn: () => studyGroups.byCourse(courseId),
  });
}

export function useCreateGroup(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { course_id: string; name: string; description?: string }) =>
      studyGroups.create(token!, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["study-groups", "course", variables.course_id] });
      queryClient.invalidateQueries({ queryKey: ["study-groups", "me"] });
    },
  });
}

export function useJoinGroup(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: string) => studyGroups.join(token!, groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["study-groups"] });
    },
  });
}

export function useLeaveGroup(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: string) => studyGroups.leave(token!, groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["study-groups"] });
    },
  });
}

export function useGroupMembers(groupId: string | null) {
  return useQuery({
    queryKey: ["study-groups", "members", groupId],
    queryFn: () => studyGroups.members(groupId!),
    enabled: !!groupId,
  });
}

export function useMyGroups(token: string | null) {
  return useQuery({
    queryKey: ["study-groups", "me"],
    queryFn: () => studyGroups.me(token!),
    enabled: !!token,
  });
}
