"""
MSAnalyzer – A comprehensive mass‑spectrometry data parser and viewer.

This module provides a graphical user interface (GUI) built on top of
Tkinter that simplifies the journey from raw instrument data to
high‑quality plots and CSV exports.  It supports both ASCII (.txt)
mass‑spectrometry files as well as the classic netCDF (.cdf) format.

Key features include:

* **Data parsing**: Extracts scans, retention times and (m/z, intensity)
  pairs from files containing multiple FUNCTION blocks.  Each function
  is written to its own CSV file for easy downstream analysis.
* **Plotting**: Generates publication‑ready figures with sensible
  defaults.  Users can customise figure size, resolution and select
  individual channels to display.  Both Matplotlib/Seaborn and
  Plotly backends are supported.
* **CSV viewer**: View any CSV file in a scrollable table without
  leaving the application.
* **Channel export**: Isolate a single channel from a function and
  save it as a standalone CSV.
* **Function comparison**: Overlay the same channel from two
  different functions to quickly assess differences.
* **Find & replace**: Search numeric values in a function and replace
  them—useful for correcting erroneous intensities or retention
  times.

The application displays a custom Wang Lab logo on the landing tab.
To bundle the logo with the application simply place ``wang_lab_logo.png``
in the same directory as this script.  When packaging as a single
executable the logo will be included automatically by most bundlers.

Author: OpenAI's ChatGPT
License: MIT
"""

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Tuple, Optional

import pandas as pd
import matplotlib
# Use the Agg backend for compatibility with bundled executables and
# headless environments.  The backend will be overridden when plots
# render into Tk canvases.
matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt
import seaborn as sns

# The Plotly import is optional.  If unavailable, the application
# gracefully falls back to Matplotlib/Seaborn.
try:
    import plotly.express as px
    import plotly.io as pio
    _PLOTLY_AVAILABLE = True
except Exception:
    _PLOTLY_AVAILABLE = False

try:
    import netCDF4
except ImportError:
    netCDF4 = None

try:
    from PIL import Image, ImageTk  # type: ignore
except ImportError:
    Image = None
    ImageTk = None


class MassSpecParser:
    """Helper class to parse mass‑spectrometry data files.

    The parser handles both ASCII files containing multiple FUNCTION
    blocks and netCDF (.cdf) files.  For ASCII data the parser
    extracts scans, retention times and m/z–intensity pairs on a
    per‑function basis.  For netCDF data the parser assumes a
    representation compatible with the mzXML/mzData conventions where
    ``scan_index``, ``point_count``, ``mass_values`` and
    ``intensity_values`` variables are present.  If the CDF file
    doesn’t conform to this expectation the parser will raise a
    ``ValueError``.
    """

    ASCII_FUNCTION_RE = re.compile(r"^FUNCTION\s+(\d+)", re.IGNORECASE)
    ASCII_SCAN_RE = re.compile(r"^Scan\s+(\d+)", re.IGNORECASE)
    ASCII_RT_RE = re.compile(r"^Retention Time\s+([0-9]*\.?[0-9]+)", re.IGNORECASE)

    @staticmethod
    def parse_ascii(path: str) -> Dict[str, pd.DataFrame]:
        """Parse a mass‑spec ASCII file and return a mapping of function labels
        to DataFrames.

        The returned dictionary maps labels of the form
        ``"<basename>_Function_<n>"`` to pandas DataFrames with four
        columns: ``Scan``, ``Retention Time``, ``m/z`` and ``Intensity``.

        Parameters
        ----------
        path : str
            Path to the ASCII file on disk.

        Returns
        -------
        dict
            Mapping from function label to a DataFrame containing the
            parsed data.
        """
        basename = os.path.splitext(os.path.basename(path))[0]
        functions: Dict[str, List[Tuple[int, float, float, float]]] = {}
        current_function: Optional[int] = None
        current_scan: Optional[int] = None
        current_rt: Optional[float] = None
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    # Skip empty lines
                    continue
                func_match = MassSpecParser.ASCII_FUNCTION_RE.match(line)
                if func_match:
                    current_function = int(func_match.group(1))
                    current_scan = None
                    current_rt = None
                    func_key = f"{basename}_Function_{current_function}"
                    functions.setdefault(func_key, [])
                    continue
                scan_match = MassSpecParser.ASCII_SCAN_RE.match(line)
                if scan_match:
                    current_scan = int(scan_match.group(1))
                    continue
                rt_match = MassSpecParser.ASCII_RT_RE.match(line)
                if rt_match:
                    try:
                        current_rt = float(rt_match.group(1))
                    except ValueError:
                        current_rt = None
                    continue
                # After a scan and retention time have been captured we
                # expect lines of the form ``<m/z> <intensity>`` separated by
                # whitespace.  Some files use tabs, others spaces.
                if current_function is not None and current_scan is not None and current_rt is not None:
                    parts = re.split(r"\s+", line)
                    if len(parts) == 2:
                        try:
                            mz_val = float(parts[0])
                            intensity = float(parts[1])
                        except ValueError:
                            # Skip malformed lines
                            continue
                        func_key = f"{basename}_Function_{current_function}"
                        functions.setdefault(func_key, []).append(
                            (current_scan, current_rt, mz_val, intensity)
                        )
        # Convert lists into DataFrames
        result: Dict[str, pd.DataFrame] = {}
        for key, rows in functions.items():
            if not rows:
                continue
            df = pd.DataFrame(rows, columns=["Scan", "Retention Time", "m/z", "Intensity"])
            df["Scan"] = df["Scan"].astype(int)
            result[key] = df
        return result

    @staticmethod
    def parse_cdf(path: str) -> Dict[str, pd.DataFrame]:
        """Parse a netCDF (.cdf) mass‑spec file into a DataFrame.

        The parser expects the file to define the following variables,
        which are part of the historical netCDF mass‑spec format used
        by many instruments:

        * ``scan_index`` (1D array, length = number of scans)
        * ``point_count`` (1D array, length = number of scans)
        * ``mass_values`` (1D array, concatenated m/z values)
        * ``intensity_values`` (1D array, concatenated intensities)
        * ``scan_acquisition_time`` (1D array, retention time per scan)

        If any of these variables are missing a ``ValueError`` is
        raised.  Each scan is assigned a sequential index starting at 1.

        Parameters
        ----------
        path : str
            Path to the .cdf file.

        Returns
        -------
        dict
            A single‑item dictionary mapping ``<basename>_Function_1`` to
            a DataFrame with columns ``Scan``, ``Retention Time``, ``m/z``
            and ``Intensity``.
        """
        if netCDF4 is None:
            raise ImportError("netCDF4 is required to read .cdf files")
        ds = netCDF4.Dataset(path)
        try:
            scan_index = ds.variables["scan_index"][:]
            point_count = ds.variables["point_count"][:]
            # m/z values may be called mass_values or mass_range in some files
            if "mass_values" in ds.variables:
                mass_values = ds.variables["mass_values"][:]
            elif "mass_range" in ds.variables:
                mass_values = ds.variables["mass_range"][:]
            elif "mz" in ds.variables:
                mass_values = ds.variables["mz"][:]
            else:
                raise KeyError("m/z values variable not found in CDF file")
            # intensities variable
            if "intensity_values" in ds.variables:
                intensity_values = ds.variables["intensity_values"][:]
            elif "intensity" in ds.variables:
                intensity_values = ds.variables["intensity"][:]
            else:
                raise KeyError("intensity values variable not found in CDF file")
            # retention time variable
            if "scan_acquisition_time" in ds.variables:
                retention_time = ds.variables["scan_acquisition_time"][:]
            elif "scan_time" in ds.variables:
                retention_time = ds.variables["scan_time"][:]
            elif "retention_time" in ds.variables:
                retention_time = ds.variables["retention_time"][:]
            else:
                raise KeyError("retention time variable not found in CDF file")
        except Exception as exc:
            ds.close()
            raise ValueError(f"Failed to parse CDF file {path}: {exc}")
        rows: List[Tuple[int, float, float, float]] = []
        n_scans = len(scan_index)
        for i in range(n_scans):
            start = int(scan_index[i])
            count = int(point_count[i])
            mz_slice = mass_values[start : start + count]
            int_slice = intensity_values[start : start + count]
            rt = float(retention_time[i]) if i < len(retention_time) else 0.0
            scan_number = i + 1
            for mz_val, inten in zip(mz_slice, int_slice):
                rows.append((scan_number, rt, float(mz_val), float(inten)))
        ds.close()
        basename = os.path.splitext(os.path.basename(path))[0]
        key = f"{basename}_Function_1"
        df = pd.DataFrame(rows, columns=["Scan", "Retention Time", "m/z", "Intensity"])
        df["Scan"] = df["Scan"].astype(int)
        return {key: df}


class MSAnalyzerApp(tk.Tk):
    """Tkinter application for mass‑spectrometry data analysis.

    This class orchestrates the GUI layout and user interactions.
    Loaded data are stored in a dictionary mapping function labels to
    pandas DataFrames.  Each tab corresponds to a discrete workflow
    (loading/parsing, plotting, viewing CSV data, exporting channels,
    comparing functions and performing find & replace).
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("MSAnalyzer")
        self.geometry("1100x760")
        # Central storage for loaded functions.  Keys are
        # human‑readable labels (e.g. ``sample_Function_1``) and values
        # are DataFrames with columns Scan, Retention Time, m/z and
        # Intensity.
        self.loaded_data: Dict[str, pd.DataFrame] = {}
        # Output directory where CSV and plot files are written.
        self.output_directory: Optional[str] = None
        # Notebook container for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        # Create each tab
        self._create_load_parse_tab()
        self._create_plot_customise_tab()
        self._create_csv_viewer_tab()
        self._create_channel_export_tab()
        self._create_compare_tab()
        self._create_find_replace_tab()

    # ------------------------------------------------------------------
    # Tab creation methods
    # ------------------------------------------------------------------
    def _create_load_parse_tab(self) -> None:
        """Construct the Load & Parse tab.

        This tab allows the user to select raw ASCII (.txt) or netCDF (.cdf)
        files and an output directory.  The files are parsed into
        DataFrames, written as CSVs, and plotted to PNGs.  Users can
        also import previously saved CSV files for further analysis.
        The tab prominently features the Wang Lab logo.
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Load & Parse")
        # Logo and welcome message
        top_frame = ttk.Frame(tab)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=10)
        # Load the logo if PIL is available
        logo_path = os.path.join(os.path.dirname(__file__), "wang_lab_logo.png")
        if Image is not None and os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path)
                # Resize to a reasonable width while maintaining aspect ratio
                ratio = min(1.0, 250.0 / float(logo_img.width))
                new_size = (int(logo_img.width * ratio), int(logo_img.height * ratio))
                logo_img = logo_img.resize(new_size, Image.LANCZOS)
                self._logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = ttk.Label(top_frame, image=self._logo_photo)
                logo_label.pack(side=tk.LEFT, padx=10)
            except Exception:
                pass  # If loading fails, skip the logo
        # Title text
        title_label = ttk.Label(
            top_frame,
            text="MSAnalyzer – Mass‑Spectrometry Data Parser and Viewer",
            font=("Helvetica", 16, "bold"),
        )
        title_label.pack(side=tk.LEFT, padx=10)
        # Buttons and file selectors
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill=tk.X, pady=20)
        select_btn = ttk.Button(
            button_frame, text="Select ASCII/CDF Files", command=self._select_raw_files
        )
        select_btn.grid(row=0, column=0, padx=5, pady=5)
        outdir_btn = ttk.Button(
            button_frame, text="Select Output Directory", command=self._select_output_directory
        )
        outdir_btn.grid(row=0, column=1, padx=5, pady=5)
        parse_btn = ttk.Button(
            button_frame, text="Parse Selected Files", command=self._parse_selected_files
        )
        parse_btn.grid(row=0, column=2, padx=5, pady=5)
        import_btn = ttk.Button(
            button_frame, text="Load CSV Files", command=self._load_csv_files
        )
        import_btn.grid(row=0, column=3, padx=5, pady=5)
        # Status text
        self.load_parse_status = tk.StringVar(value="No files parsed yet.")
        status_label = ttk.Label(tab, textvariable=self.load_parse_status, wraplength=1000)
        status_label.pack(fill=tk.X, padx=10)
        # Keep track of selected raw files
        self._selected_raw_files: List[str] = []

    def _create_plot_customise_tab(self) -> None:
        """Construct the Plot & Customise tab.

        Users can pick a loaded function, select channels to plot, adjust
        figure size and DPI, choose plotting backend (Matplotlib/Seaborn
        or Plotly) and preview the resulting figure within the app.  A
        legend shows channel numbers only (e.g. ``166``).
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Plot & Customise")
        # Top controls frame
        control_frame = ttk.Frame(tab)
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=10)
        # Function dropdown
        self.plot_func_var = tk.StringVar()
        ttk.Label(control_frame, text="Function:").grid(row=0, column=0, padx=5)
        self.plot_func_dd = ttk.Combobox(control_frame, textvariable=self.plot_func_var, state="readonly", width=40)
        self.plot_func_dd.grid(row=0, column=1, padx=5)
        self.plot_func_dd.bind("<<ComboboxSelected>>", self._update_plot_channels)
        # Channel listbox
        ttk.Label(control_frame, text="Channels (m/z):").grid(row=1, column=0, padx=5, sticky=tk.N)
        self.plot_channel_list = tk.Listbox(control_frame, selectmode=tk.MULTIPLE, height=8, width=20)
        self.plot_channel_list.grid(row=1, column=1, padx=5, sticky=tk.W)
        # Figure dimensions inputs
        ttk.Label(control_frame, text="Width (in)").grid(row=0, column=2, padx=5)
        self.width_var = tk.DoubleVar(value=8.0)
        ttk.Entry(control_frame, textvariable=self.width_var, width=6).grid(row=0, column=3, padx=5)
        ttk.Label(control_frame, text="Height (in)").grid(row=1, column=2, padx=5)
        self.height_var = tk.DoubleVar(value=5.0)
        ttk.Entry(control_frame, textvariable=self.height_var, width=6).grid(row=1, column=3, padx=5)
        ttk.Label(control_frame, text="DPI").grid(row=0, column=4, padx=5)
        self.dpi_var = tk.IntVar(value=300)
        ttk.Entry(control_frame, textvariable=self.dpi_var, width=6).grid(row=0, column=5, padx=5)
        # Backend options
        self.backend_var = tk.StringVar(value="matplotlib")
        ttk.Label(control_frame, text="Backend:").grid(row=1, column=2, padx=5, columnspan=2, sticky=tk.E)
        backends = [
            ("Matplotlib/Seaborn", "matplotlib"),
            ("Plotly", "plotly"),
        ]
        col_idx = 4
        for text, val in backends:
            rb = ttk.Radiobutton(control_frame, text=text, variable=self.backend_var, value=val)
            rb.grid(row=1, column=col_idx, padx=5, sticky=tk.W)
            col_idx += 1
        # Plot button
        plot_btn = ttk.Button(control_frame, text="Plot", command=self._plot_selected_channels)
        plot_btn.grid(row=0, column=6, padx=10, rowspan=2)
        # Canvas for plotting
        self.plot_canvas_frame = ttk.Frame(tab)
        self.plot_canvas_frame.pack(fill=tk.BOTH, expand=True)

    def _create_csv_viewer_tab(self) -> None:
        """Construct the CSV Viewer tab.

        Users may open any CSV file from disk and inspect its contents
        using a scrollable Treeview.  This is useful when the
        application has not previously parsed the file or when viewing
        external CSV data sets.
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="CSV Viewer")
        # Open button
        open_btn = ttk.Button(tab, text="Open CSV File...", command=self._open_and_display_csv)
        open_btn.pack(pady=10)
        # Frame for table
        table_frame = ttk.Frame(tab)
        table_frame.pack(fill=tk.BOTH, expand=True)
        # Scrollbars
        self.csv_tree_scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.csv_tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.csv_tree_scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        self.csv_tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        # Treeview
        self.csv_tree = ttk.Treeview(
            table_frame,
            columns=[],
            show="headings",
            yscrollcommand=self.csv_tree_scroll_y.set,
            xscrollcommand=self.csv_tree_scroll_x.set,
        )
        self.csv_tree.pack(fill=tk.BOTH, expand=True)
        self.csv_tree_scroll_y.config(command=self.csv_tree.yview)
        self.csv_tree_scroll_x.config(command=self.csv_tree.xview)

    def _create_channel_export_tab(self) -> None:
        """Construct the Channel Export tab.

        This tab lets the user select a loaded function and then a
        single m/z channel from that function.  Clicking the export
        button writes a CSV file containing only the selected channel to
        disk.
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Channel Export")
        # Function dropdown
        exp_frame = ttk.Frame(tab)
        exp_frame.pack(pady=10)
        ttk.Label(exp_frame, text="Function:").grid(row=0, column=0, padx=5)
        self.export_func_var = tk.StringVar()
        self.export_func_dd = ttk.Combobox(exp_frame, textvariable=self.export_func_var, state="readonly", width=40)
        self.export_func_dd.grid(row=0, column=1, padx=5)
        self.export_func_dd.bind("<<ComboboxSelected>>", self._update_export_channels)
        # Channel listbox
        ttk.Label(exp_frame, text="Channel (m/z):").grid(row=1, column=0, padx=5, sticky=tk.N)
        self.export_channel_list = tk.Listbox(exp_frame, selectmode=tk.SINGLE, height=8, width=20)
        self.export_channel_list.grid(row=1, column=1, padx=5, sticky=tk.W)
        # Save button
        save_btn = ttk.Button(tab, text="Save Channel CSV", command=self._save_single_channel)
        save_btn.pack(pady=10)

    def _create_compare_tab(self) -> None:
        """Construct the Compare Functions tab.

        Users can select two functions that have at least one common
        channel.  The selected channel is plotted from both functions
        on a single figure for comparison.  Only the channel number
        appears in the legend.
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Compare Functions")
        cmp_frame = ttk.Frame(tab)
        cmp_frame.pack(pady=10)
        # Function 1 dropdown
        ttk.Label(cmp_frame, text="Function A:").grid(row=0, column=0, padx=5)
        self.compare_func1_var = tk.StringVar()
        self.compare_func1_dd = ttk.Combobox(cmp_frame, textvariable=self.compare_func1_var, state="readonly", width=40)
        self.compare_func1_dd.grid(row=0, column=1, padx=5)
        self.compare_func1_dd.bind("<<ComboboxSelected>>", self._refresh_compare_channels)
        # Function 2 dropdown
        ttk.Label(cmp_frame, text="Function B:").grid(row=1, column=0, padx=5)
        self.compare_func2_var = tk.StringVar()
        self.compare_func2_dd = ttk.Combobox(cmp_frame, textvariable=self.compare_func2_var, state="readonly", width=40)
        self.compare_func2_dd.grid(row=1, column=1, padx=5)
        self.compare_func2_dd.bind("<<ComboboxSelected>>", self._refresh_compare_channels)
        # Common channels listbox
        ttk.Label(cmp_frame, text="Common Channels:").grid(row=2, column=0, padx=5, sticky=tk.N)
        self.compare_channel_list = tk.Listbox(cmp_frame, selectmode=tk.SINGLE, height=8, width=20)
        self.compare_channel_list.grid(row=2, column=1, padx=5, sticky=tk.W)
        # Plot button
        plot_cmp_btn = ttk.Button(tab, text="Plot Comparison", command=self._plot_comparison)
        plot_cmp_btn.pack(pady=10)
        # Canvas for comparison plot
        self.compare_canvas_frame = ttk.Frame(tab)
        self.compare_canvas_frame.pack(fill=tk.BOTH, expand=True)

    def _create_find_replace_tab(self) -> None:
        """Construct the Find & Replace tab.

        This tab enables the user to search for a numeric value in the
        currently selected function’s DataFrame and replace it with
        another value.  The search is applied across all numeric
        columns (Scan, Retention Time, m/z and Intensity).
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Find & Replace")
        frame = ttk.Frame(tab)
        frame.pack(pady=10)
        ttk.Label(frame, text="Function:").grid(row=0, column=0, padx=5)
        self.fr_func_var = tk.StringVar()
        self.fr_func_dd = ttk.Combobox(frame, textvariable=self.fr_func_var, state="readonly", width=40)
        self.fr_func_dd.grid(row=0, column=1, padx=5)
        ttk.Label(frame, text="Find value:").grid(row=1, column=0, padx=5)
        self.find_value_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.find_value_var).grid(row=1, column=1, padx=5)
        ttk.Label(frame, text="Replace with:").grid(row=2, column=0, padx=5)
        self.replace_value_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.replace_value_var).grid(row=2, column=1, padx=5)
        apply_btn = ttk.Button(frame, text="Apply Find & Replace", command=self._apply_find_replace)
        apply_btn.grid(row=3, column=0, columnspan=2, pady=10)

    # ------------------------------------------------------------------
    # Event handlers for Load & Parse tab
    # ------------------------------------------------------------------
    def _select_raw_files(self) -> None:
        """Prompt the user to select one or more ASCII/CDF files to parse."""
        files = filedialog.askopenfilenames(
            title="Select ASCII (.txt) or CDF (.cdf) files",
            filetypes=[
                ("Mass‑Spec Files", "*.txt *.cdf"),
                ("ASCII Files", "*.txt"),
                ("CDF Files", "*.cdf"),
                ("All Files", "*.*"),
            ],
        )
        if files:
            self._selected_raw_files = list(files)
            self.load_parse_status.set(f"Selected {len(files)} file(s).  Choose an output directory and click Parse.")

    def _select_output_directory(self) -> None:
        """Prompt the user to select an output directory."""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_directory = directory
            self.load_parse_status.set(f"Output directory set to: {directory}")

    def _parse_selected_files(self) -> None:
        """Parse the selected raw files into CSVs and plots.

        This method validates that both raw files and an output
        directory have been selected.  Each file is parsed according to
        its extension (.txt for ASCII, .cdf for netCDF).  For every
        function discovered a CSV is written to the ``csv`` subfolder
        and a publication‑quality PNG is written to the ``plots``
        subfolder within the chosen output directory.  Parsed DataFrames
        are stored in ``loaded_data``.
        """
        if not self._selected_raw_files:
            messagebox.showwarning("No files selected", "Please select ASCII/CDF files to parse.")
            return
        if not self.output_directory:
            messagebox.showwarning("No output directory", "Please select an output directory before parsing.")
            return
        # Create subdirectories
        csv_dir = os.path.join(self.output_directory, "csv")
        plots_dir = os.path.join(self.output_directory, "plots")
        os.makedirs(csv_dir, exist_ok=True)
        os.makedirs(plots_dir, exist_ok=True)
        # Parse each file
        summary_messages: List[str] = []
        for file_path in self._selected_raw_files:
            try:
                if file_path.lower().endswith(".txt"):
                    parsed = MassSpecParser.parse_ascii(file_path)
                elif file_path.lower().endswith(".cdf"):
                    parsed = MassSpecParser.parse_cdf(file_path)
                else:
                    summary_messages.append(f"Skipped unsupported file: {file_path}")
                    continue
            except Exception as exc:
                summary_messages.append(f"Failed to parse {file_path}: {exc}")
                continue
            # Write out each DataFrame and plot
            for func_label, df in parsed.items():
                self.loaded_data[func_label] = df
                csv_path = os.path.join(csv_dir, f"{func_label}.csv")
                try:
                    df.to_csv(csv_path, index=False)
                except Exception as csv_exc:
                    summary_messages.append(f"Could not write CSV {csv_path}: {csv_exc}")
                # Generate plot for each channel automatically
                try:
                    sns.set(style="whitegrid")
                    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
                    for channel, group in df.groupby("m/z"):
                        group_sorted = group.sort_values("Retention Time")
                        ax.plot(
                            group_sorted["Retention Time"],
                            group_sorted["Intensity"],
                            label=str(int(channel)) if channel.is_integer() else f"{channel:.4g}",
                        )
                    ax.set_xlabel("Retention Time")
                    ax.set_ylabel("Intensity")
                    ax.set_title(func_label)
                    ax.legend(title="Channel", fontsize=8)
                    fig.tight_layout()
                    plot_path = os.path.join(plots_dir, f"{func_label}.png")
                    fig.savefig(plot_path)
                    plt.close(fig)
                except Exception as plot_exc:
                    summary_messages.append(f"Could not plot {func_label}: {plot_exc}")
        # Refresh dropdown lists after parsing
        self._refresh_all_dropdowns()
        msg = "\n".join(summary_messages) if summary_messages else "Parsing complete."
        self.load_parse_status.set(msg)

    def _load_csv_files(self) -> None:
        """Import existing CSV files into the application.

        The user may select one or more CSV files.  Each file is
        expected to follow the naming convention ``<base>_Function_<n>.csv``
        and contain the columns ``Scan``, ``Retention Time``, ``m/z``,
        and ``Intensity``.  Files that do not conform will be
        skipped.  Loaded DataFrames are added to ``loaded_data`` and
        dropdown lists are refreshed.
        """
        files = filedialog.askopenfilenames(title="Select CSV files", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not files:
            return
        skipped = []
        for path in files:
            try:
                df = pd.read_csv(path)
                required_cols = {"Scan", "Retention Time", "m/z", "Intensity"}
                if not required_cols.issubset(df.columns):
                    skipped.append(path)
                    continue
                label = os.path.splitext(os.path.basename(path))[0]
                self.loaded_data[label] = df
            except Exception:
                skipped.append(path)
        self._refresh_all_dropdowns()
        if skipped:
            messagebox.showinfo("Import completed", f"Some files were skipped due to format issues:\n{chr(10).join(skipped)}")

    # ------------------------------------------------------------------
    # Event handlers for Plot & Customise tab
    # ------------------------------------------------------------------
    def _update_plot_channels(self, _event: Optional[object] = None) -> None:
        """Update the channel listbox when the selected function changes."""
        func = self.plot_func_var.get()
        self.plot_channel_list.delete(0, tk.END)
        if func and func in self.loaded_data:
            channels = sorted(set(self.loaded_data[func]["m/z"].unique()))
            for ch in channels:
                # Display integer channels without decimal part
                display = str(int(ch)) if float(ch).is_integer() else f"{ch:.4g}"
                self.plot_channel_list.insert(tk.END, display)

    def _plot_selected_channels(self) -> None:
        """Create a plot based on user selections in the Plot & Customise tab."""
        func = self.plot_func_var.get()
        if not func or func not in self.loaded_data:
            messagebox.showwarning("No function selected", "Please select a function to plot.")
            return
        # Get selected channels
        sel_indices = self.plot_channel_list.curselection()
        if not sel_indices:
            messagebox.showwarning("No channels", "Please select one or more channels (m/z) to plot.")
            return
        sel_channels = []
        for idx in sel_indices:
            text = self.plot_channel_list.get(idx)
            try:
                # Cast back to float for comparison
                sel_channels.append(float(text))
            except ValueError:
                continue
        df = self.loaded_data[func]
        width, height, dpi = self.width_var.get(), self.height_var.get(), self.dpi_var.get()
        backend = self.backend_var.get()
        # Clear previous plot canvas
        for widget in self.plot_canvas_frame.winfo_children():
            widget.destroy()
        # Generate figure
        if backend == "plotly" and _PLOTLY_AVAILABLE:
            # Use Plotly to create an interactive line plot
            try:
                sub = df[df["m/z"].isin(sel_channels)].copy()
                sub.sort_values(["m/z", "Retention Time"], inplace=True)
                fig = px.line(
                    sub,
                    x="Retention Time",
                    y="Intensity",
                    color="m/z",
                    labels={"m/z": "Channel"},
                    title=func,
                )
                # Set figure size
                fig.update_layout(width=int(width * dpi), height=int(height * dpi))
                # Render as static PNG for embedding into Tk
                img_bytes = pio.to_image(fig, format="png")
                if Image is None:
                    raise RuntimeError("Pillow is required to display Plotly figures in the GUI")
                from io import BytesIO

                pil_img = Image.open(BytesIO(img_bytes))
                self._plot_photo = ImageTk.PhotoImage(pil_img)
                label = ttk.Label(self.plot_canvas_frame, image=self._plot_photo)
                label.pack(fill=tk.BOTH, expand=True)
            except Exception as exc:
                messagebox.showerror("Plot error", f"Failed to generate Plotly figure: {exc}")
            return
        # Otherwise use Matplotlib/Seaborn
        try:
            sns.set(style="whitegrid")
            fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
            for ch in sel_channels:
                sub = df[df["m/z"] == ch].sort_values("Retention Time")
                ax.plot(
                    sub["Retention Time"],
                    sub["Intensity"],
                    label=str(int(ch)) if float(ch).is_integer() else f"{ch:.4g}",
                )
            ax.set_xlabel("Retention Time")
            ax.set_ylabel("Intensity")
            ax.set_title(func)
            ax.legend(title="Channel")
            fig.tight_layout()
            # Embed the Matplotlib figure into Tk
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            canvas = FigureCanvasTkAgg(fig, master=self.plot_canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as exc:
            messagebox.showerror("Plot error", f"Failed to generate plot: {exc}")

    # ------------------------------------------------------------------
    # CSV Viewer helpers
    # ------------------------------------------------------------------
    def _open_and_display_csv(self) -> None:
        """Open an arbitrary CSV and display it in the viewer tab."""
        path = filedialog.askopenfilename(title="Select a CSV file", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not path:
            return
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to read CSV: {exc}")
            return
        self._populate_csv_tree(df)

    def _populate_csv_tree(self, df: pd.DataFrame) -> None:
        """Populate the CSV treeview with the contents of a DataFrame."""
        self.csv_tree.delete(*self.csv_tree.get_children())
        # Clear existing columns
        self.csv_tree['columns'] = list(df.columns)
        for col in df.columns:
            self.csv_tree.heading(col, text=col)
            # Set column widths based on header length
            width = max(len(col) * 8, 80)
            self.csv_tree.column(col, width=width, anchor=tk.W)
        # Insert rows
        for _, row in df.iterrows():
            values = [row[col] for col in df.columns]
            self.csv_tree.insert("", tk.END, values=values)

    # ------------------------------------------------------------------
    # Channel Export helpers
    # ------------------------------------------------------------------
    def _update_export_channels(self, _event: Optional[object] = None) -> None:
        """Populate the channel list for the selected function in the Channel Export tab."""
        func = self.export_func_var.get()
        self.export_channel_list.delete(0, tk.END)
        if func and func in self.loaded_data:
            channels = sorted(set(self.loaded_data[func]["m/z"].unique()))
            for ch in channels:
                display = str(int(ch)) if float(ch).is_integer() else f"{ch:.4g}"
                self.export_channel_list.insert(tk.END, display)

    def _save_single_channel(self) -> None:
        """Save the selected channel from the export tab to a CSV file."""
        func = self.export_func_var.get()
        if not func or func not in self.loaded_data:
            messagebox.showwarning("No function", "Please select a function.")
            return
        sel = self.export_channel_list.curselection()
        if not sel:
            messagebox.showwarning("No channel", "Please select a channel to export.")
            return
        ch_text = self.export_channel_list.get(sel[0])
        try:
            ch = float(ch_text)
        except ValueError:
            messagebox.showerror("Error", "Invalid channel selected.")
            return
        df = self.loaded_data[func]
        out_df = df[df["m/z"] == ch]
        if out_df.empty:
            messagebox.showinfo("No data", "The selected channel has no data.")
            return
        path = filedialog.asksaveasfilename(
            title="Save channel CSV",
            defaultextension=".csv",
            initialfile=f"{func}_channel_{int(ch)}.csv" if float(ch).is_integer() else f"{func}_channel_{ch:.4g}.csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            out_df.to_csv(path, index=False)
            messagebox.showinfo("Saved", f"Channel saved to {path}")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save channel: {exc}")

    # ------------------------------------------------------------------
    # Compare Functions helpers
    # ------------------------------------------------------------------
    def _refresh_compare_channels(self, _event: Optional[object] = None) -> None:
        """Refresh the list of common channels between the selected functions."""
        func1 = self.compare_func1_var.get()
        func2 = self.compare_func2_var.get()
        self.compare_channel_list.delete(0, tk.END)
        if not func1 or not func2:
            return
        if func1 not in self.loaded_data or func2 not in self.loaded_data:
            return
        channels1 = set(self.loaded_data[func1]["m/z"].unique())
        channels2 = set(self.loaded_data[func2]["m/z"].unique())
        common = sorted(channels1 & channels2)
        for ch in common:
            display = str(int(ch)) if float(ch).is_integer() else f"{ch:.4g}"
            self.compare_channel_list.insert(tk.END, display)

    def _plot_comparison(self) -> None:
        """Plot the selected channel for two functions on the comparison tab."""
        func1 = self.compare_func1_var.get()
        func2 = self.compare_func2_var.get()
        if not func1 or func1 not in self.loaded_data or not func2 or func2 not in self.loaded_data:
            messagebox.showwarning("Invalid selection", "Please select two valid functions.")
            return
        sel = self.compare_channel_list.curselection()
        if not sel:
            messagebox.showwarning("No channel", "Please select a common channel to compare.")
            return
        ch_text = self.compare_channel_list.get(sel[0])
        try:
            ch = float(ch_text)
        except ValueError:
            messagebox.showerror("Error", "Invalid channel selected.")
            return
        df1 = self.loaded_data[func1]
        df2 = self.loaded_data[func2]
        # Clear previous canvas
        for widget in self.compare_canvas_frame.winfo_children():
            widget.destroy()
        # Prepare data
        sub1 = df1[df1["m/z"] == ch].sort_values("Retention Time")
        sub2 = df2[df2["m/z"] == ch].sort_values("Retention Time")
        if sub1.empty or sub2.empty:
            messagebox.showinfo("No data", "Selected channel has no data in one or both functions.")
            return
        # Use Seaborn/Matplotlib for comparison plot
        try:
            sns.set(style="whitegrid")
            fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
            ax.plot(
                sub1["Retention Time"],
                sub1["Intensity"],
                label=f"{func1}",
            )
            ax.plot(
                sub2["Retention Time"],
                sub2["Intensity"],
                label=f"{func2}",
            )
            ax.set_xlabel("Retention Time")
            ax.set_ylabel("Intensity")
            ax.set_title(f"Channel {int(ch) if float(ch).is_integer() else ch:.4g} Comparison")
            ax.legend(title="Function")
            fig.tight_layout()
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            canvas = FigureCanvasTkAgg(fig, master=self.compare_canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as exc:
            messagebox.showerror("Plot error", f"Failed to generate comparison plot: {exc}")

    # ------------------------------------------------------------------
    # Find & Replace helpers
    # ------------------------------------------------------------------
    def _apply_find_replace(self) -> None:
        """Apply find and replace operation on the selected function."""
        func = self.fr_func_var.get()
        if not func or func not in self.loaded_data:
            messagebox.showwarning("No function selected", "Please select a function.")
            return
        find_text = self.find_value_var.get()
        replace_text = self.replace_value_var.get()
        if not find_text:
            messagebox.showwarning("Invalid input", "Please provide a value to find.")
            return
        try:
            find_value = float(find_text)
            replace_value = float(replace_text)
        except ValueError:
            messagebox.showerror("Error", "Find and replace values must be numeric.")
            return
        df = self.loaded_data[func]
        # Apply replacement across numeric columns only
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        df[numeric_cols] = df[numeric_cols].replace(find_value, replace_value)
        messagebox.showinfo("Find & Replace", f"Replaced all occurrences of {find_value} with {replace_value} in {func}.")
        # If the function is currently plotted or exported the user may need to replot manually

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _refresh_all_dropdowns(self) -> None:
        """Refresh all function dropdowns when loaded_data changes."""
        func_list = list(self.loaded_data.keys())
        for cb in [self.plot_func_dd, self.export_func_dd, self.compare_func1_dd, self.compare_func2_dd, self.fr_func_dd]:
            # Save current selection if still valid
            current = cb.get()
            cb['values'] = func_list
            if current in func_list:
                cb.set(current)
            else:
                cb.set('')
        # Refresh channels lists if needed
        self._update_plot_channels()
        self._update_export_channels()
        self._refresh_compare_channels()


def main() -> None:
    """Entry point for running the GUI application."""
    app = MSAnalyzerApp()
    app.mainloop()


if __name__ == "__main__":
    main()