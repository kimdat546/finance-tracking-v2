# Frontend Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env if your backend is on a different URL
```

### 3. Start Development Server

```bash
npm run dev
```

The app will open at `http://localhost:5173`

## Project Overview

This is a complete React 18 + TypeScript + Vite frontend for the Personal Finance Tracker application.

### What's Included

**Configuration Files:**
- `package.json` - All dependencies and scripts
- `tsconfig.json` - TypeScript configuration with path aliases (@/)
- `vite.config.ts` - Vite bundler configuration
- `tailwind.config.js` - Tailwind CSS theme configuration
- `postcss.config.js` - PostCSS for Tailwind
- `.env.example` - Environment variables template

**Core Application:**
- `src/main.tsx` - React app entry point with QueryClientProvider
- `src/App.tsx` - Main router with all pages
- `src/index.css` - Global Tailwind imports and base styles

**API Integration (`src/api/`):**
- `client.ts` - Axios instance with auth token injection and interceptors
- `transactions.ts` - Transaction API endpoints
- `index.ts` - Exports all API functions

**State Management (`src/store/`):**
- `app-store.ts` - Zustand store for UI state (sidebar, pending count, sync status)

**Custom Hooks (`src/hooks/`):**
- `use-transactions.ts` - React Query hooks for transactions (useTransactions, usePendingTransactions, useUpdateTransaction, etc.)

**Type Definitions (`src/types/`):**
- `index.ts` - All TypeScript interfaces and enums matching backend schemas

**Utility Functions:**
- `src/utils/format.ts` - Vietnamese formatting (VND, dates, relative time)
- `src/utils/cn.ts` - Tailwind class merging utility

**Components (`src/components/`):**

*Layout:*
- `Layout/Sidebar.tsx` - Navigation sidebar with collapsible menu
- `Layout/Header.tsx` - Top header with sync status and user menu
- `Layout/Layout.tsx` - Main layout wrapper

*Reusable UI:*
- `ui/Button.tsx` - Button with variants (primary, secondary, danger, ghost)
- `ui/Card.tsx` - Card with header, title, content, footer components
- `ui/Badge.tsx` - Badge with color variants

**Pages (`src/pages/`):**

1. **Dashboard** - Summary cards, charts, recent transactions
2. **Transactions** - Filterable transaction list with tabs (all/pending)
3. **SplitBills** - Share expenses with friends
4. **Budget** - Set and monitor spending budgets
5. **Goals** - Track savings goals
6. **Debts** - Manage loans and payments
7. **Subscriptions** - Monitor recurring charges
8. **Reports** - Analytics and spending insights
9. **Settings** - Manage accounts, categories, email sync

**Testing:**
- `src/test/setup.ts` - Vitest configuration

**Docker:**
- `Dockerfile` - Multi-stage build for production
- `nginx.conf` - Nginx configuration for SPA

## Key Features

### Authentication
- Auth tokens stored in localStorage
- Automatic token injection in requests
- 401 redirect to login on auth failure

### Data Fetching
- TanStack React Query for caching and sync
- Query invalidation on mutations
- Optimistic updates

### State Management
- Zustand for UI state
- Sidebar open/closed toggle
- Pending review count badge
- Sync status indicator

### Styling
- Tailwind CSS 4 with custom theme
- Dark mode support via `dark:` variants
- Responsive design
- Vietnamese language labels

### API Integration
- Proxy `/api` to backend (localhost:8000)
- Configurable via VITE_API_URL
- Error handling and interceptors

## Development Commands

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Run tests with UI
npm run test:ui

# Lint code
npm run lint

# Format code
npm run format
```

## Available Routes

- `/` - Dashboard
- `/transactions` - Transactions list
- `/split-bills` - Split bills management
- `/budget` - Budget planning
- `/goals` - Financial goals
- `/debts` - Debt tracking
- `/subscriptions` - Subscription management
- `/reports` - Financial reports
- `/settings` - Settings

## API Endpoints Used

The frontend expects these backend endpoints:

**Transactions:**
- `GET /transactions` - List with pagination
- `GET /transactions/{id}` - Single transaction
- `PUT /transactions/{id}` - Update
- `DELETE /transactions/{id}` - Delete
- `GET /transactions/pending` - Pending review
- `PATCH /transactions/{id}/categorize` - Set category
- `POST /transactions/ingest` - Bulk import
- `GET /transactions/statistics` - Stats for date range

## Customization

### Colors
Edit `tailwind.config.js`:
```js
colors: {
  primary: { /* blue shades */ },
  success: { /* green shades */ },
  danger: { /* red shades */ },
  warning: { /* amber shades */ },
}
```

### Language
All Vietnamese labels are hardcoded. Search and replace for other languages:
- Dashboard labels
- Navigation items
- Page titles
- Placeholders

### API URL
Set `VITE_API_URL` in `.env` to point to your backend.

## Production Deployment

### Using Docker

```bash
docker build -t finance-tracker-frontend .
docker run -p 80:80 finance-tracker-frontend
```

### Using Vite Preview

```bash
npm run build
npm run preview
```

### Using a Web Server

```bash
npm run build
# Serve the `dist` folder with your web server
```

The nginx.conf includes:
- SPA fallback (routes to index.html)
- API proxy to backend
- Security headers
- Gzip compression
- Cache headers for assets

## Browser DevTools

The app works with React DevTools and Redux DevTools (for Zustand debugging).

## Performance Notes

- Code splitting enabled for react, query, and recharts vendors
- Lazy loading images
- Recharts optimization for large datasets
- Query caching reduces API calls
- Optimized CSS with Tailwind purging

## Troubleshooting

**API calls fail with CORS errors:**
- Check VITE_API_URL is correct
- Ensure backend has CORS enabled
- Check nginx.conf API proxy settings

**Charts not displaying:**
- Ensure recharts is installed
- Check browser console for data errors
- Verify mock data is being used

**Dark mode not working:**
- Add `dark` class to `<html>` element
- Check Tailwind dark mode in config

**Build fails:**
- Delete `node_modules` and `dist`
- Run `npm install` again
- Check for TypeScript errors with `npm run lint`

## Next Steps

1. Configure backend API URL in `.env`
2. Test transaction API endpoints
3. Customize colors and branding
4. Add authentication pages (login, register)
5. Implement error boundaries
6. Add analytics tracking
7. Set up CI/CD pipeline

## Support

For issues or questions about the setup, check the README.md or contact the development team.
