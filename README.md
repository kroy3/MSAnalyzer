# MSAnalyzer

**MSAnalyzer** is a powerful, user-friendly Python toolkit that converts raw mass-spectrometry data into structured CSV files and publication-quality visualizations.  It supports both ASCII (`.txt`) and NetCDF (`.cdf`) file formats, and offers both command-line and GUI workflows for data parsing, exploration, and export.

---

## 🚀 Key Features

- **Multi‐format Parsing**  
  - Reads raw ASCII files with multiple `FUNCTION` blocks  
  - Parses NetCDF/CDF files via `netCDF4` (or `scipy` fallback)  
  - Standardizes output to columns: `Scan`, `Retention Time`, `Channel`, `Intensity`  

- **Publication‐Quality Plotting**  
  - Matplotlib/Seaborn backend with sensible fonts, line widths, and 300 DPI output  
  - Optional Plotly backend for interactive charts  
  - Compact legends (channel numbers only)  

- **Graphical User Interface**  
  - **Load & Parse** – Select raw files & output folder; parse files into CSV + PNG  
  - **Plot & Customize** – Choose function & channel(s), set figure size/DPI, preview plots  
  - **CSV Viewer** – Open any CSV, search/filter rows in a scrollable table  
  - **Channel Export** – Export a single channel’s data to CSV  
  - **Compare Functions** – Overlay the same channel from two functions side-by-side  
  - **Find & Replace** – Count and replace numeric values within a function’s data  

- **Modular Design**  
  - `parser.py` – ASCII & CDF parsing logic  
  - `plot_utils.py` – Headless plotting utilities  
  - `csv_viewer.py` – Interactive Tkinter-based data table  
  - `msanalyzer_gui.py` – Main GUI orchestrator  
  - `msanalyzer.py` – Single-file entry point (all features in one script)  

- **Branding**  
  - Displays your **Wang Lab** logo on the landing tab  

---

## 📦 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YourOrg/MSAnalyzer.git
   cd MSAnalyzer
