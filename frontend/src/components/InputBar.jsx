import { useEffect, useRef } from 'react';
import styles from './InputBar.module.css';

export default function InputBar({
  value,
  onChange,
  onGenerate,
  onKeep,
  onRegen,
  onVary,
  disabled,
  loading,
  awaitingConfirmation,
  prominent = false,
  onDismissPostKeepOverlay,
}) {
  const confirm = !!awaitingConfirmation;
  const overlayDismissRef = useRef(false);

  useEffect(() => {
    overlayDismissRef.current = false;
  }, [onDismissPostKeepOverlay]);

  const tryDismissOverlay = () => {
    if (!onDismissPostKeepOverlay || overlayDismissRef.current) return;
    overlayDismissRef.current = true;
    onDismissPostKeepOverlay();
  };

  return (
    <div
      className={`${styles.bar} ${confirm ? styles.barConfirm : ''} ${prominent ? styles.barProminent : ''}`}
    >
      <input
        className={styles.input}
        type="text"
        placeholder="Describe a vibe, genre, or what you want to make…"
        data-testid="prompt-input"
        value={value}
        onChange={(e) => {
          if (onDismissPostKeepOverlay) tryDismissOverlay();
          onChange(e.target.value);
        }}
        onKeyDown={(e) => {
          if (onDismissPostKeepOverlay) {
            const typing =
              (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) ||
              e.key === 'Backspace' ||
              e.key === 'Delete';
            if (typing) tryDismissOverlay();
          }
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!disabled && !loading) onGenerate();
          }
        }}
        disabled={disabled || loading}
      />
      <div className={`${styles.actions} ${confirm ? styles.actionsConfirm : ''}`}>
        <button
          type="button"
          className={`${styles.btn} ${confirm ? styles.btnKeepLead : ''}`}
          onClick={onKeep}
          disabled={disabled}
          data-testid="keep-button"
        >
          Keep
        </button>
        <button
          type="button"
          className={`${styles.btn} ${confirm ? styles.btnSecondaryLead : ''}`}
          onClick={onRegen}
          disabled={disabled}
        >
          Try Again
        </button>
        <button
          type="button"
          className={`${styles.btn} ${confirm ? styles.btnSecondaryLead : ''}`}
          onClick={onVary}
          disabled={disabled}
        >
          Vary
        </button>
        <button
          type="button"
          className={styles.generate}
          onClick={onGenerate}
          disabled={loading || !value.trim()}
          data-testid="generate-button"
        >
          {loading ? '…' : 'Generate'}
        </button>
      </div>
    </div>
  );
}
