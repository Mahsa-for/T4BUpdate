import * as go from "gojs";

// Usually at the top of your file
const $ = go.GraphObject.make;

// Add this to your node template

$(go.Node, "Auto",
  new go.Binding("location", "loc", go.Point.parse).makeTwoWay(go.Point.stringify),
  // Main shape
  $(go.Shape, "RoundedRectangle",
    { fill: "white", strokeWidth: 2 },
    new go.Binding("fill", "color"),
    new go.Binding("stroke", "color")
  ),
  // Panel for label and type
  $(go.Panel, "Vertical",
    { margin: 8 },
    // Label
    $(go.TextBlock,
      { 
        margin: 4,
        font: "bold 12px sans-serif",
        editable: true
      },
      new go.Binding("text", "label").makeTwoWay()
    ),
    // Type selector (HTMLInfo dropdown)
    $(go.Panel, "Auto",
      { 
        margin: new go.Margin(4, 0, 0, 0),
        background: "#f0f0f0",
        cursor: "pointer"
      },
      $(go.Shape, "RoundedRectangle",
        { 
          fill: "#ffffff", 
          stroke: "#cccccc",
          strokeWidth: 1
        }
      ),
      $(go.TextBlock,
        { 
          margin: new go.Margin(2, 6, 2, 6),
          font: "10px sans-serif",
          stroke: "#666666"
        },
        new go.Binding("text", "type", (type) => type || "No Type")
      ),
      {
        click: (e, obj) => {
          const node = obj.part as go.Node;
          showTypeSelector(e, node);
        }
      }
    )
  )
)

// Example shapeTypes mapping node names to available types
const shapeTypes: { [key: string]: string[] } = {
  "Rectangle": ["Type A", "Type B", "Type C"],
  "Circle": ["Type X", "Type Y"],
  // Add more node names and types as needed
};

// Type selector function
function showTypeSelector(e: go.InputEvent, node: go.Node) {
  const diagram = node.diagram;
  if (!diagram) return;

  const nodeName = node.data.name;
  const availableTypes = shapeTypes[nodeName] || ["No Type"];
  
  // Create HTML dropdown
  const dropdown = document.createElement("select");
  dropdown.style.position = "absolute";
  dropdown.style.left = e.viewPoint.x + "px";
  dropdown.style.top = e.viewPoint.y + "px";
  dropdown.style.fontSize = "12px";
  dropdown.style.padding = "4px";
  dropdown.style.zIndex = "1000";
  
  // Add options
  availableTypes.forEach(type => {
    const option = document.createElement("option");
    option.value = type;
    option.text = type;
    if (type === (node.data.type || "No Type")) {
      option.selected = true;
    }
    dropdown.appendChild(option);
  });
  
  // Handle selection
  dropdown.onchange = () => {
    diagram.model.startTransaction("change type");
    diagram.model.set(node.data, "type", dropdown.value);
    diagram.model.commitTransaction("change type");
    dropdown.remove();
  };
  
  dropdown.onblur = () => {
    dropdown.remove();
  };
  
  document.body.appendChild(dropdown);
  dropdown.focus();
}