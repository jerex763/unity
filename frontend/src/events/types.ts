export type EventGroupChoice = {
  id: number
  name: string
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
  registered_count: number
  waitlisted_count: number
  created_by: string
  created_at: string
  updated_at: string
}
