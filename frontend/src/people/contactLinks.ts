export function emailAppHref(email: string) {
  const separator = email.lastIndexOf('@')
  if (separator < 0) return `mailto:${encodeURIComponent(email)}`
  const localPart = email.slice(0, separator)
  const domain = email.slice(separator + 1)
  return `mailto:${encodeURIComponent(localPart)}@${domain}`
}

export function whatsappHref(phone: string) {
  if (
    [...phone].some((character) => {
      const codePoint = character.codePointAt(0) ?? 0
      return codePoint <= 0x1f || codePoint === 0x7f
    })
  )
    return null
  const trimmed = phone.trim()
  const internationalNumber = trimmed.startsWith('+')
    ? trimmed.slice(1)
    : trimmed.startsWith('00')
      ? trimmed.slice(2)
      : null
  if (internationalNumber === null) return null
  if (!/^[0-9 ()-]+$/.test(internationalNumber)) return null
  const digits = internationalNumber.replace(/[ ()-]/g, '')
  if (!/^[1-9][0-9]{0,14}$/.test(digits)) return null
  return `https://wa.me/${digits}`
}
