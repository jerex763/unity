# Unity frontend

React, TypeScript and Vite provide the responsive web app. The production build
includes a web app manifest and service worker so supported browsers can install it
as a PWA.

## Local development

Use Node.js 22 or newer. With the backend running on port 8000:

```bash
npm ci
cp .env.example .env
npm run dev
```

Vite serves the app at <http://localhost:5173> and proxies `/api` requests to the
local Django server. Set `VITE_API_BASE_URL` when the API is hosted elsewhere.

## Quality checks

```bash
npm run lint
npm run format:check
npm test
npm run build
```

Visible copy belongs in `src/i18n.ts`; English is the initial language and further
translations can be added without changing components.
