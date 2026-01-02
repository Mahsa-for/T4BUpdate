export interface ShapeDefinition {
  name: string; // Optional for shapes that don't have a specific name
  label: string;
  shape: string;
  color: string;
  group: string;
  stroke: string; // Optional stroke color
  borderRadius?: string; // Optional border radius for rounded shapes
}

// New interfaces for patterns
export interface PatternShape {
  key: string;
  label: string;
  shape: string;
  color: string;
  stroke: string;
  loc: string;
  width: number;
  height: number;
}

export interface PatternLink {
  from: string;
  to: string;
}

export interface PatternDefinition {
  name: string;
  description: string;
  shapes: PatternShape[];
  links: PatternLink[];
  dimensions: {
    width: number;
    height: number;
  };
  group?: string;
  isPattern: true; // Flag to distinguish from individual shapes
}

// Union type for both individual shapes and patterns
export type LibraryItem = ShapeDefinition | PatternDefinition;
