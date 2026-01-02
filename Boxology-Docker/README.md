# 📦 Boxology-Docker

This submodule contains the Dockerized environment for the **Tool4Boxology** project. It extends the [fjudith/drawio](https://github.com/fjudith/drawio) base image with:

- 🧩 Pre-installed Boxology plugin
- 📚 Custom vocabulary libraries
- 🖼️ Sidebar preview images
- 🔧 UI enhancements to support hybrid AI system design

This setup allows you to run Draw.io locally or remotely with all Boxology extensions and libraries preloaded.

---

## 🚀 Getting Started

### 🐳 1. Prerequisites
- [Docker](https://www.docker.com/products/docker-desktop/) installed
- Optionally: `docker-compose` (if using `docker-compose.yml`)

### ▶️ 2. Build & Run the Container

```bash
git clone https://github.com/SDM-TIB/Tool4Boxology.git
cd Tool4Boxology/Boxology-Docker
docker build -t boxology-drawio .
docker run -p 8080:8080 boxology-drawio
```

Then open your browser and go to: [http://localhost:8080](http://localhost:8080)

You should see Draw.io with the Boxology plugin and components available by default.

### 🛠 3. Using docker-compose (optional)

If a `docker-compose.yml` is provided, use:
```bash
docker-compose up
```

---

## 🧩 What's Inside?

This Docker container extends Draw.io by including:

### 🔌 Plugin
- `BoxologyValidation.js` — A custom validation plugin that enforces Boxology logic constraints

### 📚 Libraries (copied to `/usr/local/tomcat/webapps/draw/lib/`):
- `PatternLib.xml` — Predefined Boxology patterns
- `ShapeLib.xml` — Reusable shape components
- `AnnotationLib.xml` — Annotation-specific components

### 🖼️ Sidebar Preview Images (copied to `/usr/local/tomcat/webapps/draw/images/`):
- `sidebar-pattern.png`
- `sidebar-shape.png`
- `sidebar-annotation.png`

### 🏁 Entrypoint
- `docker-entrypoint.sh` — Script used to start Tomcat with correct environment setup

---

## 🔍 File Structure

| File/Folder | Description |
|-------------|-------------|
| `Dockerfile` | Instructions to build a custom Draw.io container with Boxology tools |
| `docker-entrypoint.sh` | Entrypoint script to launch container properly |
| `js/plugins/` | Contains `BoxologyValidation.js` plugin logic |
| `lib/` | Contains all XML libraries used in the sidebar (patterns, shapes, annotations) |
| `images/` | Custom sidebar preview icons for the plugin libraries |

---

## 📄 License

- Code in this folder is licensed under the [MIT License](../LICENSE)
- Diagrams and plugin documentation are under [CC BY 4.0](../LICENSE-CC-BY-4.0)

---

## 🙋 Contact

For questions or help, contact:  
**Mahsa Forghani Tehrani**  
📧 mahsa.forghani.tehrani@stud.uni-hannover.de
