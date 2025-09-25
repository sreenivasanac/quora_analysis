import React, { useMemo } from 'react';
import * as d3 from 'd3';
import './CalendarView.css';

const CalendarView = ({ weekStart, weekEnd, timestamps, timezone }) => {
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const hours = Array.from({ length: 24 }, (_, i) => i);

  // Process timestamps into a grid structure
  const timestampGrid = useMemo(() => {
    const grid = {};

    // Initialize grid
    days.forEach((day, dayIndex) => {
      grid[dayIndex] = {};
      hours.forEach(hour => {
        grid[dayIndex][hour] = [];
      });
    });

    // Populate grid with timestamps
    timestamps.forEach(ts => {
      const date = new Date(ts.datetime);
      const dayOfWeek = date.getDay() === 0 ? 6 : date.getDay() - 1; // Adjust for Monday start
      const hour = date.getHours();

      if (grid[dayOfWeek] && grid[dayOfWeek][hour] !== undefined) {
        grid[dayOfWeek][hour].push(ts);
      }
    });

    return grid;
  }, [timestamps, days, hours]);

  // Calculate max count for scaling
  const maxCount = useMemo(() => {
    let max = 0;
    Object.values(timestampGrid).forEach(dayData => {
      Object.values(dayData).forEach(hourData => {
        if (hourData.length > max) {
          max = hourData.length;
        }
      });
    });
    return max;
  }, [timestampGrid]);

  // Color scale
  const colorScale = d3.scaleSequential()
    .domain([0, maxCount])
    .interpolator(d3.interpolateBlues);

  // Get current hour for highlighting
  const now = new Date();
  const currentDay = now.getDay() === 0 ? 6 : now.getDay() - 1;
  const currentHour = now.getHours();

  // Check if current week
  const isCurrentWeek = () => {
    const now = new Date();
    return now >= weekStart && now <= weekEnd;
  };

  return (
    <div className="calendar-view">
      <div className="calendar-grid">
        {/* Hour labels */}
        <div className="hour-labels">
          <div className="empty-cell"></div>
          {hours.map(hour => (
            <div key={hour} className="hour-label">
              {hour.toString().padStart(2, '0')}:00
            </div>
          ))}
        </div>

        {/* Day rows */}
        {days.map((day, dayIndex) => (
          <div key={day} className="day-row">
            <div className="day-label">{day}</div>
            {hours.map(hour => {
              const cellTimestamps = timestampGrid[dayIndex][hour] || [];
              const count = cellTimestamps.length;
              const isCurrentCell = isCurrentWeek() && dayIndex === currentDay && hour === currentHour;

              return (
                <div
                  key={`${dayIndex}-${hour}`}
                  className={`hour-cell ${isCurrentCell ? 'current-hour' : ''}`}
                  style={{
                    backgroundColor: count > 0 ? colorScale(count) : 'transparent'
                  }}
                  title={`${day} ${hour}:00 - ${count} post${count !== 1 ? 's' : ''}`}
                >
                  {count > 0 && (
                    <div className="timestamp-dots">
                      {Array.from({ length: Math.min(count, 10) }, (_, i) => (
                        <div key={i} className="dot" />
                      ))}
                      {count > 10 && <span className="count-overflow">+{count - 10}</span>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="calendar-legend">
        <div className="legend-title">Activity Intensity</div>
        <div className="legend-gradient">
          <div className="gradient-bar" style={{
            background: `linear-gradient(to right, ${colorScale(0)}, ${colorScale(maxCount / 2)}, ${colorScale(maxCount)})`
          }}></div>
          <div className="gradient-labels">
            <span>0</span>
            <span>{Math.floor(maxCount / 2)}</span>
            <span>{maxCount}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarView;