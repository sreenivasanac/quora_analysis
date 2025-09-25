# Quora Activity Timeline Visualization

A calendar heatmap visualization system for viewing 20,000+ Quora answer timestamps with timezone support.

## Features

- **Weekly Calendar View**: 7 days × 24 hours grid showing activity patterns
- **Multi-Timezone Support**: Switch between IST, CST, PST, and EST timezones
- **Interactive Visualization**: Hover over cells to see post counts
- **Activity Intensity**: Color-coded cells based on posting frequency
- **Week Navigation**: Browse through different weeks with easy navigation
- **Statistics Panel**: View overall statistics including total posts, busiest times
- **Current Time Highlight**: Visual indicator for current hour in the selected timezone

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL database with Quora answers data
- `.env` file with DATABASE_URL configured

### Backend Setup

1. Navigate to the visualization directory:
```bash
cd visualization
```

2. Install Python dependencies:
```bash
pip install -r requirements_viz.txt
```

3. Start the Flask backend server:
```bash
python visualization_backend.py
```

The backend will run on `http://localhost:5000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd visualization_frontend
```

2. Install Node dependencies:
```bash
npm install
```

3. Start the React development server:
```bash
npm start
```

The frontend will run on `http://localhost:3000`

## Usage

1. **Start Both Servers**: Make sure both Flask backend (port 5000) and React frontend (port 3000) are running

2. **View the Visualization**: Open your browser and go to `http://localhost:3000`

3. **Navigate Weeks**:
   - Use "← Previous Week" and "Next Week →" buttons to browse different weeks
   - Click "Current Week" to jump to the current week

4. **Change Timezone**:
   - Select from the dropdown menu in the header
   - Available timezones:
     - IST (Indian Standard Time, UTC+5:30)
     - CST (China Standard Time, UTC+8:00)
     - PST (Pacific Standard Time, UTC-8:00)
     - EST (Eastern Standard Time, UTC-5:00)

5. **View Activity Patterns**:
   - Darker blue cells indicate more posts in that hour
   - Hover over cells to see exact post count
   - Dots appear in cells with activity (up to 10 dots shown)
   - Numbers like "+5" indicate additional posts beyond 10

6. **Statistics Panel**:
   - Total number of answers
   - Most active hour of the day
   - Most active day of the week
   - Date range of posts

## Architecture

### Backend (Flask)
- **API Endpoints**:
  - `/api/timestamps` - Get timestamps for a date range
  - `/api/stats` - Get overall statistics
  - `/api/health` - Health check endpoint
- **Timezone Conversion**: Server-side conversion using pytz
- **Database**: PostgreSQL connection with psycopg2

### Frontend (React)
- **Components**:
  - `App.js` - Main application component
  - `CalendarView` - Weekly grid visualization
  - `TimezoneSelector` - Timezone dropdown selector
  - `StatsPanel` - Statistics display
- **Visualization**: D3.js for color scaling
- **Date Handling**: date-fns for date operations

## Troubleshooting

### Backend Issues

1. **Database Connection Error**:
   - Check `.env` file has correct DATABASE_URL
   - Verify PostgreSQL is running
   - Check database credentials

2. **Port Already in Use**:
   - Change port in `visualization_backend.py` if 5000 is occupied
   - Update `API_BASE_URL` in `frontend/src/api.js` accordingly

### Frontend Issues

1. **Cannot Connect to Backend**:
   - Ensure Flask server is running on port 5000
   - Check CORS is enabled in Flask
   - Verify no firewall blocking the connection

2. **No Data Showing**:
   - Check browser console for errors
   - Verify timestamps exist in database with `post_timestamp_parsed` field populated
   - Ensure date range contains data

## Performance Notes

- The system efficiently loads only the current week's data
- With 20,000+ timestamps, initial statistics calculation may take a moment
- Timezone changes trigger data reload with conversion

## Development

### Adding New Timezones

1. Update `TIMEZONES` dict in `visualization_backend.py`
2. Add timezone option in `TimezoneSelector.js`
3. Update timezone mapping in `getTimezoneName()` function

### Customizing Visualization

- Modify color scheme in `CalendarView.js` (d3.interpolateBlues)
- Adjust grid size in `CalendarView.css`
- Change dot limit per cell in `CalendarView.js`

## License

Part of the Quora Analysis project