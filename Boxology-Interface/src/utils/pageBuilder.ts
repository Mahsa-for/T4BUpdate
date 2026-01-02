import { v4 as uuidv4 } from 'uuid';

export type BoxologyModel = {
  nodeDataArray: any[];
  linkDataArray: any[];
};

export type PageData = {
  id: string;
  name: string;
  nodeDataArray: any[];
  linkDataArray: any[];
};

export type PagesBuildResult = {
  pages: PageData[];
};

// Normalize: clean up the model
function normalizeModel(model: any): BoxologyModel {
  const clone = JSON.parse(JSON.stringify(model || { nodeDataArray: [], linkDataArray: [] }));
  return clone;
}

// Recursively build VS Code "pages" from a hierarchical model
export function buildPagesFromModel(
  model: BoxologyModel,
  mainName = 'Main Page'
): PagesBuildResult {
  const normalized = normalizeModel(model);
  const pages: PageData[] = [];

  const pageId = uuidv4();
  // Keep original node data (already normalized)
  const page: PageData = {
    id: pageId,
    name: mainName,
    nodeDataArray: normalized.nodeDataArray || [],
    linkDataArray: normalized.linkDataArray || [],
  };
  pages.push(page);

  return { pages };
}