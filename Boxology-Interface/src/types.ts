export interface ShapeDefinition {
  name?: string; // Optional for shapes that don't have a specific name
  label: string;
  shape: string;
  color: string;
  group: string;
  stroke: string; // Optional stroke color
}
