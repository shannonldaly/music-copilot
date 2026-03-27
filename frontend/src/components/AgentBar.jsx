import { AGENTS } from '../constants';
import styles from './AgentBar.module.css';

/**
 * @param {Record<string, 'idle'|'firing'|'done'>} states
 */
export default function AgentBar({ states }) {
  return (
    <div className={styles.bar}>
      {AGENTS.map((a) => (
        <div key={a.id} className={styles.row}>
          <span className={styles.label}>{a.label}</span>
          <span
            className={`${styles.led} ${styles[`led_${states[a.id] || 'idle'}`]}`}
            title={`${a.label}: ${states[a.id] || 'idle'}`}
          />
        </div>
      ))}
    </div>
  );
}
