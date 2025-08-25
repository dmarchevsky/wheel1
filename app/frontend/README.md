# Wheel Strategy Frontend

A modern, responsive trading dashboard built with Next.js and Material-UI (MUI) for managing options trading strategies.

## Features

- **Modern UI**: Built with Material-UI v5 with a dark theme optimized for trading
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Real-time Data**: Live position tracking and P&L calculations
- **Interactive Charts**: Advanced data visualization with MUI X Charts
- **Data Grid**: Powerful table component with sorting, filtering, and pagination
- **TypeScript**: Full type safety throughout the application
- **Component Library**: Reusable components for consistent UI/UX

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **UI Library**: Material-UI (MUI) v5
- **Charts**: MUI X Charts + Recharts
- **Data Grid**: MUI X Data Grid
- **Date Handling**: MUI X Date Pickers + date-fns
- **HTTP Client**: Axios
- **Language**: TypeScript
- **Styling**: Emotion (CSS-in-JS)

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Docker (for containerized deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd wheel1/app/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   ```
   
   Configure the following variables:
   ```env
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```

4. **Run the development server**
   ```bash
   npm run dev
   ```

5. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

### Docker Deployment

The frontend is configured for Docker deployment with the existing infrastructure:

```bash
# From the project root
cd infra
docker-compose up frontend
```

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout with MUI theme
│   ├── page.tsx           # Dashboard home page
│   └── positions/         # Positions management page
├── components/            # Reusable UI components
│   ├── PositionCard.tsx   # Individual position display
│   ├── RecommendationCard.tsx # Trading recommendations
│   └── SummaryCard.tsx    # Metric summary cards
├── lib/                   # Utility libraries
│   └── api.ts            # API client configuration
└── types/                # TypeScript type definitions
    └── index.ts          # Application interfaces
```

## Key Components

### Dashboard (`src/app/page.tsx`)
The main dashboard featuring:
- Portfolio overview with key metrics
- Current positions table
- Trading recommendations
- Real-time P&L tracking

### Positions Page (`src/app/positions/page.tsx`)
Dedicated position management with:
- Detailed position information
- Add/edit/delete functionality
- Multiple view modes (table/cards)
- Advanced filtering and sorting

### PositionCard Component
Expandable position cards showing:
- Basic position details
- P&L with color coding
- Greeks (delta, gamma, theta, vega)
- Interactive expand/collapse

### RecommendationCard Component
Trading recommendation display with:
- Strategy information
- Risk assessment
- Confidence indicators
- Execute trade functionality

## API Integration

The frontend integrates with the backend API through the `src/lib/api.ts` client:

- **Positions**: CRUD operations for option positions
- **Recommendations**: Trading strategy recommendations
- **Account**: Portfolio and balance information
- **Health**: API status monitoring

## Styling & Theming

The application uses a custom dark theme optimized for trading:

- **Primary Color**: Green (#00d4aa) for positive P&L
- **Secondary Color**: Red (#ff6b6b) for negative P&L
- **Background**: Dark theme (#0a0a0a, #1a1a1a)
- **Typography**: Inter font family
- **Components**: Customized MUI components with rounded corners

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - TypeScript type checking

### Code Style

- TypeScript for type safety
- ESLint for code quality
- Prettier for code formatting
- Component-based architecture
- Custom hooks for state management

## Deployment

### Production Build

```bash
npm run build
npm run start
```

### Docker Build

```bash
docker build -f infra/Dockerfile.frontend -t wheel-frontend .
```

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for new features
3. Include proper error handling
4. Test components across different screen sizes
5. Update documentation for new features

## License

This project is part of the Wheel Strategy trading system.

