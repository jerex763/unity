import { useEffect, useRef, type RefObject } from 'react'

const focusableSelector = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function focusableElements(container: HTMLElement) {
  return Array.from(
    container.querySelectorAll<HTMLElement>(focusableSelector),
  ).filter((element) => element.getAttribute('aria-hidden') !== 'true')
}

function inertBackground(dialog: HTMLElement) {
  const changed: HTMLElement[] = []
  let branch: HTMLElement = dialog
  while (branch.parentElement && branch.parentElement !== document.body) {
    const parent = branch.parentElement
    for (const sibling of Array.from(parent.children)) {
      if (
        sibling !== branch &&
        sibling instanceof HTMLElement &&
        !sibling.inert
      ) {
        sibling.inert = true
        changed.push(sibling)
      }
    }
    branch = parent
  }
  return () => {
    for (const element of changed) element.inert = false
  }
}

export function useModalDialog<ElementType extends HTMLElement>(
  open: boolean,
  onClose: () => void,
  initialFocusRef?: RefObject<HTMLElement | null>,
) {
  const dialogRef = useRef<ElementType>(null)
  const closeRef = useRef(onClose)

  useEffect(() => {
    closeRef.current = onClose
  }, [onClose])

  useEffect(() => {
    if (!open || !dialogRef.current) return
    const dialog = dialogRef.current
    const returnFocus =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null
    const restoreBackground = inertBackground(dialog)

    const focusInitial = () => {
      const target =
        initialFocusRef?.current ?? focusableElements(dialog).at(0) ?? dialog
      target.focus({ preventScroll: true })
    }
    focusInitial()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeRef.current()
        return
      }
      if (event.key !== 'Tab') return
      const focusable = focusableElements(dialog)
      if (!focusable.length) {
        event.preventDefault()
        dialog.focus({ preventScroll: true })
        return
      }
      const first = focusable[0]
      const last = focusable.at(-1) ?? first
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      } else if (!dialog.contains(document.activeElement)) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      restoreBackground()
      if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true })
    }
  }, [initialFocusRef, open])

  return dialogRef
}
