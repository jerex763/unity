export type FollowUpStatus =
  'new' | 'assigned' | 'in_progress' | 'connected' | 'closed'

export type FollowUp = {
  id: number
  person: {
    id: number
    full_name: string
    preferred_name: string | null
    phone: string | null
    email: string | null
  }
  source: 'event_visit' | 'friend_invite' | 'walk_in' | 'other'
  engagement: 'possible' | 'probable' | 'likely'
  status: FollowUpStatus
  assigned_to: number | null
  assigned_to_name: string | null
  due_at: string | null
  closed_at: string | null
  outcome: string | null
  created_at: string
  updated_at: string
}

export type WorkerChoice = {
  id: number
  username: string
  name: string
}
