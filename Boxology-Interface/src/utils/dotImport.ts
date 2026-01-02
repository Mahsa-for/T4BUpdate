import { parse } from '@ts-graphviz/parser';

export type BoxologyModel = {
  nodeDataArray: any[];
  linkDataArray: any[];
};

type Attrs = Record<string, string>;

const asArray = (v: any) => (Array.isArray(v) ? v : v ? [v] : []);
const toLower = (v: any) => String(v || '').toLowerCase();

function attrsToMap(a: any): Attrs {
  const map: Attrs = {};
  if (!a) return map;
  // parser represents attributes differently across versions; normalize
  const lists = asArray(a);
  for (const list of lists) {
    const items = list?.children || list?.attributes || list;
    const arr = asArray(items);
    for (const it of arr) {
      const k =
        it?.children?.[0]?.value ??
        it?.key?.value ??
        it?.key ??
        it?.id ??
        it?.name;
      const v =
        it?.children?.[1]?.children?.[0]?.value ??
        it?.children?.[1]?.value ??
        it?.value ??
        it?.val ??
        '';
      if (k != null) map[String(k)] = String(v ?? '');
    }
  }
  return map;
}

const getId = (s: any) =>
  typeof s === 'string'
    ? s
    : s?.id?.value ?? s?.id ?? s?.value ?? s?.name ?? '';

const getStatements = (node: any): any[] =>
  asArray(node?.children || node?.statements || node?.body?.children || node?.body);

const lastPathPart = (path: string) => {
  const parts = (path || '').split('/').filter(Boolean);
  return parts.length ? parts[parts.length - 1] : path || '';
};

const keyFromNodeId = (id: string) => {
  let s = id.replace(/^n_/, '');
  s = s.replace(/__hdr$/, '');
  const parts = s.split('__');
  return parts[parts.length - 1] || s;
};

// Extract first two ids from an edge statement (supports a->b->c; we take (a,b) and (b,c) in caller)
function edgeTargetIds(st: any): string[] {
  const t = st?.targets || st?.nodes || st?.children || [];
  const arr = asArray(t).map(getId).filter(Boolean);
  if (arr.length >= 2) return [arr[0], arr[1]];
  // fallback: look deeper
  const deep: string[] = [];
  asArray(t).forEach((x: any) => {
    const id = getId(x);
    if (id) deep.push(id);
    const id2 = getId(x?.id);
    if (id2) deep.push(id2);
  });
  return deep.slice(0, 2);
}

// Recursively parse a graph/subgraph into our model
function parseGraph(ast: any): BoxologyModel {
  const nodeDataArray: any[] = [];
  const linkDataArray: any[] = [];

  // id → node key mapping
  const idToKey = new Map<string, string>();

  const stmts = getStatements(ast);

  // First pass: handle subgraphs (clusters) and nodes
  for (const st of stmts) {
    const kind = toLower(st?.type || st?.constructor?.name || st?.kind);
    if (kind.includes('subgraph')) {
      // User cluster or any subgraph: merge its members at this level
      const inner = parseGraph(st);
      nodeDataArray.push(...inner.nodeDataArray);
      linkDataArray.push(...inner.linkDataArray);
      continue;
    }

    if (kind.includes('node')) {
      const nid = getId(st?.id);
      const a = attrsToMap(st?.attributes);
      const key = lastPathPart(a['path']) || keyFromNodeId(nid);
      const node: any = {
        key,
        label: a['label'] ?? key
      };
      // shape
      if (a['shape']) {
        node.shape =
          a['shape'] === 'box'
            ? 'Rectangle'
            : a['shape'] === 'ellipse'
            ? 'Ellipse'
            : a['shape'] === 'diamond'
            ? 'Diamond'
            : a['shape'];
      }
      if (a['fillcolor']) node.color = a['fillcolor'];
      if (a['color']) node.stroke = a['color'];
      nodeDataArray.push(node);
      idToKey.set(nid, key);
    }
  }

  // Second pass: edges
  for (const st of stmts) {
    const kind = toLower(st?.type || st?.constructor?.name || st?.kind);
    if (kind.includes('edge')) {
      // Support simple a->b and chained edges by walking consecutive pairs
      const t = st?.targets || st?.nodes || st?.children || [];
      const seq = asArray(t).map(getId).filter(Boolean);
      for (let i = 0; i < seq.length - 1; i++) {
        const fromId = seq[i];
        const toId = seq[i + 1];
        const fromKey = idToKey.get(fromId) || keyFromNodeId(fromId);
        const toKey = idToKey.get(toId) || keyFromNodeId(toId);
        if (fromKey && toKey) linkDataArray.push({ from: fromKey, to: toKey });
      }
      // Fallback if not chained
      if (seq.length < 2) {
        const [a, b] = edgeTargetIds(st);
        const fromKey = a && (idToKey.get(a) || keyFromNodeId(a));
        const toKey = b && (idToKey.get(b) || keyFromNodeId(b));
        if (fromKey && toKey) linkDataArray.push({ from: fromKey, to: toKey });
      }
    }
  }

  return { nodeDataArray, linkDataArray };
}

export function parseDOTToModel(dot: string): BoxologyModel {
  const ast = parse(dot);
  const graphNode = Array.isArray(ast) ? ast[0] : ast;
  return parseGraph(graphNode);
}