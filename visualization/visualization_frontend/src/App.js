import React, { useState, useEffect } from 'react';
import CalendarView from './components/CalendarView';
import TimezoneSelector from './components/TimezoneSelector';
import StatsPanel from './components/StatsPanel';
import { fetchTimestamps, fetchStats } from './api';
import './App.css';

function App() {
  const [currentWeek, setCurrentWeek] = useState(new Date());
  const [timezone, setTimezone] = useState('IST');
  const [timestamps, setTimestamps] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Calculate week boundaries
  const getWeekBoundaries = (date) => {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust for Monday start
    const monday = new Date(d.setDate(diff));
    monday.setHours(0, 0, 0, 0);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    sunday.setHours(23, 59, 59, 999);
    return { start: monday, end: sunday };
  };

  // Load timestamps for current week
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const { start, end } = getWeekBoundaries(currentWeek);
        const data = await fetchTimestamps(start, end, timezone);
        setTimestamps(data.timestamps || []);
      } catch (err) {
        setError('Failed to load timestamps');
        console.error('Error loading timestamps:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [currentWeek, timezone]);

  // Load statistics
  useEffect(() => {
    const loadStats = async () => {
      try {
        const statsData = await fetchStats(timezone);
        setStats(statsData.stats);
      } catch (err) {
        console.error('Error loading stats:', err);
      }
    };

    loadStats();
  }, [timezone]);

  // Navigation handlers
  const goToPreviousWeek = () => {
    const newWeek = new Date(currentWeek);
    newWeek.setDate(newWeek.getDate() - 7);
    setCurrentWeek(newWeek);
  };

  const goToNextWeek = () => {
    const newWeek = new Date(currentWeek);
    newWeek.setDate(newWeek.getDate() + 7);
    setCurrentWeek(newWeek);
  };

  const goToCurrentWeek = () => {
    setCurrentWeek(new Date());
  };

  const { start, end } = getWeekBoundaries(currentWeek);
  const weekLabel = `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;

  return (
    <div className="App">
      <header className="App-header">
        <h1>Quora Activity Timeline</h1>
        <div className="header-controls">
          <TimezoneSelector
            currentTimezone={timezone}
            onTimezoneChange={setTimezone}
          />
        </div>
      </header>

      {stats && (
        <StatsPanel stats={stats} timezone={timezone} />
      )}

      <div className="calendar-container">
        <div className="week-navigation">
          <button onClick={goToPreviousWeek} className="nav-button">
            ← Previous Week
          </button>
          <div className="week-label">
            <h2>{weekLabel}</h2>
            <button onClick={goToCurrentWeek} className="current-week-btn">
              Current Week
            </button>
          </div>
          <button onClick={goToNextWeek} className="nav-button">
            Next Week →
          </button>
        </div>

        {loading && <div className="loading">Loading timestamps...</div>}
        {error && <div className="error">{error}</div>}

        {!loading && !error && (
          <CalendarView
            weekStart={start}
            weekEnd={end}
            timestamps={timestamps}
            timezone={timezone}
          />
        )}
      </div>
    </div>
  );
}

export default App;
