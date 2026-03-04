"use client";

import { useState } from "react";
import Link from "next/link";
import { useCourseGroups, useCreateGroup, useJoinGroup, useLeaveGroup, useGroupMembers, useMyGroups } from "@/hooks/use-study-groups";
import { getErrorMessage } from "@/lib/errors";
import type { StudyGroupWithCount } from "@/lib/api";

interface StudyGroupsSectionProps {
  courseId: string;
  token: string | null;
  userId: string | null;
}

function GroupMembersList({ groupId }: { groupId: string }) {
  const { data, isLoading } = useGroupMembers(groupId);

  if (isLoading) {
    return <p className="text-sm text-gray-400">Загрузка участников...</p>;
  }

  if (!data || data.items.length === 0) {
    return <p className="text-sm text-gray-400">Нет участников</p>;
  }

  return (
    <ul className="mt-2 space-y-1">
      {data.items.map((member) => (
        <li key={member.id} className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-xs font-medium text-blue-700">
            {member.user_id.slice(0, 2).toUpperCase()}
          </span>
          <Link
            href={`/users/${member.user_id}`}
            className="text-sm text-blue-600 hover:underline"
          >
            {member.user_id.slice(0, 8)}...
          </Link>
        </li>
      ))}
    </ul>
  );
}

function GroupCard({
  group,
  token,
  userId,
  isMember,
}: {
  group: StudyGroupWithCount;
  token: string | null;
  userId: string | null;
  isMember: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const joinGroup = useJoinGroup(token);
  const leaveGroup = useLeaveGroup(token);

  const isFull = group.member_count >= group.max_members;

  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-left font-medium text-gray-800 hover:text-blue-600"
          >
            {group.name}
          </button>
          {group.description && (
            <p className="mt-1 text-sm text-gray-500">{group.description}</p>
          )}
          <p className="mt-1 text-xs text-gray-400">
            {group.member_count} / {group.max_members} участников
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {isMember ? (
            <>
              <span className="rounded bg-green-100 px-2 py-1 text-xs text-green-700">
                Вы участник
              </span>
              <button
                onClick={() => leaveGroup.mutate(group.id)}
                disabled={leaveGroup.isPending}
                className="rounded border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                {leaveGroup.isPending ? "..." : "Выйти"}
              </button>
            </>
          ) : token && userId ? (
            <button
              onClick={() => joinGroup.mutate(group.id)}
              disabled={joinGroup.isPending || isFull}
              className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {joinGroup.isPending ? "..." : isFull ? "Группа полна" : "Вступить"}
            </button>
          ) : null}
        </div>
      </div>

      {(joinGroup.error || leaveGroup.error) && (
        <p className="mt-2 text-sm text-red-500">
          {getErrorMessage(joinGroup.error || leaveGroup.error)}
        </p>
      )}

      {expanded && (
        <div className="mt-3 border-t border-gray-200 pt-3">
          <h4 className="mb-1 text-sm font-medium text-gray-600">Участники</h4>
          <GroupMembersList groupId={group.id} />
        </div>
      )}
    </div>
  );
}

export function StudyGroupsSection({ courseId, token, userId }: StudyGroupsSectionProps) {
  const { data: groupsData, isLoading } = useCourseGroups(courseId);
  const { data: myGroups } = useMyGroups(token);
  const createGroup = useCreateGroup(token);

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const myGroupIds = new Set(myGroups?.map((g) => g.id) ?? []);

  function handleCreate() {
    if (!name.trim()) return;
    createGroup.mutate(
      { course_id: courseId, name: name.trim(), description: description.trim() || undefined },
      {
        onSuccess: () => {
          setName("");
          setDescription("");
          setShowForm(false);
        },
      },
    );
  }

  const groups = groupsData?.items ?? [];

  return (
    <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-bold">Учебные группы</h2>
        {token && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded border border-blue-200 px-3 py-1 text-sm text-blue-600 hover:bg-blue-50"
          >
            {showForm ? "Отмена" : "Создать группу"}
          </button>
        )}
      </div>

      {showForm && (
        <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50 p-4">
          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Название группы
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value.slice(0, 100))}
              placeholder="Например: Группа взаимопомощи"
              className="w-full rounded border border-gray-200 px-3 py-2 text-sm"
              maxLength={100}
            />
            <p className="mt-1 text-xs text-gray-400">{name.length}/100</p>
          </div>
          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Описание (необязательно)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Чем будет заниматься группа?"
              className="w-full rounded border border-gray-200 px-3 py-2 text-sm"
              rows={2}
            />
          </div>
          {createGroup.error && (
            <p className="mb-2 text-sm text-red-500">
              {getErrorMessage(createGroup.error)}
            </p>
          )}
          <button
            onClick={handleCreate}
            disabled={createGroup.isPending || !name.trim()}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {createGroup.isPending ? "Создание..." : "Создать"}
          </button>
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-400">Загрузка групп...</p>
      ) : groups.length === 0 ? (
        <p className="text-sm text-gray-400">
          Пока нет учебных групп. Создайте первую!
        </p>
      ) : (
        <div className="space-y-3">
          {groups.map((group) => (
            <GroupCard
              key={group.id}
              group={group}
              token={token}
              userId={userId}
              isMember={myGroupIds.has(group.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
