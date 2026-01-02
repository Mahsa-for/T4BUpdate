## 🖋️  [Elementary Pattern in DOT Language](https://github.com/SDM-TIB/Tool4Boxology/tree/990d1d8fe63f9c2451a199222345b4aa3a58c7ab/ElementaryPattern).

This repository also includes Boxology representations written in **DOT language**—a plain text graph description syntax used with Graphviz. These patterns are used **only for visualization purposes**, **not for validation**.

You can view and edit them using tools like the [Graphviz Visual Editor](https://magjac.com/graphviz-visual-editor/). Either insert shapes manually or copy code from the provided `Vocabulary` file. Each **elementary pattern** is implemented in its own file, reflecting the modular design philosophy of Boxology.

> 🔄 **Important Notes**:
> - **DOT is case-sensitive** (`Symbol` ≠ `symbol`)
> - Each node must have a **unique identifier**. For example, if you use two `Symbol` nodes, name them `Symbol1` and `Symbol2`; otherwise, Graphviz will merge them.
> - Use `rankdir=LR` or `rankdir=TB` to organize the layout direction of your diagrams.

Although DOT helps visualize Boxology structures clearly, it does **not** enforce logic validation. For pattern validation, use the plugin provided in `BoxologyValidation.js` within the Draw.io environment.
