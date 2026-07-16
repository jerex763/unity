const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

type ErrorPayload = {
  detail?: string
  [key: string]: unknown
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly payload: ErrorPayload,
  ) {
    super(payload.detail ?? `API request failed with status ${status}`)
    this.name = 'ApiError'
  }
}

function getCookie(name: string): string | undefined {
  return document.cookie
    .split(';')
    .map((value) => value.trim())
    .find((value) => value.startsWith(`${name}=`))
    ?.slice(name.length + 1)
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')

  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) headers.set('X-CSRFToken', decodeURIComponent(csrfToken))
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers,
  })

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ErrorPayload
    throw new ApiError(response.status, payload)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
