# Deployment Guide: Vercel + Supabase

This guide covers deploying your Quora visualization app to Vercel with Supabase database.

## Prerequisites
- Supabase account with database setup ✓ (You already completed this)
- GitHub repository
- Vercel account

## Local Development

### 1. Run Flask Backend (Port 5000)
```bash
cd visualization
python visualization_backend.py
```

### 2. Run React Frontend (Port 3000)
```bash
cd visualization/visualization_frontend
npm start
```

The React app will automatically connect to the Flask backend on localhost:5000.

## Production Deployment to Vercel

### 1. Environment Variables
Add these environment variables in Vercel dashboard:
- `DATABASE_URL`: Your Supabase PostgreSQL connection string

### 2. Deploy to Vercel
1. Connect your GitHub repository to Vercel
2. Vercel will automatically detect the `vercel.json` configuration
3. The deployment will:
   - Deploy Python serverless functions (`/api/*`)
   - Build and serve the React frontend
   - Handle routing between frontend and API

### 3. Architecture
- **Frontend**: React app served as static files
- **Backend**: Python serverless functions in `/api/` directory
- **Database**: Supabase PostgreSQL (already configured)

## API Endpoints (Both Local & Production)
- `/api/health` - Health check
- `/api/timestamps` - Get timestamps for date range
- `/api/stats` - Get overall statistics
- `/api/timestamps/all` - Get all timestamps

## File Structure
```
project/
├── api/                    # Vercel serverless functions
│   ├── timestamps.py
│   ├── stats.py
│   └── health.py
├── utils/                  # Shared business logic
│   ├── database.py
│   └── timezone_utils.py
├── visualization/
│   ├── visualization_backend.py    # Flask app (local dev)
│   └── visualization_frontend/     # React app
├── requirements.txt        # Python dependencies
└── vercel.json            # Vercel configuration
```

## Cost
- **Vercel**: Free tier (sufficient for your use case)
- **Supabase**: Free tier (500MB database)
- **Total**: $0/month

## Benefits of This Setup
- ✅ Works locally with Flask + React
- ✅ Deploys to Vercel serverless functions
- ✅ Same codebase for both environments
- ✅ No code duplication
- ✅ Easy development workflow