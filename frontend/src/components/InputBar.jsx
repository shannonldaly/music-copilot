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
}) {
  const confirm = !!awaitingConfirmation;

  return (
    <div className={`${styles.bar} ${confirm ? styles.barConfirm : ''}`}>
      <input
        className={styles.input}
        type="text"
        placeholder="Describe a vibe, genre, or what you want to make…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
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
        >
          Keep
        </button>
        <button
          type="button"
          className={`${styles.btn} ${confirm ? styles.btnSecondaryLead : ''}`}
          onClick={onRegen}
          disabled={disabled}
        >
          Regen
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
        >
          {loading ? '…' : 'Generate'}
        </button>
      </div>
    </div>
  );
}
