import React from 'react';

/**
 * Renders **bold** segments as <strong>; other text unchanged.
 */
function formatInlineSegments(text) {
  if (text == null || text === '') return null;
  const parts = String(text).split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    const m = part.match(/^\*\*([^*]+)\*\*$/);
    if (m) {
      return <strong key={i}>{m[1]}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

/**
 * Teaching / theory copy: paragraphs split on newlines, inline **bold** preserved.
 */
export function FormattedTeaching({ children, className }) {
  if (children == null || children === '') {
    return null;
  }
  const lines = String(children).split('\n');
  return (
    <div className={className}>
      {lines.map((line, idx) => (
        <p key={idx}>
          {formatInlineSegments(line)}
        </p>
      ))}
    </div>
  );
}
