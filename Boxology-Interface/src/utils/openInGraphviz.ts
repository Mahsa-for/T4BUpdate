export type GraphvizEngine = 'dot' | 'neato' | 'fdp' | 'sfdp' | 'twopi' | 'circo';

export function openInGraphviz(dot: string, engine: GraphvizEngine = 'dot') {
  const base = 'https://magjac.com/graphviz-visual-editor/';
  const url = `${base}?dot=${encodeURIComponent(dot)}&engine=${encodeURIComponent(engine)}`;
  window.open(url, '_blank', 'noopener,noreferrer');
}