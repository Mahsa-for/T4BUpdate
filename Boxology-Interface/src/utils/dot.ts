export type BoxologyModel = {
  nodeDataArray: any[];
  linkDataArray: any[];
};

type ExportOpts = {
  graphLabel?: string;
  groupCategory?: string; // default 'ClusterGroup'
};

const esc = (s: any) => (s ?? '').toString().replace(/"/g, '\\"');
const idPart = (s: any) => String(s).replace(/[^A-Za-z0-9_]/g, '_');

const mapShape = (shape?: string) => {
  switch (shape) {
    case 'Rectangle': return 'box';
    case 'RoundedRectangle': return 'box';
    case 'Ellipse': return 'ellipse';
    case 'Diamond': return 'diamond';
    case 'Triangle': return 'triangle';
    case 'TriangleDown': return 'invtriangle';
    case 'Hexagon': return 'hexagon';
    case 'Parallelogram': return 'parallelogram';
    default: return 'box';
  }
};

function nodeAttrs(n: any) {
  const attrs: string[] = [];
  const label = n.label ?? n.text ?? n.name ?? n.key;
  attrs.push(`label="${esc(label)}"`);
  attrs.push(`shape=${mapShape(n.shape)}`);
  const style: string[] = [];
  if (n.shape === 'RoundedRectangle') style.push('rounded');
  style.push('filled');
  if (n.bold) style.push('bold');
  attrs.push(`style="${style.join(',')}"`);
  if (n.fill || n.color) attrs.push(`fillcolor="${esc(n.fill || n.color)}"`);
  if (n.stroke) attrs.push(`color="${esc(n.stroke)}"`);
  attrs.push(`fontname="Helvetica"`);
  return attrs;
}

// Helper function to resolve label duplicates by adding stars
function resolveLabelDuplicates(nodes: any[]): Map<string, string> {
  const labelMap = new Map<string, string>(); // maps node.key -> unique display label
  const labelCounts = new Map<string, number>(); // tracks how many times each label appears
  
  // Sort nodes by creation order (assuming key or some timestamp indicates order)
  const sortedNodes = [...nodes].filter(n => !n.isGroup).sort((a, b) => {
    // Try to sort by key if it contains timestamp/number, otherwise preserve original order
    const aKey = String(a.key);
    const bKey = String(b.key);
    return aKey.localeCompare(bKey, undefined, { numeric: true });
  });

  for (const node of sortedNodes) {
    const originalLabel = node.label || node.text || node.name || node.key;
    let uniqueLabel = originalLabel;
    
    // Check if this label already exists
    const currentCount = labelCounts.get(originalLabel) || 0;
    
    if (currentCount > 0) {
      // Add stars for duplicates
      uniqueLabel = originalLabel + '*'.repeat(currentCount);
    }
    
    labelCounts.set(originalLabel, currentCount + 1);
    labelMap.set(String(node.key), uniqueLabel);
  }
  
  return labelMap;
}

export function modelToDOT(model: BoxologyModel, opts: ExportOpts = {}): string {
  const groupCategory = opts.groupCategory ?? 'ClusterGroup';

  const lines: string[] = [];
  lines.push(`digraph ${esc(opts.graphLabel || 'Boxology')} {`);
  lines.push(`    rankdir=TB;`);
  lines.push(``);

  emitModel(lines, model, [], groupCategory);

  lines.push('}');
  return lines.join('\n');
}

function emitModel(
  lines: string[],
  model: BoxologyModel,
  pathPrefix: string[],
  groupCategory: string
) {
  const nodes = model.nodeDataArray || [];
  const links = model.linkDataArray || [];

  // Resolve label duplicates first
  const uniqueLabelMap = resolveLabelDuplicates(nodes);

  // Helper function to get unique DOT node identifier (resolved label)
  const getDotNodeId = (n: any): string => {
    return uniqueLabelMap.get(String(n.key)) || n.label || n.text || n.name || n.key;
  };

  // Helper function to get semantic type (unchanged name for validation/TTL)
  const getNodeType = (n: any): string => {
    return n.name || n.label || n.text || n.key;
  };

  // User groups (clusters)
  const groups = nodes.filter((n: any) => n.isGroup && (!n.category || n.category === groupCategory));
  const groupMembers: Record<string, any[]> = {};
  for (const g of groups) groupMembers[g.key] = [];
  for (const n of nodes) {
    if (!n.isGroup && n.group && groupMembers[n.group]) groupMembers[n.group].push(n);
  }

  // Emit user clusters with regular members
  for (const g of groups) {
    const gid = idPart(`${g.key}`);
    const groupLabel = g.label || g.text || g.name || g.key;
    lines.push(`    // Subgraph - ${esc(groupLabel)}`);
    lines.push(`    subgraph cluster_${gid} {`);
    lines.push(`        label="${esc(groupLabel)}";`);
    lines.push(`        style=filled;`);
    lines.push(`        color=${esc(g.color || 'lightgrey')};`);
    lines.push(``);
    
    // Define nodes with unique label as DOT ID and name as type attribute
    for (const n of (groupMembers[g.key] || [])) {
      const dotNodeId = getDotNodeId(n);
      const nodeType = getNodeType(n);
      const shape = mapShape(n.shape);
      const fillcolor = n.fill || n.color || 'white';
      const style = n.style || 'filled';
      
      lines.push(`        "${esc(dotNodeId)}" [label="${esc(dotNodeId)}", type="${esc(nodeType)}", shape=${shape},style=filled ,fillcolor="${esc(fillcolor)}"];`);
    }
    
    lines.push(`        `);
    lines.push(`    }`);
    lines.push(``);
  }

  // Emit nodes not in any user group
  for (const n of nodes) {
    if (n.isGroup) continue;
    const inUserGroup = !!n.group && groups.some((g: any) => g.key === n.group);
    if (inUserGroup) continue;
    
    const dotNodeId = getDotNodeId(n);
    const nodeType = getNodeType(n);
    const shape = mapShape(n.shape);
    const style = n.style || 'filled';
    const fillcolor = n.fill || n.color || 'white';

    lines.push(`    "${esc(dotNodeId)}" [label="${esc(dotNodeId)}", type="${esc(nodeType)}", shape=${shape}, style=filled, fillcolor="${esc(fillcolor)}"];`);
  }

  // Emit edges at the end, using unique DOT node IDs
  if (links && links.length > 0) {
    for (const l of links) {
      const fromNode = nodes.find((n: any) => n.key === l.from);
      const toNode = nodes.find((n: any) => n.key === l.to);
      
      if (fromNode && toNode) {
        const fromDotId = getDotNodeId(fromNode);
        const toDotId = getDotNodeId(toNode);
        
        lines.push(`    "${esc(fromDotId)}" -> "${esc(toDotId)}";`);
      }
    }
  }
}

// Export the duplicate resolution function for use in the Boxology tool
export { resolveLabelDuplicates };