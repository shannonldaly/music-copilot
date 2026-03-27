const STEPS = 16;

/**
 * @param {Record<string, number[]>} grid - API drum grid (kick, snare, closed_hat, …)
 */
export function buildDrumRows(grid) {
  const g = grid || {};
  const kick = new Set((g.kick || []).map(Number));
  const snare = new Set((g.snare || []).map(Number));
  const hat = new Set([
    ...(g.closed_hat || []),
    ...(g.open_hat || []),
  ].map(Number));

  const rows = [
    { id: 'kick', label: 'KICK', steps: kick, color: '#f5602a' },
    { id: 'snare', label: 'SNR', steps: snare, color: '#4a9eff' },
    { id: 'hat', label: 'HAT', steps: hat, color: '#a3a3a3' },
  ];

  return { rows, stepIndices: Array.from({ length: STEPS }, (_, i) => i) };
}

export { STEPS as DRUM_STEPS };
