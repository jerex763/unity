export type FollowUpDueStatus = 'none' | 'overdue' | 'today' | 'future'

export function classifyFollowUpDueDate(
  dueAt: string | null,
  today: string,
): FollowUpDueStatus {
  if (!dueAt) return 'none'
  if (dueAt < today) return 'overdue'
  if (dueAt === today) return 'today'
  return 'future'
}
