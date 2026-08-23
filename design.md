# UI & Design System

> **Note**: As per the prototype build plan, this project is primarily a backend detection script/pipeline designed to yield a data table for a research paper. A full web UI or Flask API is *explicitly out of scope*. However, for the purposes of a hypothetical terminal output CLI or a future demo dashboard, the following design guidelines apply.

## 1. Color Palette (Terminal & Demo Dashboard)
The theme should reflect a cybersecurity / forensic analytical tool.

- **Background (Dark Mode)**: `#0F172A` (Slate 900) - Gives a deep, professional tech vibe.
- **Card/Container**: `#1E293B` (Slate 800)
- **Primary Accent (Processing/Active)**: `#3B82F6` (Blue 500)
- **Success (Clean Resume)**: `#10B981` (Emerald 500)
- **Warning (Suspicious/Low Confidence)**: `#F59E0B` (Amber 500)
- **Danger (Keyword Stuffing Detected)**: `#EF4444` (Red 500)
- **Text (Primary)**: `#F8FAFC` (Slate 50)
- **Text (Muted/Secondary)**: `#94A3B8` (Slate 400)

## 2. Typography
If rendering charts (via Matplotlib/Seaborn) or a simple static HTML report:

- **Primary Font**: `Inter` or `Roboto` - Clean, modern, highly legible for data-heavy dashboards.
- **Monospace/Code Font**: `JetBrains Mono` or `Fira Code` - For displaying parsed JSON, thresholds, or raw text snippets.
- **Heading Styles**: Bold and tight letter-spacing for analytical headers (e.g., **MODULE A: KEYWORD DENSITY**).
- **Body Text**: Size 14px/16px, Line-height 1.5.

## 3. Visualizing Results (Data Aesthetics)
- **SHAP Value Outputs**: Use a diverging color map. Red highlights for words that pushed the score toward "Stuffed", Blue for words that pushed toward "Clean".
- **Confusion Matrices**: Use a dark-themed heatmap (Seaborn's `mako` or custom slate-to-blue gradient). White text for the numbers inside the matrix for contrast.
- **Command Line Interface (CLI)**: Use `rich` or `colorama` library in Python to print output tables with the Success/Danger colors mentioned above.
