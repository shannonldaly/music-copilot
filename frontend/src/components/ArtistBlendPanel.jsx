import styles from './ArtistBlendPanel.module.css';

function bulletList(items) {
  if (!items?.length) return null;
  return (
    <ul className={styles.bullets}>
      {items.map((item, i) => (
        <li key={i} className={styles.bulletItem}>
          {item}
        </li>
      ))}
    </ul>
  );
}

export default function ArtistBlendPanel({ data }) {
  if (!data || typeof data !== 'object') return null;

  const a1 = data.artist_1 ?? data.artist1 ?? '';
  const a2 = data.artist_2 ?? data.artist2 ?? '';
  const desc = data.blend_description ?? data.blendDescription ?? '';
  const from1 = data.from_artist_1 ?? data.fromArtist1 ?? [];
  const from2 = data.from_artist_2 ?? data.fromArtist2 ?? [];
  const prod = data.production_direction ?? data.productionDirection ?? '';

  if (!a1 && !a2 && !desc && !prod && !from1.length && !from2.length) return null;

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h2 className={styles.headline}>
          {a1 && a2 ? (
            <>
              {a1} <span className={styles.times}>×</span> {a2}
            </>
          ) : (
            'Artist blend'
          )}
        </h2>
      </header>

      {desc ? (
        <p className={styles.description}>{desc}</p>
      ) : null}

      <div className={styles.columns}>
        <div className={styles.col}>
          <div className={styles.colLabel}>From {a1 || 'Artist 1'}</div>
          {bulletList(from1)}
        </div>
        <div className={styles.col}>
          <div className={styles.colLabel}>From {a2 || 'Artist 2'}</div>
          {bulletList(from2)}
        </div>
      </div>

      {prod ? (
        <div className={styles.production}>
          <div className={styles.sectionLabel}>Production direction</div>
          <div className={styles.productionBody}>{prod}</div>
        </div>
      ) : null}
    </section>
  );
}
