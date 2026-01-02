// exportHelpers.ts
import * as go from "gojs";

/** Normalize */
const norm = (s?: string) => (s ?? '').trim().toLowerCase();

// UPDATED: include 'embed' and common variants, detect by type/subtype/name/label
const PROCESS_TYPES = new Set<string>([
  'Train', 'Training', 'Engineer', 'Engineering','Deduce', 'Induce', 'Induction',
   'Transform', 'Embed', 'Embedding'
].map(norm));

// UPDATED: check type, then subtype, then name, then label (case-insensitive)
const isProcess = (n: any) => {
  const t = norm(n?.type ?? n?.subtype ?? n?.name ?? n?.label);
  return PROCESS_TYPES.has(t);
};

function toComponent(n: any) {
  return {
    id: n.key,
    // Prefer semantic type/subtype, then name/label
    name: n.type ?? n.subtype ?? n.name ?? n.label ?? '',
    label: n.label ?? n.text ?? n.name ?? ''
  };
}

function singleOrArray(arr: any[]) {
  if (!arr || arr.length === 0) return undefined;
  return arr;
}

/**
 * Build design patterns from raw model data (no Diagram instance needed)
 *
 * - finds ClusterGroup nodes
 * - collects member nodes
 * - finds intra-cluster links
 * - picks the process node (first matching PROCESS_TYPES)
 * - computes inputs as nodes that link -> process (from anywhere)
 * - computes outputs as nodes that link <- process (to anywhere)
 * - exports only id,label,input,output,process for each cluster
 */
export function buildDesignPatternsFromModelData(
  nodeDataArray: any[],
  linkDataArray: any[]
) {
  const nodeByKey = new Map<string, any>(nodeDataArray.map((n: any) => [String(n.key), n]));
  const groups = nodeDataArray.filter((n: any) => n.isGroup && n.category === 'ClusterGroup');

  const links = (linkDataArray ?? []).map((l: any) => ({
    from: String(l.from),
    to: String(l.to),
    raw: l
  }));

  const patterns: any[] = [];

  for (const g of groups) {
    const gKey = String(g.key);

    // members of this cluster
    const members = nodeDataArray.filter((n: any) => !n.isGroup && String(n.group) === gKey);
    const memberKeys = new Set(members.map(m => String(m.key)));

    // intra-cluster links (both ends in same cluster)
    const intraLinks = links.filter(l => memberKeys.has(l.from) && memberKeys.has(l.to));

    // find process node among members (UI should enforce exactly one)
    const processNodes = members.filter(isProcess);
    const processNode = processNodes[0] ?? null;

    // direct inputs: nodes (anywhere) that have a link -> process
    const inputNodes = processNode
      ? links
          .filter(l => l.to === String(processNode.key))
          .map(l => nodeByKey.get(l.from))
          .filter(Boolean)
      : [];

    // direct outputs: nodes (anywhere) that have a link from process
    const outputNodes = processNode
      ? links
          .filter(l => l.from === String(processNode.key))
          .map(l => nodeByKey.get(l.to))
          .filter(Boolean)
      : [];

    // fallback: if no process, treat cluster sources/sinks as inputs/outputs (intra-cluster)
    let inputs = inputNodes;
    let outputs = outputNodes;
    if (!processNode) {
      const incomingSet = new Set(intraLinks.map(l => l.to));
      const outgoingSet = new Set(intraLinks.map(l => l.from));
      const sources = members.filter(m => !incomingSet.has(String(m.key)));
      const sinks = members.filter(m => !outgoingSet.has(String(m.key)));
      inputs = sources;
      outputs = sinks;
    }

    const pattern: any = {
      id: g.key,
      label: g.label ?? g.text ?? 'Cluster'
    };

    const mappedInputs = inputs.map(toComponent);
    const mappedOutputs = outputs.map(toComponent);

    const mappedProcess = processNode ? toComponent(processNode) : undefined;

    if (mappedInputs.length > 0) pattern.input = singleOrArray(mappedInputs);
    if (mappedOutputs.length > 0) pattern.output = singleOrArray(mappedOutputs);
    if (mappedProcess) pattern.process = mappedProcess;

    patterns.push(pattern);
  }

  return patterns;
}

/**
 * Create a stable id from topology (node keys + links). Deterministic across loads.
 */
export function generateStableIdFromData(nodeDataArray: any[] = [], linkDataArray: any[] = []) {
  const nodeKeys = (nodeDataArray ?? []).map(n => String(n.key)).sort();
  const linkReprs = (linkDataArray ?? []).map(l => `${String(l.from)}->${String(l.to)}`).sort();
  const seed = JSON.stringify({ nodes: nodeKeys, links: linkReprs });


  // djb2 hash (returns hex)
  let hash = 5381;
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash << 5) + hash) + seed.charCodeAt(i);
    // keep 32-bit
    hash = hash & 0xffffffff;
  }
  const hex = (hash >>> 0).toString(16);
  return `box_${hex}`;
}

export function normalizeNodeKey(key: any): string {
  if (typeof key === 'number' && key < 0) {
    // Convert negative keys to positive unique strings
    return `node_${Math.abs(key)}${Date.now()}`;
  }
  return String(key);
}
export function normalizeModelData(nodeDataArray: any[], linkDataArray: any[]): {
  nodeDataArray: any[];
  linkDataArray: any[];
  keyMap: Map<string, string>;
} {
  const keyMap = new Map<string, string>();

  // First pass: create mapping for all negative keys
  nodeDataArray.forEach(node => {
    const oldKey = String(node.key);
    if (typeof node.key === 'number' && node.key < 0) {
      const newKey = normalizeNodeKey(node.key);
      keyMap.set(oldKey, newKey);
    } else {
      keyMap.set(oldKey, oldKey);
    }
  });

  // Second pass: apply mapping to nodes
  const normalizedNodes = nodeDataArray.map(node => ({
    ...node,
    key: keyMap.get(String(node.key)) || node.key,
    group: node.group ? (keyMap.get(String(node.group)) || node.group) : node.group
  }));

  // Third pass: apply mapping to links
  const normalizedLinks = linkDataArray.map(link => ({
    ...link,
    from: keyMap.get(String(link.from)) || link.from,
    to: keyMap.get(String(link.to)) || link.to
  }));

  return {
    nodeDataArray: normalizedNodes,
    linkDataArray: normalizedLinks,
    keyMap
  };
}

/**
 * Generate a UUID v4 (RFC 4122 compliant)
 * Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
 */
export function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export const generateMultiPageRMLExport = (pages: any[]): any => {
  if (!pages || pages.length === 0) {
    throw new Error('No diagrams available. Please create at least one diagram before generating a knowledge graph.');
  }
  
  // Check if all pages are empty (no nodes or only empty diagrams)
  const hasContent = pages.some(page => {
    const nodeDataArray = page.nodeDataArray ?? [];
    return nodeDataArray.length > 0;
  });

  if (!hasContent) {
    throw new Error('All diagrams are empty. Please add shapes to at least one diagram before generating a knowledge graph.');
  }
  const boxologies = pages.map((page, idx) => {
    // Normalize keys first
    const { nodeDataArray, linkDataArray } = normalizeModelData(
      page.nodeDataArray ?? [],
      page.linkDataArray ?? []
    );

    const patterns = buildDesignPatternsFromModelData(nodeDataArray, linkDataArray);

    // Use UUID instead of box_[hex]
    const id = page.boxologyId ?? generateUUID();
    if (!page.boxologyId) page.boxologyId = id;

    const label = page.name || page.boxologyLabel || `Diagram ${idx + 1}`;
    page.boxologyLabel = label;

    return {
      id,  
      label,   
      DesignPattern: patterns
    };
  });

  return { boxologies };
};
