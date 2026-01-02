# Boxology-Interface

This module contains a custom **web-based interface** for designing hybrid AI systems using **Boxology** principles. It is built with **React**, **TypeScript**, **Vite**, and **GoJS**, and provides an interactive diagramming environment for creating modular, validated AI system architectures. The interface enables **Knowledge Graph generation** from your diagrams and provides seamless integration with **Virtuoso** for semantic querying and validation.

⚠️ **Note:** This interface is under **active development**. New features and visual enhancements are being added frequently.

---

## ✨ Features

- 📦 **Drag-and-drop Boxology components** - Interactive shape library with custom shapes
- 🔗 **Connect components** with semantically meaningful edges
- 🎯 **Clustering support** - Group and organize processes in neural-symbolic systems
- 🧠 **Knowledge Graph Generation** - Automatically generate knowledge graphs from diagrams
- 🔍 **Virtuoso Integration** - Navigate to SPARQL endpoint for querying generated knowledge graphs
- 📊 **Organized workspace** - Clean, intuitive interface for complex system design
- 💾 **Multiple Export Formats** - Export as JSON, DOT (Graphviz), PNG, and styled JSON for reuse
- 🆔 **Unique Component IDs** - Each Boxology component has a stable ID for KG updates and reusability
- ✅ **Real-time validation** - Validate your architecture against Boxology patterns
- 🎨 **Visual customization** - Customize shapes and save styling for future projects

#### **Knowledge Graph Features**
- **🔄 Active KG Generation**: Real-time knowledge graph creation as you build diagrams
- **🔗 Virtuoso Integration**: Direct connection to Virtuoso SPARQL endpoint for querying
- **🚀 Navigate to SPARQL**: One-click navigation to Virtuoso Conductor for interactive querying
- **🆔 Stable Identifiers**: Each component maintains unique, persistent IDs across updates
- **📋 Two JSON Export Types**: 
  - Standard JSON for knowledge graph creation
  - Styled JSON preserving visual layout for diagram reuse

#### **Data Persistence & Integrity**
- **Complete KG Preservation**: All semantic relationships preserved in RDF format
- **Two-Format JSON Support**: 
  - **KG JSON**: Optimized for knowledge graph generation and Virtuoso upload
  - **Styled JSON**: Full visual and structural data for loading and editing diagrams later
- **Stable ID System**: Components maintain unique identifiers enabling KG updates and incremental changes
- **Virtuoso Synchronization**: Seamless upload and query workflow with triple store
- **Export Compatibility**: Full support across JSON, RDF/Turtle, DOT, and image formats

### 🎯 Workflow Example

1. **Create Main Architecture**: Design your top-level AI system components
2. **Define Clustering**: Use containers to group and specify each process in your neural-symbolic system
3. **Assign Component IDs**: Each Boxology component receives a unique, stable identifier
4. **Preview & Validate**: Validate your architecture against Boxology patterns in real-time
5. **Generate KG Actively**: Knowledge graph is generated automatically as you design
6. **Save for Later**: Export as styled JSON to preserve layout and reload for future editing
7. **Export for KG Creation**: Export as standard JSON or RDF/Turtle
8. **Upload to Virtuoso**: Generate and upload knowledge graph to Virtuoso triple store
9. **Query with SPARQL**: Navigate to Virtuoso interface to query your AI architecture
10. **Visualize with Graphviz**: Navigate to Graphviz to preview and export as DOT language

---

## 🧰 Built With

- [React](https://reactjs.org/) - Frontend framework
- [Vite](https://vitejs.dev/) - Build tool and development server
- [TypeScript](https://www.typescriptlang.org/) - Type-safe JavaScript
- [GoJS](https://gojs.net/) - Interactive diagramming library
- [Material-UI](https://mui.com/) - React component library
- [React Router](https://reactrouter.com/) - Client-side routing
- [FastAPI](https://fastapi.tiangolo.com/) - Backend API framework (Python)
- [Virtuoso](https://virtuoso.openlinksw.com/) - RDF triple store and SPARQL endpoint
- [Graphviz](https://graphviz.org/) - Graph visualization tool
- [RDFLib](https://rdflib.readthedocs.io/) - Python library for RDF processing

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v16 or higher)
- Python 3.8+
- Docker and Docker Compose

### Option 1: Manual Setup

#### 1. Start Virtuoso in Docker
```bash
docker run -d -p 8890:8890 --name virtuoso kemele/virtuoso:7-stable

```

#### 2. Start Backend API
```bash
cd backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --reload-dir src  
```

#### 3. Start Frontend Interface
```bash
cd Boxology-Interface
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

### Option 2: Docker Compose (Recommended)

```bash
# From the root directory
docker-compose up -d
```

This will start:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Virtuoso**: http://localhost:8890/sparql (SPARQL endpoint)

#### Access Virtuoso Conductor
- URL: http://localhost:8890/conductor
- Username: `dba`
- Password: `dba`

---

## 📂 Folder Structure

| Folder/File              | Purpose                                           |
|--------------------------|---------------------------------------------------|
| `src/`                   | React components and diagram logic                |
| `src/components/`        | UI components (Toolbar, Sidebars, Dialogs)        |
| `src/utils/`             | Utility functions for export, validation, KG gen  |
| `src/utils/exportHelpers.ts` | KG generation and ID management             |
| `src/pages/`             | Page components (HomePage, ToolPage)              |
| `backend/`               | FastAPI backend for KG generation and Virtuoso    |
| `backend/kg_generator/`  | Knowledge graph generation logic                  |
| `public/`                | Static assets                                     |
| `docker-compose.yml`     | Docker orchestration configuration                |
| `vite.config.ts`         | Vite build configuration                          |
| `tsconfig.json`          | TypeScript settings                               |

---

## 🔧 Planned Improvements

We are working continuously to improve the UI, stability, and knowledge graph capabilities of the Boxology Interface.

---

## 📄 License

- Code is licensed under the [MIT License](../LICENSE)
- UI diagrams and Boxology shapes are under [CC BY 4.0 License](../LICENSE-CC-BY-4.0)

---

## 🧠 Acknowledgments

This project uses [GoJS](https://gojs.net/) for diagram rendering.  
We currently use the **evaluation version**, which includes a watermark, in compliance with the GoJS [license agreement](https://gojs.net/latest/license.html).

For commercial use or removal of the watermark, a license from [Northwoods Software](https://nwoods.com/) is required.

---

## 🙋 Contact & Support

**Developed by:** Mahsa Forghani Tehrani  
📧 **Email:** mahsa.forghani.tehrani@stud.uni-hannover.de  
📚 **Documentation:** [GitHub Repository](https://github.com/SDM-TIB/Tool4Boxology.git)

For questions, suggestions, or collaboration opportunities regarding knowledge graph generation and semantic AI system design, please don't hesitate to reach out.
