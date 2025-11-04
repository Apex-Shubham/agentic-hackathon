# UI (React) — Quick Start

This is a minimal React (Vite) single-page app that talks to the Flask API at `/api/*`.

Local development

1. Install Node.js (16+ recommended).
2. From the `ui/` folder install deps and run the dev server:

```bash
cd ui
npm ci
npm run dev
```

3. Open the app in your browser:

```
http://localhost:3000
```

Vite is configured to proxy `/api` requests to `http://localhost:5001` so the Flask backend can run on port 5001 locally.

Production build

- To build a production bundle:

```bash
cd ui
npm run build
```

- The build output will be in `ui/dist`.

Deployment options

- Single-image deploy (simple): copy `ui/dist` into the Flask `static/` folder (or set Flask to serve the static `dist/index.html`). You can do this in a multi-stage Docker build.
- Decoupled deploy (recommended for production): deploy the built static files to Vercel/Netlify/S3+CloudFront and host the Flask API separately. If you host separately, enable CORS in Flask for your frontend origin.

Notes

- The example `App.jsx` polls `GET /api/portfolio` every 5 seconds and renders the JSON response. Use it as a starting point to replace the current Jinja template frontend.
- If you prefer a different port or API host in dev, update `vite.config.js` proxy target.
