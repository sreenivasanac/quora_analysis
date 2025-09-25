import React from 'react';
import './StatsPanel.css';

const StatsPanel = ({ stats, timezone }) => {
  if (!stats) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="stats-panel">
      <h2>Statistics ({timezone} Timezone)</h2>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total_count.toLocaleString()}</div>
          <div className="stat-label">Total Answers</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.busiest_hour}:00</div>
          <div className="stat-label">Most Active Hour</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.busiest_day}</div>
          <div className="stat-label">Most Active Day</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{formatDate(stats.earliest_date)}</div>
          <div className="stat-label">First Answer</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{formatDate(stats.latest_date)}</div>
          <div className="stat-label">Latest Answer</div>
        </div>
      </div>
    </div>
  );
};

export default StatsPanel;