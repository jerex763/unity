export type PersonGroup = {
  id: number
  name: string
  role?: 'leader' | 'co_leader' | 'member'
  joined_at?: string
}

export type DirectoryPerson = {
  id: number
  full_name: string
  preferred_name: string | null
  membership_status: 'visitor' | 'newcomer' | 'regular' | 'member' | 'inactive'
  email: string | null
  phone: string | null
  wechat_id: string | null
  photo_url: string | null
  suburb: string | null
  university: string | null
  groups: PersonGroup[]
}

export type PersonEventAttendance = {
  id: number
  title: string
  starts_at: string
  location: string
  checked_in_at: string
}

export type PersonFollowUp = {
  id: number
  source: 'event_visit' | 'friend_invite' | 'walk_in' | 'other'
  status: 'new' | 'assigned' | 'in_progress' | 'connected' | 'closed'
  assigned_to: string | null
  due_at: string | null
  closed_at: string | null
  outcome: string | null
}

export type PersonLink = {
  id: number
  full_name: string
  preferred_name: string | null
  photo_url: string | null
}

export type PersonRelationship = {
  id: number
  kind: 'friend' | 'family' | 'spouse' | 'guardian'
  person: PersonLink
  created_at: string
}

export type ProfilePerson = DirectoryPerson & {
  gender: 'male' | 'female' | 'unspecified'
  date_of_birth: string | null
  has_whatsapp: boolean
  home_country: string | null
  occupation: string | null
  course: string | null
  interests: string[]
  invited_by: number | null
  inviter: PersonLink | null
  invitees: PersonLink[]
  relationships: PersonRelationship[]
  notes?: string
  faith_background?: string | null
  discipleship_stage?:
    | 'pre_evangelism'
    | 'evangelism'
    | 'conversion'
    | 'maturity'
    | 'leadership'
    | null
  events_attended: PersonEventAttendance[]
  follow_up_history?: PersonFollowUp[]
}
