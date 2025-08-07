# MSAnalyzer

**MSAnalyzer** is a powerful, user-friendly Python toolkit that converts raw mass-spectrometry data into structured CSV files and publication-quality visualizations. It supports both ASCII (`.txt`) and NetCDF (`.cdf`) file formats, and offers both command-line and GUI workflows for data parsing, exploration, and export.

---

## 🚀 Key Features

* **Multi‑format Parsing**

  * Reads raw ASCII files with multiple `FUNCTION` blocks
  * Parses NetCDF/CDF files via `netCDF4` (or `scipy` fallback)
  * Standardizes output to columns: `Scan`, `Retention Time`, `Channel`, `Intensity`

* **Publication‑Quality Plotting**

  * Matplotlib/Seaborn backend with sensible fonts, line widths, and 300 DPI output
  * Optional Plotly backend for interactive charts
  * Compact legends (channel numbers only)

* **Graphical User Interface**

  * **Load & Parse** – Select raw ASCII/CDF files and an output folder; parse files into CSVs and PNG plots
  * **Plot & Customize** – Choose a function and channel(s), set figure size and DPI, preview plots
  * **CSV Viewer** – Open any CSV, search/filter rows in a scrollable table
  * **Channel Export** – Export a single channel’s data to CSV
  * **Compare Functions** – Overlay the same channel from two functions
  * **Find & Replace** – Count and replace numeric values within a function’s data

* **Modular Design**

  * `parser.py` – ASCII & CDF parsing logic
  * `plot_utils.py` – Plotting utilities (headless capable)
  * `csv_viewer.py` – Interactive CSV table widget
  * `msanalyzer_gui.py` – Main GUI application
  * `msanalyzer.py` – Single-file, all-in-one GUI script

---

## 📦 Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/YourOrg/MSAnalyzer.git
   cd MSAnalyzer
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

## 🎬 Usage

### GUI Mode

```bash
python msanalyzer_gui.py
```

1. **Load & Parse**: Select ASCII/CDF files, choose output directory, click **Parse Selected Files** or **Load CSV Files**.
2. **Plot & Customize**: Pick a function, select channel(s), adjust width/height/DPI, choose backend, click **Plot**.
3. **CSV Viewer**: Click **Open CSV File…** and filter with the search bar.
4. **Channel Export**: Select function and channel, click **Save Channel CSV**.
5. **Compare Functions**: Choose two functions and a common channel, click **Plot Comparison**.
6. **Find & Replace**: Select function, enter find/replace values, click **Find** or **Replace**.

### Single‑Script Mode

```bash
python msanalyzer.py
```

---

## 📂 Repository Structure

```
MSAnalyzer/
├── parser.py
├── plot_utils.py
├── csv_viewer.py
├── msanalyzer_gui.py
├── msanalyzer.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🤝 Contributing

Contributions welcome! Please fork, branch, commit, and open a PR.
Ideas: batch CLI mode, log-scale plots, support for additional file formats.

---

## 📄 License

Released under the Apache License 2.0. See `LICENSE` for details.
