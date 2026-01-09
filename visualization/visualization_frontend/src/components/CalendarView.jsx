import React, { useMemo, useState, useRef, useEffect } from 'react';
import QuestionPopover from './QuestionPopover.jsx';
import './CalendarView.css';

const CalendarView = ({ weekStart, weekEnd, timestamps, timezone }) => {
  // Memoize static arrays to prevent unnecessary re-renders
  const days = useMemo(() => ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], []);
  const hours = useMemo(() => Array.from({ length: 24 }, (_, i) => i), []);

  // State for popover
  const [hoveredCell, setHoveredCell] = useState(null);
  const [pinnedCell, setPinnedCell] = useState(null);
  const [popoverPosition, setPopoverPosition] = useState({ top: 0, left: 0 });
  const gridRef = useRef(null);
  const hoverTimeoutRef = useRef(null);

  // Timezone mapping for date-fns
  const getTimezoneString = (tz) => {
    const mapping = {
      'IST': 'Asia/Kolkata',
      'CST': 'Asia/Shanghai',
      'PST': 'America/Los_Angeles',
      'EST': 'America/New_York'
    };
    return mapping[tz] || 'Asia/Kolkata';
  };

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
      // For timezone-converted data, use the day property from backend if available
      // Otherwise fall back to parsing the datetime (which may have timezone issues)
      let dayOfWeek;
      if (ts.day) {
        // Convert day name to index (Monday = 0, Sunday = 6)
        const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        dayOfWeek = dayNames.indexOf(ts.day);
      } else {
        const date = new Date(ts.datetime);
        dayOfWeek = date.getDay() === 0 ? 6 : date.getDay() - 1; // Adjust for Monday start
      }

      // Use the hour from backend conversion (ts.hour) instead of re-parsing
      // This preserves the timezone conversion done on the backend
      const hour = ts.hour !== undefined ? ts.hour : new Date(ts.datetime).getHours();

      if (grid[dayOfWeek] && grid[dayOfWeek][hour] !== undefined) {
        grid[dayOfWeek][hour].push(ts);
      }
    });

    return grid;
  }, [timestamps, days, hours]);

  // Fixed intensity thresholds for consistent coloring across weeks
  const getIntensityColor = (count) => {
    if (count === 0) return 'transparent';
    if (count === 1) return '#a5d6a7'; // Very light green
    if (count === 2) return '#4caf50'; // Medium green
    if (count >= 3) return '#1b5e20'; // Dark green
    return 'transparent';
  };

  // Get current hour for highlighting in selected timezone
  const getCurrentTimeInTimezone = () => {
    const tzString = getTimezoneString(timezone);
    // Get current time in the selected timezone
    const now = new Date();
    const localTime = now.toLocaleString('en-US', { timeZone: tzString });
    return new Date(localTime);
  };

  const nowInTimezone = getCurrentTimeInTimezone();
  const currentDay = nowInTimezone.getDay() === 0 ? 6 : nowInTimezone.getDay() - 1;
  const currentHour = nowInTimezone.getHours();

  // Check if current week
  const isCurrentWeek = () => {
    const nowInTz = getCurrentTimeInTimezone();
    return nowInTz >= weekStart && nowInTz <= weekEnd;
  };

  // Handle click outside to close pinned popover
  useEffect(() => {
    const handleClickOutside = (event) => {
      // Check if click was outside both the popover and the grid cells
      const clickedOnPopover = event.target.closest('.question-popover');
      const clickedOnCell = event.target.closest('.hour-cell');

      if (!clickedOnPopover && !clickedOnCell && pinnedCell) {
        // Click was outside, close the pinned popover
        setPinnedCell(null);
        setHoveredCell(null);
      }
    };

    // Only add listener when there's a pinned popover
    if (pinnedCell) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [pinnedCell]);

  // Handle cell hover
  const handleCellHover = (dayIndex, hour, event) => {
    const cellData = timestampGrid[dayIndex][hour];
    if (!cellData || cellData.length === 0) return;

    // Clear any existing timeout
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }

    // Don't show hover popover if already pinned
    if (pinnedCell) return;

    // Set timeout to show popover after short delay
    hoverTimeoutRef.current = setTimeout(() => {
      const rect = event.target.getBoundingClientRect();
      const gridRect = gridRef.current?.getBoundingClientRect() || { top: 0, left: 0 };

      setPopoverPosition({
        top: rect.bottom - gridRect.top + 10,
        left: rect.left - gridRect.left
      });
      setHoveredCell({ dayIndex, hour });
    }, 300);
  };

  // Handle cell mouse leave
  const handleCellLeave = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    if (!pinnedCell) {
      setHoveredCell(null);
    }
  };

  // Handle cell click
  const handleCellClick = (dayIndex, hour, event) => {
    const cellData = timestampGrid[dayIndex][hour];
    if (!cellData || cellData.length === 0) return;

    // Stop propagation to prevent immediate close from click-outside handler
    event.stopPropagation();

    // Toggle pinned state
    if (pinnedCell?.dayIndex === dayIndex && pinnedCell?.hour === hour) {
      setPinnedCell(null);
      setHoveredCell(null);
    } else {
      const rect = event.target.getBoundingClientRect();
      const gridRect = gridRef.current?.getBoundingClientRect() || { top: 0, left: 0 };

      setPopoverPosition({
        top: rect.bottom - gridRect.top + 10,
        left: rect.left - gridRect.left
      });
      setPinnedCell({ dayIndex, hour });
      setHoveredCell(null);
    }
  };

  // Get questions for popover
  const getPopoverQuestions = () => {
    if (pinnedCell) {
      return timestampGrid[pinnedCell.dayIndex][pinnedCell.hour] || [];
    }
    if (hoveredCell) {
      return timestampGrid[hoveredCell.dayIndex][hoveredCell.hour] || [];
    }
    return [];
  };

  return (
    <div className="calendar-view">
      <div className="calendar-grid" ref={gridRef}>
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
                  className={`hour-cell ${isCurrentCell ? 'current-hour' : ''} ${count > 0 ? 'has-data' : ''}`}
                  style={{
                    backgroundColor: getIntensityColor(count)
                  }}
                  onMouseEnter={(e) => handleCellHover(dayIndex, hour, e)}
                  onMouseLeave={handleCellLeave}
                  onClick={(e) => handleCellClick(dayIndex, hour, e)}
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
          <div className="legend-levels">
            <div className="legend-level">
              <div className="legend-color" style={{ backgroundColor: 'transparent', border: '1px solid #ddd' }}></div>
              <span>0</span>
            </div>
            <div className="legend-level">
              <div className="legend-color" style={{ backgroundColor: getIntensityColor(1) }}></div>
              <span>1</span>
            </div>
            <div className="legend-level">
              <div className="legend-color" style={{ backgroundColor: getIntensityColor(2) }}></div>
              <span>2</span>
            </div>
            <div className="legend-level">
              <div className="legend-color" style={{ backgroundColor: getIntensityColor(3) }}></div>
              <span>3+</span>
            </div>
          </div>
        </div>
      </div>

      {/* Question Popover */}
      {(hoveredCell || pinnedCell) && (
        <QuestionPopover
          questions={getPopoverQuestions()}
          position={popoverPosition}
          onClose={() => {
            setPinnedCell(null);
            setHoveredCell(null);
          }}
          isPinned={!!pinnedCell}
        />
      )}
    </div>
  );
};

export default CalendarView;