**MSAnalyzer** is a powerful, user‑friendly Python toolkit that converts raw mass‑spectrometry ASCII data into structured CSVs and publication‑quality visualizations.  With both command‑line and graphical interfaces, MSAnalyzer accelerates your workflow from raw instrument output to ready‑to‑publish figures.

## Features

* **Robust ASCII Parsing**

  * Automatically detects multiple `FUNCTION` sections in raw data files
  * Exports each function’s scans and intensities into individual CSV files
* **High‑Quality Plotting**

  * Generates high‑resolution PNG (300 DPI) plots of intensity vs. retention time
  * Sensible default styles aligned with scientific publication standards
* **Integrated GUI**

  * Tabbed interface (Tkinter) with three workspaces:

    * **Load & Parse**: Select raw files or existing CSVs and specify output directory
    * **Plot & Customize**: Choose loaded functions, filter m/z traces, adjust figure size/DPI, and preview plots inline
    * **CSV Viewer**: Load and inspect any CSV in a scrollable table
* **Modular, Extensible Design**

  * Core parsing and plotting logic separated from UI code
  * Can be imported as a library to integrate into other Python projects

## Installation

Ensure you have Python 3.8 or later installed.  Then install dependencies:

```bash
pip install pandas matplotlib
```

*Tkinter is included in most Python distributions.*

## Usage

### Command‑Line Interface

MSAnalyzer’s primary entry point is `msanalyzer.py`:

```bash
python msanalyzer.py [options]
```

* **Parsing only**

  ```bash
  python msanalyzer.py --parse file1.txt file2.txt --outdir results/
  ```

  Parses raw ASCII files into `results/csv/*.csv` and `results/plots/*.png`.

* **Plotting only**

  ```bash
  python msanalyzer.py --plot results/csv/Base_Function_1.csv --outdir results/plots/
  ```

  Generates a high‑res plot from an existing CSV.

* **Full GUI**

  ```bash
  python msanalyzer.py --gui
  ```

  Launches the interactive tabbed application for parsing, plotting, and CSV viewing.

Use `-h` or `--help` to see all available options.

### Graphical Interface

After running:

```bash
python msanalyzer.py --gui
```

1. **Load & Parse**: Select raw ASCII files or existing CSVs, set an output directory, then parse and save.
2. **Plot & Customize**: Pick any loaded function, filter m/z values, modify figure settings, and preview plots.
3. **CSV Viewer**: Open any CSV for quick inspection.

## Repository Structure

```text
msanalyzer.py               # Main script (CLI and GUI)
functions_csv/              # Default output for parsed CSVs (empty)
plots/                      # Default output for generated plots (empty)
README.md                   # This documentation
requirements.txt            # Python dependencies
.gitignore                  # Files and folders to ignore
```

## Contributing

Contributions, issues, and feature requests are welcome!  Please fork the repository and submit a pull request.  Ideas:

* Batch processing mode
* Additional plot types (e.g. log scale, multiple overlays)
* Support for other mass‑spec data formats

## License

MSAnalyzer is released under the MIT License.  See [LICENSE](LICENSE) for details.
