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
}) {
  return (
    <div className={styles.bar}>
      <input
        className={styles.input}
        type="text"
        placeholder="Describe a vibe, key, or ask for a progression…"
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
      <div className={styles.actions}>
        <button type="button" className={styles.btn} onClick={onKeep} disabled={disabled}>
          Keep
        </button>
        <button type="button" className={styles.btn} onClick={onRegen} disabled={disabled}>
          Regen
        </button>
        <button type="button" className={styles.btn} onClick={onVary} disabled={disabled}>
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
