export type EventGroupChoice = {
  id: number
  name: string
}

export type EventRegistration = {
  id: number
  person: {
    id: number
    full_name: string
    preferred_name: string | null
  }
  status: 'registered' | 'waitlisted' | 'cancelled' | 'walk_in'
  note: string
  registered_at: string
  checked_in_at: string | null
  checkin_method: 'qr' | 'manual' | null
}

export type CheckInPerson = {
  id: number
  full_name: string
  preferred_name: string | null
  membership_status: 'visitor' | 'newcomer' | 'regular' | 'member' | 'inactive'
  current_registration_status: EventRegistration['status'] | null
  contact_hint: string | null
}

export type ChurchEvent = {
  id: number
  group: number | null
  group_name?: string
  title: string
  description: string
  starts_at: string
  ends_at: string
  location: string
  capacity: number | null
  signup_opens: boolean
  signup_closes_at: string | null
  registration_open: boolean
  places_available: boolean
  my_registration: EventRegistration | null
  public_registration_enabled: boolean
  registered_count: number
  waitlisted_count: number
  created_by: string
  created_at: string
  updated_at: string
}
