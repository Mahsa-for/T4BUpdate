import * as go from 'gojs';
import { validateEntireDiagram } from '../plugin/GoJSBoxologyValidation'; // Import the new function

export interface ValidationResult {
  status: 'valid' | 'invalid' | 'partial';
  score: number; // 0-100 percentage
  totalChecks: number;
  passedChecks: number;
  failedChecks: number;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  summary: string;
  pluginResult?: string; // Add plugin result
}

export interface ValidationError {
  type: 'critical' | 'major' | 'minor';
  category: string;
  message: string;
  nodeIds?: string[];
  linkIds?: string[];
  count?: number;
}

export interface ValidationWarning {
  type: 'performance' | 'best-practice' | 'style';
  category: string;
  message: string;
  nodeIds?: string[];
  linkIds?: string[];
  count?: number;
}

/**
 * Comprehensive diagram validation that integrates with Boxology plugin
 */
export function validateDiagram(diagram: go.Diagram): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];
  const checks: { name: string; passed: boolean; weight: number }[] = [];

  // Helper function to add check result
  const addCheck = (name: string, passed: boolean, weight: number = 1) => {
    checks.push({ name, passed, weight });
  };

  // 1. Run the Boxology validation plugin for ENTIRE DIAGRAM
  let pluginResult = '';
  let pluginPassed = false;
  
  try {
    pluginResult = validateEntireDiagram(diagram); // Use the new function
    console.log('Plugin result:', pluginResult);
    
    // Check if validation passed
    const resultLower = pluginResult.toLowerCase();
    
    // Check for explicit failure indicators
    const hasErrors = resultLower.includes('❌') || 
                     resultLower.includes('invalid diagram') ||
                     resultLower.includes('issues detected') ||
                     resultLower.includes('unmatched') ||
                     resultLower.includes('isolated') ||
                     resultLower.includes('disconnected') ||
                     resultLower.includes('empty diagram');
    
    // Check for success indicators
    const hasSuccess = resultLower.includes('✅') && 
                      resultLower.includes('valid diagram');
    
    // Plugin passes only if it has success indicators AND no error indicators
    pluginPassed = hasSuccess && !hasErrors;
    
    addCheck('Boxology Plugin Validation', pluginPassed, 5); // Very high weight
    
    if (!pluginPassed) {
      errors.push({
        type: 'critical',
        category: 'Boxology Rules',
        message: `Boxology validation failed`,
        count: 1
      });
    }
    
  } catch (error) {
    console.error('Validation plugin error:', error);
    pluginResult = `Plugin Error: ${error}`;
    pluginPassed = false;
    
    addCheck('Boxology Plugin Validation', false, 5);
    errors.push({
      type: 'critical',
      category: 'Boxology Rules',
      message: `Validation plugin error: ${error}`,
      count: 1
    });
  }

  // 2. Check if diagram is empty (Critical)
  const isEmpty = diagram.nodes.count === 0;
  addCheck('Diagram Not Empty', !isEmpty, 3);
  if (isEmpty) {
    errors.push({
      type: 'critical',
      category: 'Structure',
      message: 'Diagram is completely empty - no nodes found',
      count: 0
    });
  }

  // Calculate score (plugin result heavily influences this)
  const totalWeight = checks.reduce((sum, check) => sum + check.weight, 0);
  const passedWeight = checks.filter(check => check.passed).reduce((sum, check) => sum + check.weight, 0);
  const score = totalWeight > 0 ? Math.round((passedWeight / totalWeight) * 100) : 0;

  const passedChecks = checks.filter(check => check.passed).length;
  const failedChecks = checks.length - passedChecks;

  // Determine status - Plugin result is the primary factor
  let status: 'valid' | 'invalid' | 'partial';
  if (pluginPassed && score >= 80) {
    status = 'valid';
  } else if (!pluginPassed) {
    // If plugin fails, determine based on what kind of issues
    if (pluginResult.includes('Empty diagram')) {
      status = 'invalid';
    } else {
      status = 'partial';
    }
  } else {
    status = score >= 60 ? 'partial' : 'invalid';
  }

  // Generate summary
  const criticalErrors = errors.filter(e => e.type === 'critical').length;
  const majorErrors = errors.filter(e => e.type === 'major').length;
  const minorErrors = errors.filter(e => e.type === 'minor').length;

  let summary = `Validation Score: ${score}/100 (${status.toUpperCase()})\n`;
  summary += `Checks: ${passedChecks}/${checks.length} passed\n`;
  summary += `Boxology Plugin: ${pluginPassed ? 'PASSED' : 'FAILED'}\n`;
  if (criticalErrors > 0) summary += `Critical Issues: ${criticalErrors}\n`;
  if (majorErrors > 0) summary += `Major Issues: ${majorErrors}\n`;
  if (minorErrors > 0) summary += `Minor Issues: ${minorErrors}\n`;
  if (warnings.length > 0) summary += `Warnings: ${warnings.length}`;

  return {
    status,
    score,
    totalChecks: checks.length,
    passedChecks,
    failedChecks,
    errors,
    warnings,
    summary,
    pluginResult
  };
}

export type GoLikeModel = {
  nodeDataArray: any[];
  linkDataArray: any[];
};

// A node is considered clustered if it belongs to a user group (isGroup true node)
export function findUnclusteredNodes(model: GoLikeModel) {
  const nodes = model.nodeDataArray || [];
  const groups = new Set(
    nodes.filter((n: any) => n.isGroup).map((g: any) => String(g.key))
  );

  const bad: any[] = [];
  for (const n of nodes) {
    if (n.isGroup) continue;
    const inGroup = n.group && groups.has(String(n.group));
    if (!inGroup) bad.push(n);
  }
  return bad;
}