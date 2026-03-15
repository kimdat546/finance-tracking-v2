# Personal Finance Tracker - Frontend

A modern React 18 + TypeScript + Vite web application for tracking personal finances, managing budgets, and analyzing spending patterns.

## Features

- **Dashboard**: Overview of income, expenses, and savings with charts
- **Transaction Management**: Track, filter, and categorize all transactions
- **Split Bills**: Share expenses with friends and settle debts
- **Budget Planning**: Set and monitor budgets for each category
- **Financial Goals**: Track savings goals and progress
- **Debt Management**: Monitor loans and payment schedules
- **Subscriptions**: Keep track of recurring charges
- **Reports**: Detailed analytics and spending insights
- **Settings**: Manage accounts, categories, and integrations

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS 4
- **Charts**: Recharts
- **State Management**: Zustand
- **Data Fetching**: TanStack React Query
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **Date Handling**: date-fns
- **Testing**: Vitest + Testing Library

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Update VITE_API_URL if needed
```

### Development

```bash
# Start development server
npm run dev

# The app will open at http://localhost:5173
```

### Build

```bash
# Create production build
npm run build

# Preview production build
npm run preview
```

### Testing

```bash
# Run tests
npm test

# Run tests with UI
npm run test:ui
```

### Linting & Formatting

```bash
# Lint code
npm run lint

# Format code
npm run format
```

## Project Structure

```
frontend/
├── public/                 # Static assets
├── src/
│   ├── api/               # API client and endpoints
│   ├── components/        # React components
│   │   ├── Layout/       # Main layout components
│   │   └── ui/           # Reusable UI components
│   ├── hooks/            # Custom React hooks
│   ├── pages/            # Page components
│   ├── store/            # Zustand state stores
│   ├── test/             # Test setup and utilities
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utility functions
│   ├── App.tsx           # Main app component
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── .env.example          # Example environment variables
├── Dockerfile            # Docker configuration
├── nginx.conf            # Nginx configuration
├── tailwind.config.js    # Tailwind CSS configuration
├── tsconfig.json         # TypeScript configuration
├── vite.config.ts        # Vite configuration
└── package.json          # Project dependencies
```

## Environment Variables

Create a `.env` file based on `.env.example`:

```env
VITE_API_URL=http://localhost:8000
```

## API Integration

The frontend communicates with the backend API at the URL specified in `VITE_API_URL`. The API client includes:

- Automatic auth token injection
- Request/response interceptors
- Error handling
- Base URL configuration

## Styling

The application uses Tailwind CSS 4 with:

- Custom color scheme for finance tracking
- Dark mode support
- Responsive design patterns
- Accessible components

### Color Palette

- **Primary**: Blue (#3B82F6)
- **Success**: Green (#10B981)
- **Danger**: Red (#EF4444)
- **Warning**: Amber (#F59E0B)

## Docker

Build and run with Docker:

```bash
# Build image
docker build -t finance-tracker-frontend .

# Run container
docker run -p 80:80 finance-tracker-frontend
```

## Performance Optimizations

- Code splitting via Vite
- Image lazy loading
- React Query caching
- Gzip compression
- Production builds minified

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License.

## Support

For issues or questions, please open an GitHub issue or contact the development team.
