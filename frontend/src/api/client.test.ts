import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiRequest } from './client'

afterEach(() => {
  document.cookie = 'csrftoken=; Max-Age=0; Path=/'
  vi.unstubAllGlobals()
})

describe('apiRequest', () => {
  it('sends session credentials and CSRF protection for writes', async () => {
    document.cookie = 'csrftoken=token%20value; Path=/'
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/auth/logout/', { method: 'POST' })

    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(request.credentials).toBe('include')
    expect(new Headers(request.headers).get('X-CSRFToken')).toBe('token value')
  })

  it('surfaces API error details', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Not allowed' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(apiRequest('/private/')).rejects.toEqual(
      expect.objectContaining({
        status: 403,
        message: 'Not allowed',
      }),
    )
  })
})
