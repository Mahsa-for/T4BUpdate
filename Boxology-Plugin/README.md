# 📦 Boxology Plugin & Vocabulary Library

A plugin and validation tool for Hyberid AI System modeling using Boxology methodology. This library and plugin ensure the construction of valid design patterns by enforcing logic and flow rules in both **web** and **app** environments.

---

## 🔍 Overview

This repository contains:

- **Boxology Plugin**: A guided plugin integrated into diagramming environments (like Draw.io) for constructing Boxology patterns.
- **Vocabulary Library**: A modular vocabulary model (see `.drawio` file) for representing components and their relations in knowledge-based or AI systems.

---

## 🚀 Features

- ✅ Validates logical flow and component connectivity  
- 🔁 Prevents invalid or dangling edges  
- ♻️ Merges duplicate nodes automatically    
- 🛠️ Toolbar integration for quick validation and debugging  

---
## 🌐 Web Version Usage

1. **Open Draw.io in your browser**  
   Go to [https://app.diagrams.net](https://app.diagrams.net)

2. **Enable Developer Mode**  
   Press `F12` or `Ctrl+Shift+I` to open the Developer Tools console.

3. **Inject the Plugin**  
   Copy the entire contents of `BoxologyValidation.js` and paste it into the **Console** tab. Press `Enter` to execute.

   ✅ You'll see a message:  
   `"✅ Boxology Guided Plugin Loaded"`

4. **Import the Vocabulary**  
   - From the **File** menu, choose **Import from... > Device**
   - Select the `ShapeLib.xml` , 'PatternLin.xml' and 'AnnotationLib.xml' files to load your Boxology components

5. **Use and Validate**  
   - Drag and connect nodes from the vocabulary as needed
   - When ready, click the **"Validate Pattern"** button added to the toolbar

---

## 🖥️ Draw.io Desktop App Usage

Currently supported only in the **desktop version** of Draw.io.

### 🛠 Enable Plugin Support

1. **Modify app launch settings**  
   Go to the Draw.io app shortcut or executable properties  
   In the **Target** field, add the following flag:

   ```
   --enable-plugins
   ```
   "C:\Program Files\draw.io\Draw.io.exe" --enable-plugins"
   
   <img src="https://github.com/SDM-TIB/Tool4Boxology/blob/main/images/enable-plugin.png" width="300">

3. **Install the Plugin**  
   - Open the Draw.io app  
   - Go to **Extras > Plugins > Add...**  
   - Choose the `BoxologyValidation-v1.2.js` file from your computer

   🔗 You can download it [here](https://github.com/SDM-TIB/Tool4Boxology/blob/main/BoxologyPlugin/BoxologyValidation-v1.2.js)

4. **Restart the App**  
   After restarting, components appear in the left menu. Invalid connections will trigger error messages.

---

## 📚 Vocabulary and Structure

### Core Node Types:
- `symbol`, `data`, `symbol/data`
- `model`, `model:semantic`, `model:statistics`
- `infer:deduce`, `generate:train`, `generate:engineer`, `transform`, `transform:embed`, `actor`

### Allowed Transitions:
Defined in the plugin (`validNext` object), enforcing valid next components.

### Pattern Types:
- **Elementary Patterns**: e.g., `["symbol", "generate:train", "model"]
---

## ✅ Validation Logic

1. **Structural Validation**:
   - Ensures each process component (e.g., `infer:deduce`, `generate:train`) has both inputs and outputs.

2. **Connection Rules**:
   - Only valid transitions between component types are allowed.

3. **Pattern Detection**:
   - Automatically identifies whether a selection forms an elementary pattern.

4. **Error Handling**:
   - Detects disconnected nodes, duplicate inputs, and invalid edge targets.

---

## 🧪 Sample Workflow

1. Start with a `symbol` or `data` node.
2. Connect to `generate:train` or `transform`.
3. Link to a `model` node.
4. Validate the pattern to confirm its logic.


---

## 🧩 Contributions

Contributions to improve pattern validation, extend vocabulary, or support new platforms are welcome!
