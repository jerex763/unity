import { createContext, useContext, useRef, type RefObject } from 'react'

export type DirectoryViewState = {
  search: string
  membershipStatus: string
  groupId: string
  university: string
  scrollY: number
  focusPersonId: number | null
}

export const emptyDirectoryView: DirectoryViewState = {
  search: '',
  membershipStatus: '',
  groupId: '',
  university: '',
  scrollY: 0,
  focusPersonId: null,
}

export const DirectoryViewContext = createContext<
  RefObject<DirectoryViewState> | undefined
>(undefined)

export function useDirectoryViewState() {
  const context = useContext(DirectoryViewContext)
  const fallback = useRef({ ...emptyDirectoryView })
  return context ?? fallback
}
