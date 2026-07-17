export type PersonGroup = {
  id: number
  name: string
}

export type DirectoryPerson = {
  id: number
  full_name: string
  preferred_name: string | null
  membership_status: 'visitor' | 'newcomer' | 'regular' | 'member' | 'inactive'
  email: string | null
  phone: string | null
  photo_url: string | null
  suburb: string | null
  university: string | null
  groups: PersonGroup[]
}
