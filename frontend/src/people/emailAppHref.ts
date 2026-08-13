export function emailAppHref(email: string) {
  const separator = email.lastIndexOf('@')
  if (separator < 0) return `mailto:${encodeURIComponent(email)}`
  const localPart = email.slice(0, separator)
  const domain = email.slice(separator + 1)
  return `mailto:${encodeURIComponent(localPart)}@${domain}`
}
