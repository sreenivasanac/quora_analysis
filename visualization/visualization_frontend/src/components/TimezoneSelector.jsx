import React from 'react';
import './TimezoneSelector.css';

const TimezoneSelector = ({ currentTimezone, onTimezoneChange }) => {
  const timezones = [
    { value: 'IST', label: 'IST (India)', offset: '+5:30' },
    { value: 'CST', label: 'CST (China)', offset: '+8:00' },
    { value: 'PST', label: 'PST (Pacific)', offset: '-8:00' },
    { value: 'EST', label: 'EST (Eastern)', offset: '-5:00' }
  ];

  return (
    <div className="timezone-selector">
      <label htmlFor="timezone">Timezone:</label>
      <select
        id="timezone"
        value={currentTimezone}
        onChange={(e) => onTimezoneChange(e.target.value)}
        className="timezone-dropdown"
      >
        {timezones.map(tz => (
          <option key={tz.value} value={tz.value}>
            {tz.label} (UTC{tz.offset})
          </option>
        ))}
      </select>
      <div className="current-time">
        Current Time: {new Date().toLocaleString('en-US', {
          timeZone: getTimezoneName(currentTimezone),
          dateStyle: 'short',
          timeStyle: 'medium'
        })}
      </div>
    </div>
  );
};

// Helper function to map our timezone codes to IANA timezone names
const getTimezoneName = (tzCode) => {
  const mapping = {
    'IST': 'Asia/Kolkata',
    'CST': 'Asia/Shanghai',
    'PST': 'America/Los_Angeles',
    'EST': 'America/New_York'
  };
  return mapping[tzCode] || 'Asia/Kolkata';
};

export default TimezoneSelector;