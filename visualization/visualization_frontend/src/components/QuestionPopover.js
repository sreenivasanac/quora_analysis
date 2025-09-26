import React from 'react';
import './QuestionPopover.css';

const QuestionPopover = ({ questions, position, onClose, isPinned }) => {
  if (!questions || questions.length === 0) return null;

  // Truncate question text for display
  const truncateText = (text, maxLength = 80) => {
    if (!text) return 'No question text';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Format time
  const formatTime = (datetime) => {
    const date = new Date(datetime);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };

  return (
    <div
      className={`question-popover ${isPinned ? 'pinned' : ''}`}
      style={{
        top: position.top,
        left: position.left
      }}
    >
      <div className="popover-header">
        <h4>Questions ({questions.length})</h4>
        {isPinned && (
          <button className="close-btn" onClick={onClose}>×</button>
        )}
      </div>
      <div className="popover-content">
        <ul className="question-list">
          {questions.map((item, index) => (
            <li key={index} className="question-item">
              <span className="question-time">{formatTime(item.datetime)}</span>
              <a
                href={item.answer_url}
                target="_blank"
                rel="noopener noreferrer"
                className="question-link"
                title={item.question_text}
              >
                {truncateText(item.question_text)}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default QuestionPopover;