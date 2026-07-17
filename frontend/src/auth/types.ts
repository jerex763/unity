export type SessionPayload = {
  user: {
    id: number
    username: string
    first_name: string
    last_name: string
  }
  membership: {
    church_id: number
    church_name: string
    role: 'admin' | 'pastor' | 'leader' | 'member'
    person_id: number | null
  }
}

export type LoginInput = {
  username: string
  password: string
  church_id?: number
}
