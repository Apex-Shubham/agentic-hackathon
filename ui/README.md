# Apex Trading Dashboard (React + TypeScript)

A modern, type-safe dashboard built with React, TypeScript, and React Query.

## Features

- **TypeScript**: Full type safety and IDE support
- **React Query**: Efficient data fetching with caching and auto-refresh
- **Zod Validation**: Runtime API response validation
- **Error Handling**: Comprehensive error boundaries and retry logic
- **Loading States**: Smooth loading skeletons
- **Real-time Updates**: Auto-polling every 5 seconds

## Quick Start

### Prerequisites

- Node.js 16+ recommended
- Python 3.x for the Flask backend

### Local Development

1. Install dependencies:

```bash
cd ui
npm ci  # or npm install
```

2. Start the development server:

```bash
npm run dev
```

3. Open in your browser:
```
http://localhost:3000
```

The Vite dev server will proxy `/api/*` requests to `http://localhost:5001` where the Flask backend should be running.

### Production Build

Build the frontend:

```bash
cd ui
npm run build
```

The production-ready files will be in `ui/dist/`.

## Project Structure

- `src/types/` - TypeScript interfaces and Zod schemas
- `src/api/` - API client and React Query hooks
- `src/components/` - React components
- `src/App.css` - Global styles

## API Integration

The dashboard uses React Query to fetch data from these endpoints:

- `GET /api/portfolio` - Current portfolio status
- More endpoints coming soon...

## Development Notes

### Type Safety

- Use the `PortfolioResponse` type for API responses
- API responses are validated at runtime with Zod schemas
- Components are fully typed with TypeScript

### State Management

- React Query handles all API state
- Automatic background refreshing every 5s
- Built-in caching and stale-while-revalidate

### Error Handling

- Global error boundary catches render errors
- API errors are caught and displayed with retry options
- Network errors show user-friendly messages

### Styling

- CSS custom properties for theming
- Responsive grid layouts
- Loading skeletons during data fetches
- Animations for status changes

## Configuration

### Development

- Edit `vite.config.ts` to change the API proxy settings
- Environment variables:
  - `VITE_API_URL`: Override the API base URL

### Production

When deploying to production, you can:

1. Build and serve with Flask:
   - Run `npm run build`
   - Copy `dist/` to Flask's static folder
   - Configure Flask to serve the SPA

2. Deploy separately:
   - Host the React build on a CDN
   - Deploy the Flask API separately
   - Enable CORS in Flask for your frontend origin

## Contributing

1. Create a feature branch
2. Make your changes
3. Run `npm run typecheck` to verify types
4. Submit a pull request