````markdown
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
---

## 📦 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YourOrg/MSAnalyzer.git
   cd MSAnalyzer
````

2. Install required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

   **Requirements** (in `requirements.txt`):

   ```txt
   pandas
   matplotlib
   seaborn
   plotly
   netCDF4
   scipy
   ```

---

## 🎬 Usage

### GUI Mode

```bash
python msanalyzer_gui.py
```

1. **Load & Parse**

   * Click **Select ASCII/CDF Files** and pick your raw data
   * Click **Select Output Directory**
   * Click **Parse Selected Files** (or **Load CSV Files** to import existing CSVs)

2. **Plot & Customize**

   * Pick a **Function** from the drop-down
   * Select one or more **Channel** numbers
   * Adjust **Width**, **Height**, **DPI**, and **Backend** (Matplotlib/Plotly)
   * Click **Plot** to preview

3. **CSV Viewer**

   * Click **Open CSV File…** to load any CSV
   * Use the search bar to filter rows

4. **Channel Export**

   * Choose a **Function** and **Channel**, then click **Save Channel CSV**

5. **Compare Functions**

   * Select two **Functions** and a common **Channel**, then click **Plot Comparison**

6. **Find & Replace**

   * Choose a **Function**, enter a **Find** value, click **Find** to count occurrences
   * Enter a **Replace** value, click **Replace** to perform replacements

---

### Single‐Script Mode

If you prefer a single entry point without separate modules:

```bash
python msanalyzer.py
```

This script provides the same GUI and functionality as `msanalyzer_gui.py`.

---

## 📂 Repository Structure

```
MSAnalyzer/
├── parser.py             # ASCII & CDF parsing logic
├── plot_utils.py         # Headless plotting utilities
├── csv_viewer.py         # Interactive CSV table widget
├── msanalyzer_gui.py     # Tkinter-based GUI application
├── msanalyzer.py         # All-in-one GUI script
├── wang_lab_logo.png     # Logo displayed in the GUI
├── requirements.txt      # Python dependencies
├── .gitignore            # Files & folders excluded from Git
└── README.md             # Project overview & usage instructions
```

---

## 🤝 Contributing

Contributions are very welcome!  Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to your branch (`git push origin feature/YourFeature`)
5. Open a pull request

Feel free to suggest new features (e.g., command-line batch mode, log‐scale plots, additional file formats) by opening an issue.

---

## 📄 License

This project is released under the **MIT License**. See [LICENSE](LICENSE) for details.

```
```
