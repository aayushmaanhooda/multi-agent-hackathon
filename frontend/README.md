# Frontend - Multi-Agent Roster Management System

## Overview

Modern React frontend built with Vite, providing an intuitive interface for managing employee rosters through a multi-agent AI system. The frontend communicates with a FastAPI backend that orchestrates LangChain agents for intelligent roster generation.

## Tech Stack

- **React 19.2.0** - UI framework
- **Vite 7.2.4** - Build tool and dev server
- **React Router DOM 7.10.1** - Client-side routing
- **Framer Motion 12.23.25** - Animations
- **Lucide React 0.556.0** - Icon library
- **CSS3** - Custom styling with modern design patterns

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── components/     # Reusable UI components
│   │   ├── GooeyNav.jsx          # Navigation component
│   │   ├── GradientText.jsx     # Text styling component
│   │   ├── BrandLogo.jsx         # Branding component
│   │   ├── ProtectedRoute.jsx    # Route protection
│   │   ├── AdminChat.jsx         # RAG chat interface
│   │   └── ...
│   ├── pages/          # Page components
│   │   ├── LandingPage.jsx       # Landing page
│   │   ├── LoginPage.jsx          # Authentication
│   │   ├── RegisterPage.jsx       # User registration
│   │   ├── Dashboard.jsx         # User dashboard
│   │   ├── SetRoster.jsx          # File upload & roster generation
│   │   ├── RosterPage.jsx         # Roster viewing
│   │   └── ...
│   ├── services/
│   │   └── api.js       # Backend API client
│   ├── App.jsx          # Main app component with routing
│   ├── main.jsx         # Entry point
│   └── index.css        # Global styles
├── package.json
├── vite.config.js
└── README.md
```

## Installation

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend server running on `http://localhost:8000`

### Install Dependencies

```bash
cd frontend
npm install
```

## Development

### Start Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (Vite default port).

### Build for Production

```bash
npm run build
```

Production build will be created in `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Environment Variables

No environment variables are required for the frontend. The API URL is hardcoded in `src/services/api.js`:

```javascript
const API_URL = "http://localhost:8000";
```

To change the backend URL, modify this constant in `api.js`.

## UI Architecture

### Multi-Agent Theme

The UI is designed around the multi-agent system concept:

- **Landing Page**: Showcases the multi-agent roster generation system
- **Set Roster Page**: Upload files and trigger multi-agent workflow
- **Progress Tracking**: Real-time updates from agent pipeline
- **Admin Chat**: RAG-powered chat interface for roster queries

### Key Components

#### `SetRoster.jsx`
- File upload interface for employee data (.xlsx) and store requirements (.csv)
- Triggers multi-agent pipeline via `/generate-roster` endpoint
- Displays real-time progress messages from agents
- Shows coverage metrics and violations after generation

#### `RosterPage.jsx`
- Displays generated roster with coverage statistics
- Shows violations and recommendations
- Download links for Excel roster and reports

#### `AdminChat.jsx`
- RAG-powered chat interface
- Queries roster data using natural language
- Maintains conversation history

#### `ProtectedRoute.jsx`
- Route protection based on authentication
- Role-based access control (admin vs regular user)

## API Integration

### Service Layer (`src/services/api.js`)

The frontend communicates with the backend through a centralized API service:

```javascript
export const api = {
    login: async (email, password) => { ... },
    register: async (userData) => { ... },
    getMe: async () => { ... },
    logout: async () => { ... },
    chat: async (message, conversationId) => { ... }
}
```

### Multi-Agent Endpoints

#### Upload Files
```javascript
// POST /upload-roster
// FormData with employee_file and store_file
// Saves files to backend/multi_agents/dataset/
```

#### Generate Roster
```javascript
// POST /generate-roster
// Triggers full multi-agent pipeline:
// Agent 1 → Agent 2 → Agent 3 → Agent 4 → (loop if violations) → Agent 5
// Returns: roster_file, report_file, violations, coverage_percent, progress
```

#### Get Roster Status
```javascript
// GET /get-roster
// Returns current roster status, coverage metrics, violations
```

#### Download Files
```javascript
// GET /download-roster/{filename}
// GET /download-report/{filename}
// Downloads generated Excel roster or report files
```

#### RAG Chat
```javascript
// POST /chat
// Sends message to RAG agent
// Returns AI-generated response based on roster data
```

## Authentication Flow

1. **Registration**: Users register with email, password, and role
   - Admin role requires access code
   - Regular users can register freely

2. **Login**: JWT-based authentication
   - Credentials sent to `/login`
   - Access token stored in HTTP-only cookie
   - Token used for subsequent API calls

3. **Session Management**:
   - `getMe()` checks current session via `/dashboard`
   - `logout()` clears session
   - Protected routes check authentication status

4. **Role-Based Access**:
   - Admin: Full access to roster generation and management
   - Regular users: Limited dashboard access

## Multi-Agent Integration

### Workflow Trigger

When user clicks "Generate Roster" in `SetRoster.jsx`:

1. Files are uploaded via `/upload-roster` (if not already uploaded)
2. `/generate-roster` endpoint is called
3. Backend orchestrates LangGraph workflow:
   - **Agent 1**: Parses employee and store data
   - **Agent 2**: Analyzes constraints and rules
   - **Agent 3**: Generates roster schedule
   - **Agent 4**: Validates roster for violations
   - **Loop**: Agent 3-4 iterate up to 4 times if violations found
   - **Agent 5**: Final comprehensive check and report generation

4. Frontend receives progress updates via `progress` array
5. Final results include:
   - Coverage percentage (target: 80-90%)
   - Violations count
   - Roster file path
   - Report file paths
   - Recommendations

### Progress Tracking

The frontend displays real-time progress messages:

```javascript
progress: [
    "🔄 Running multi-agent workflow...",
    "🔄 Agent 1: Parsing and structuring data...",
    "✅ Agent 1 completed: Processed 50 employees...",
    "🔄 Agent 2: Analyzing constraints...",
    // ... more messages
]
```

## Routing

Routes defined in `App.jsx`:

- `/` - Landing page
- `/login` - User login
- `/register` - User registration
- `/dashboard` - User dashboard (protected)
- `/set-roster` - Upload files and generate roster (admin only)
- `/roster` - View generated roster (admin only)
- `/chat` - RAG chat interface (admin only)
- `/about` - About page
- `/contact` - Contact page
- `/subscription` - Subscription page

## Styling

- Custom CSS with modern design patterns
- Gradient effects and animations
- Responsive design
- Multi-agent themed UI elements

## Development Notes

- Uses React Router for client-side navigation
- State management via React hooks (useState, useEffect)
- API calls use native `fetch` API
- Credentials included for cookie-based auth
- Error handling via try-catch blocks

## Production Deployment

1. Build the project: `npm run build`
2. Serve `dist/` directory with a static file server (nginx, Apache, etc.)
3. Configure CORS on backend to allow frontend domain
4. Update `API_URL` in `api.js` for production backend URL

## Troubleshooting

### CORS Errors
- Ensure backend CORS middleware allows frontend origin
- Check `allow_origins` in backend `api.py`

### Authentication Issues
- Verify cookies are enabled in browser
- Check backend session management
- Ensure JWT token is being set correctly

### File Upload Issues
- Verify file types (.xlsx for employees, .csv for stores)
- Check file size limits
- Ensure backend dataset directory exists

### Agent Progress Not Updating
- Check WebSocket/SSE if implemented
- Verify backend returns `progress` array in response
- Check network tab for API responses
