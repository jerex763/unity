import { useRef, type PropsWithChildren } from 'react'

import {
  DirectoryViewContext,
  emptyDirectoryView,
} from './directory-view-state'

// Memory only: do not persist names/search text in URLs or browser storage.
export function DirectoryViewStateProvider({ children }: PropsWithChildren) {
  const state = useRef({ ...emptyDirectoryView })
  return (
    <DirectoryViewContext.Provider value={state}>
      {children}
    </DirectoryViewContext.Provider>
  )
}
