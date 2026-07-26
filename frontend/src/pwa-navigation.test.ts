import { describe, expect, it } from 'vitest'

import { navigationFallbackDenylist } from '../vite.config'

const isDenied = (path: string) =>
  navigationFallbackDenylist.some((pattern) => pattern.test(path))

describe('PWA navigation fallback', () => {
  it.each([
    '/api',
    '/api/',
    '/api/health/',
    '/api?format=json',
    '/admin',
    '/admin/',
    '/admin/login/',
    '/admin?next=/admin/',
    '/static',
    '/static/',
    '/static/admin/css/base.css',
    '/static?asset=base.css',
    '/assets',
    '/assets/',
    '/assets/index.js',
    '/assets?file=index.js',
    '/media',
    '/media/',
    '/media/avatar.jpg',
    '/media?file=avatar.jpg',
    '/sw.js',
    '/sw.js?v=1',
    '/manifest.webmanifest',
    '/manifest.webmanifest?v=1',
    '/unity-icon.svg',
    '/unity-icon.svg?v=1',
  ])('does not serve the SPA shell for %s', (path) => {
    expect(isDenied(path)).toBe(true)
  })

  it.each([
    '/',
    '/people',
    '/events/123',
    '/follow-ups',
    '/apiary',
    '/administrator',
    '/statics',
    '/asset-store',
    '/media-library',
    '/sw.jsx',
    '/manifest.webmanifesto',
    '/unity-icon.svgz',
  ])('keeps the SPA fallback for %s', (path) => {
    expect(isDenied(path)).toBe(false)
  })
})
