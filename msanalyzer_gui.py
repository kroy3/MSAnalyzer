"""
msanalyzer_gui.py
------------------

Graphical user interface for the MSAnalyzer package.  This module
orchestrates the user experience: selecting files, parsing data,
generating plots, viewing tables, exporting channels, comparing
functions and performing find & replace operations.  It leverages
separate modules (``parser.py``, ``plot_utils.py``, ``csv_viewer.py``)
for the underlying data handling and plotting functionality.  The GUI
is built on Tkinter and remains responsive by deferring heavy
computation to helper functions.

The landing tab features the Wang Lab logo to provide context and
branding.  Ensure that ``wang_lab_logo.png`` resides in the same
directory as this script.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional, Tuple

import pandas as pd

from parser import MassSpecParser
from plot_utils import plot_channels, compare_channels
from csv_viewer import CSVViewer

try:
    from PIL import Image, ImageTk  # type: ignore
except ImportError:
    Image = None
    ImageTk = None

try:
    import plotly.express as px  # type: ignore
    import plotly.io as pio  # type: ignore
    _PLOTLY_AVAILABLE = True
except Exception:
    _PLOTLY_AVAILABLE = False

import matplotlib
# Use Agg by default; embedding will override
matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt
import seaborn as sns

class MSAnalyzerGUI(tk.Tk):
    """Top‑level application class for the mass‑spectrometry GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.title("MSAnalyzer")
        self.geometry("1150x780")
        # Data storage: mapping function label -> DataFrame
        self.loaded_data: Dict[str, pd.DataFrame] = {}
        # Output directory for parsed CSVs and plots
        self.output_directory: Optional[str] = None
        # Selected raw files awaiting parsing
        self._selected_raw_files: List[str] = []
        # Build interface
        self._build_interface()

    def _build_interface(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        # Create tabs
        self._create_tab_load_parse()
        self._create_tab_plot_customise()
        self._create_tab_csv_viewer()
        self._create_tab_channel_export()
        self._create_tab_compare_functions()
        self._create_tab_find_replace()

    # ------------------------------------------------------------------
    # Load & Parse tab
    # ------------------------------------------------------------------
    def _create_tab_load_parse(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Load & Parse")
        # Header with logo
        header = ttk.Frame(tab)
        header.pack(fill=tk.X, pady=10)
        logo_path = os.path.join(os.path.dirname(__file__), "wang_lab_logo.png")
        if Image is not None and os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                ratio = min(1.0, 200.0 / float(img.width))
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
                self._logo_photo = ImageTk.PhotoImage(img)
                ttk.Label(header, image=self._logo_photo).pack(side=tk.LEFT, padx=10)
            except Exception:
                pass
        ttk.Label(
            header,
            text="MSAnalyzer – Mass‑Spectrometry Data Parser and Viewer",
            font=("Helvetica", 16, "bold"),
        ).pack(side=tk.LEFT)
        # Buttons for file selection and parsing
        controls = ttk.Frame(tab)
        controls.pack(fill=tk.X, pady=15)
        ttk.Button(
            controls, text="Select ASCII/CDF Files", command=self._select_raw_files
        ).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(
            controls, text="Select Output Directory", command=self._select_output_directory
        ).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(
            controls, text="Parse Selected Files", command=self._parse_selected_files
        ).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(
            controls, text="Load CSV Files", command=self._load_csv_files
        ).grid(row=0, column=3, padx=5, pady=5)
        # Status message
        self.status_var = tk.StringVar(value="No files parsed.")
        ttk.Label(tab, textvariable=self.status_var, wraplength=1050).pack(fill=tk.X, padx=10)

    def _select_raw_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select ASCII (.txt) or CDF (.cdf) files",
            filetypes=[("Mass‑Spec Files", "*.txt *.cdf"), ("All Files", "*.*")],
        )
        if files:
            self._selected_raw_files = list(files)
            self.status_var.set(f"Selected {len(files)} file(s).  Choose output directory and click Parse.")

    def _select_output_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_directory = directory
            self.status_var.set(f"Output directory set to: {directory}")

    def _parse_selected_files(self) -> None:
        if not self._selected_raw_files:
            messagebox.showwarning("No files", "Please select ASCII/CDF files to parse.")
            return
        if not self.output_directory:
            messagebox.showwarning("No output directory", "Please select an output directory.")
            return
        csv_dir = os.path.join(self.output_directory, "csv")
        plots_dir = os.path.join(self.output_directory, "plots")
        os.makedirs(csv_dir, exist_ok=True)
        os.makedirs(plots_dir, exist_ok=True)
        messages: List[str] = []
        for path in self._selected_raw_files:
            try:
                if path.lower().endswith(".txt"):
                    parsed = MassSpecParser.parse_ascii(path)
                elif path.lower().endswith(".cdf"):
                    parsed = MassSpecParser.parse_cdf(path)
                else:
                    messages.append(f"Unsupported format: {path}")
                    continue
            except Exception as exc:
                messages.append(f"Error parsing {os.path.basename(path)}: {exc}")
                continue
            for func_label, df in parsed.items():
                # Store DataFrame
                self.loaded_data[func_label] = df
                # Write CSV
                out_csv = os.path.join(csv_dir, f"{func_label}.csv")
                try:
                    df.to_csv(out_csv, index=False)
                except Exception as exc:
                    messages.append(f"Failed to write CSV for {func_label}: {exc}")
                # Plot each channel
                try:
                    fig = plot_channels(df, sorted(df["Channel"].unique()), width=8, height=5, dpi=300, title=func_label)
                    out_png = os.path.join(plots_dir, f"{func_label}.png")
                    fig.savefig(out_png)
                    plt.close(fig)
                except Exception as exc:
                    messages.append(f"Failed to plot {func_label}: {exc}")
        self._refresh_dropdowns()
        msg = "\n".join(messages) if messages else "Parsing complete."
        self.status_var.set(msg)

    def _load_csv_files(self) -> None:
        files = filedialog.askopenfilenames(title="Select CSV files", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not files:
            return
        skipped: List[str] = []
        for path in files:
            try:
                df = pd.read_csv(path)
                # Standardise column names
                col_map = {c.lower(): c for c in df.columns}
                if not {"scan", "retention time", "channel", "intensity"}.issubset(set(col_map.keys())):
                    skipped.append(os.path.basename(path))
                    continue
                # Reorder columns
                df = df[[col_map["scan"], col_map["retention time"], col_map["channel"], col_map["intensity"]]]
                df.columns = ["Scan", "Retention Time", "Channel", "Intensity"]
                label = os.path.splitext(os.path.basename(path))[0]
                self.loaded_data[label] = df
            except Exception:
                skipped.append(os.path.basename(path))
        self._refresh_dropdowns()
        if skipped:
            messagebox.showinfo("Import notice", f"Skipped files: {', '.join(skipped)}")

    # ------------------------------------------------------------------
    # Plot & Customise tab
    # ------------------------------------------------------------------
    def _create_tab_plot_customise(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Plot & Customise")
        # Controls
        ctrl = ttk.Frame(tab)
        ctrl.pack(fill=tk.X, pady=10)
        ttk.Label(ctrl, text="Function:").grid(row=0, column=0, padx=5)
        self.plot_func_var = tk.StringVar()
        self.plot_func_dd = ttk.Combobox(ctrl, textvariable=self.plot_func_var, state="readonly", width=40)
        self.plot_func_dd.grid(row=0, column=1, padx=5)
        self.plot_func_dd.bind("<<ComboboxSelected>>", self._update_plot_channel_list)
        ttk.Label(ctrl, text="Channels:").grid(row=1, column=0, padx=5, sticky=tk.N)
        self.plot_channel_list = tk.Listbox(ctrl, selectmode=tk.MULTIPLE, height=8, width=20)
        self.plot_channel_list.grid(row=1, column=1, padx=5, sticky=tk.W)
        # Figure parameters
        ttk.Label(ctrl, text="Width (in)").grid(row=0, column=2, padx=5)
        self.plot_width = tk.DoubleVar(value=8.0)
        ttk.Entry(ctrl, textvariable=self.plot_width, width=6).grid(row=0, column=3, padx=5)
        ttk.Label(ctrl, text="Height (in)").grid(row=1, column=2, padx=5)
        self.plot_height = tk.DoubleVar(value=5.0)
        ttk.Entry(ctrl, textvariable=self.plot_height, width=6).grid(row=1, column=3, padx=5)
        ttk.Label(ctrl, text="DPI").grid(row=0, column=4, padx=5)
        self.plot_dpi = tk.IntVar(value=300)
        ttk.Entry(ctrl, textvariable=self.plot_dpi, width=6).grid(row=0, column=5, padx=5)
        ttk.Label(ctrl, text="Backend:").grid(row=1, column=2, padx=5, columnspan=2, sticky=tk.E)
        self.backend_var = tk.StringVar(value="matplotlib")
        ttk.Radiobutton(ctrl, text="Matplotlib/Seaborn", variable=self.backend_var, value="matplotlib").grid(row=1, column=4, padx=5)
        ttk.Radiobutton(ctrl, text="Plotly", variable=self.backend_var, value="plotly").grid(row=1, column=5, padx=5)
        # Plot button
        ttk.Button(ctrl, text="Plot", command=self._plot_custom).grid(row=0, column=6, rowspan=2, padx=10)
        # Canvas area
        self.plot_area = ttk.Frame(tab)
        self.plot_area.pack(fill=tk.BOTH, expand=True)

    def _update_plot_channel_list(self, _event: Optional[object] = None) -> None:
        func = self.plot_func_var.get()
        self.plot_channel_list.delete(0, tk.END)
        if func and func in self.loaded_data:
            channels = sorted(self.loaded_data[func]["Channel"].unique())
            for ch in channels:
                display = str(int(ch)) if float(ch).is_integer() else f"{ch:.4g}"
                self.plot_channel_list.insert(tk.END, display)

    def _plot_custom(self) -> None:
        func = self.plot_func_var.get()
        if not func or func not in self.loaded_data:
            messagebox.showwarning("No function", "Select a function to plot.")
            return
        selections = self.plot_channel_list.curselection()
        if not selections:
            messagebox.showwarning("No channels", "Select one or more channels to plot.")
            return
        channels: List[float] = []
        for idx in selections:
            text = self.plot_channel_list.get(idx)
            try:
                channels.append(float(text))
            except ValueError:
                pass
        width = self.plot_width.get()
        height = self.plot_height.get()
        dpi = self.plot_dpi.get()
        backend = self.backend_var.get()
        df = self.loaded_data[func]
        # Clear previous plot
        for widget in self.plot_area.winfo_children():
            widget.destroy()
        # Create plot
        if backend == "plotly" and _PLOTLY_AVAILABLE:
            # Use Plotly to generate interactive figure; embed as static PNG
            sub = df[df["Channel"].isin(channels)].copy()
            sub.sort_values(["Channel", "Retention Time"], inplace=True)
            try:
                fig = px.line(
                    sub,
                    x="Retention Time",
                    y="Intensity",
                    color="Channel",
                    labels={"Channel": "Channel"},
                    title=func,
                )
                fig.update_layout(width=int(width * dpi), height=int(height * dpi))
                img_bytes = pio.to_image(fig, format="png")
                if Image is None:
                    raise RuntimeError("Pillow is required to display Plotly figures in the GUI.")
                from io import BytesIO
                pil_img = Image.open(BytesIO(img_bytes))
                self._plot_photo = ImageTk.PhotoImage(pil_img)
                ttk.Label(self.plot_area, image=self._plot_photo).pack(fill=tk.BOTH, expand=True)
                return
            except Exception as exc:
                messagebox.showerror("Plot error", f"Plotly error: {exc}")
                return
        # Fallback to Matplotlib/Seaborn
        try:
            fig = plot_channels(df, channels, width=width, height=height, dpi=dpi, title=func)
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            canvas = FigureCanvasTkAgg(fig, master=self.plot_area)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as exc:
            messagebox.showerror("Plot error", f"Error generating plot: {exc}")

    # ------------------------------------------------------------------
    # CSV Viewer tab
    # ------------------------------------------------------------------
    def _create_tab_csv_viewer(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="CSV Viewer")
        # Instantiate CSVViewer
        self.csv_viewer = CSVViewer(tab)
        self.csv_viewer.pack(fill=tk.BOTH, expand=True)
        # Button to open arbitrary CSV
        ttk.Button(tab, text="Open CSV File...", command=self._open_and_show_csv).pack(pady=5)

    def _open_and_show_csv(self) -> None:
        path = filedialog.askopenfilename(title="Select a CSV file", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not path:
            return
        try:
            df = pd.read_csv(path)
            self.csv_viewer.display_dataframe(df)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open CSV: {exc}")

    # ------------------------------------------------------------------
    # Channel Export tab
    # ------------------------------------------------------------------
    def _create_tab_channel_export(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Channel Export")
        frm = ttk.Frame(tab)
        frm.pack(pady=10)
        ttk.Label(frm, text="Function:").grid(row=0, column=0, padx=5)
        self.export_func_var = tk.StringVar()
        self.export_func_dd = ttk.Combobox(frm, textvariable=self.export_func_var, state="readonly", width=40)
        self.export_func_dd.grid(row=0, column=1, padx=5)
        self.export_func_dd.bind("<<ComboboxSelected>>", self._update_export_channel_list)
        ttk.Label(frm, text="Channel:").grid(row=1, column=0, padx=5, sticky=tk.N)
        self.export_channel_list = tk.Listbox(frm, selectmode=tk.SINGLE, height=8, width=20)
        self.export_channel_list.grid(row=1, column=1, padx=5, sticky=tk.W)
        ttk.Button(tab, text="Save Channel CSV", command=self._save_selected_channel).pack(pady=10)

    def _update_export_channel_list(self, _event: Optional[object] = None) -> None:
        func = self.export_func_var.get()
        self.export_channel_list.delete(0, tk.END)
        if func and func in self.loaded_data:
            channels = sorted(self.loaded_data[func]["Channel"].unique())
            for ch in channels:
                display = str(int(ch)) if float(ch).is_integer() else f"{ch:.4g}"
                self.export_channel_list.insert(tk.END, display)

    def _save_selected_channel(self) -> None:
        func = self.export_func_var.get()
        if not func or func not in self.loaded_data:
            messagebox.showwarning("No function", "Select a function first.")
            return
        sel = self.export_channel_list.curselection()
        if not sel:
            messagebox.showwarning("No channel", "Select a channel to export.")
            return
        ch_text = self.export_channel_list.get(sel[0])
        try:
            channel = float(ch_text)
        except ValueError:
            messagebox.showerror("Error", "Invalid channel selected.")
            return
        df = self.loaded_data[func]
        out_df = df[df["Channel"] == channel]
        if out_df.empty:
            messagebox.showinfo("No data", "Selected channel has no data.")
            return
        path = filedialog.asksaveasfilename(
            title="Save channel CSV",
            defaultextension=".csv",
            initialfile=f"{func}_channel_{int(channel)}.csv" if float(channel).is_integer() else f"{func}_channel_{channel:.4g}.csv",
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
    # Compare Functions tab
    # ------------------------------------------------------------------
    def _create_tab_compare_functions(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Compare Functions")
        frm = ttk.Frame(tab)
        frm.pack(pady=10)
        ttk.Label(frm, text="Function A:").grid(row=0, column=0, padx=5)
        self.compare_func1_var = tk.StringVar()
        self.compare_func1_dd = ttk.Combobox(frm, textvariable=self.compare_func1_var, state="readonly", width=40)
        self.compare_func1_dd.grid(row=0, column=1, padx=5)
        self.compare_func1_dd.bind("<<ComboboxSelected>>", self._refresh_common_channels)
        ttk.Label(frm, text="Function B:").grid(row=1, column=0, padx=5)
        self.compare_func2_var = tk.StringVar()
        self.compare_func2_dd = ttk.Combobox(frm, textvariable=self.compare_func2_var, state="readonly", width=40)
        self.compare_func2_dd.grid(row=1, column=1, padx=5)
        self.compare_func2_dd.bind("<<ComboboxSelected>>", self._refresh_common_channels)
        ttk.Label(frm, text="Common Channels:").grid(row=2, column=0, padx=5, sticky=tk.N)
        self.compare_channel_list = tk.Listbox(frm, selectmode=tk.SINGLE, height=8, width=20)
        self.compare_channel_list.grid(row=2, column=1, padx=5, sticky=tk.W)
        ttk.Button(tab, text="Plot Comparison", command=self._plot_comparison).pack(pady=10)
        self.compare_plot_area = ttk.Frame(tab)
        self.compare_plot_area.pack(fill=tk.BOTH, expand=True)

    def _refresh_common_channels(self, _event: Optional[object] = None) -> None:
        func1 = self.compare_func1_var.get()
        func2 = self.compare_func2_var.get()
        self.compare_channel_list.delete(0, tk.END)
        if not func1 or not func2 or func1 not in self.loaded_data or func2 not in self.loaded_data:
            return
        channels1 = set(self.loaded_data[func1]["Channel"].unique())
        channels2 = set(self.loaded_data[func2]["Channel"].unique())
        common = sorted(channels1 & channels2)
        for ch in common:
            display = str(int(ch)) if float(ch).is_integer() else f"{ch:.4g}"
            self.compare_channel_list.insert(tk.END, display)

    def _plot_comparison(self) -> None:
        func1 = self.compare_func1_var.get()
        func2 = self.compare_func2_var.get()
        if not func1 or not func2 or func1 not in self.loaded_data or func2 not in self.loaded_data:
            messagebox.showwarning("Invalid selection", "Select two valid functions.")
            return
        sel = self.compare_channel_list.curselection()
        if not sel:
            messagebox.showwarning("No channel", "Select a common channel to compare.")
            return
        ch_text = self.compare_channel_list.get(sel[0])
        try:
            channel = float(ch_text)
        except ValueError:
            messagebox.showerror("Error", "Invalid channel.")
            return
        df1 = self.loaded_data[func1]
        df2 = self.loaded_data[func2]
        # Clear previous
        for widget in self.compare_plot_area.winfo_children():
            widget.destroy()
        try:
            fig = compare_channels(df1, df2, channel, width=8, height=5, dpi=300, labels=(func1, func2))
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            canvas = FigureCanvasTkAgg(fig, master=self.compare_plot_area)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as exc:
            messagebox.showerror("Plot error", f"Failed to plot comparison: {exc}")

    # ------------------------------------------------------------------
    # Find & Replace tab
    # ------------------------------------------------------------------
    def _create_tab_find_replace(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Find & Replace")
        frm = ttk.Frame(tab)
        frm.pack(pady=10)
        ttk.Label(frm, text="Function:").grid(row=0, column=0, padx=5)
        self.fr_func_var = tk.StringVar()
        self.fr_func_dd = ttk.Combobox(frm, textvariable=self.fr_func_var, state="readonly", width=40)
        self.fr_func_dd.grid(row=0, column=1, padx=5)
        ttk.Label(frm, text="Find value:").grid(row=1, column=0, padx=5)
        self.fr_find_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.fr_find_var).grid(row=1, column=1, padx=5)
        ttk.Label(frm, text="Replace with:").grid(row=2, column=0, padx=5)
        self.fr_replace_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.fr_replace_var).grid(row=2, column=1, padx=5)
        ttk.Button(frm, text="Find", command=self._find_values).grid(row=3, column=0, pady=5)
        ttk.Button(frm, text="Replace", command=self._replace_values).grid(row=3, column=1, pady=5)
        # Results label
        self.fr_result_var = tk.StringVar()
        ttk.Label(tab, textvariable=self.fr_result_var, wraplength=1050).pack(fill=tk.X, padx=10)

    def _find_values(self) -> None:
        func = self.fr_func_var.get()
        if not func or func not in self.loaded_data:
            messagebox.showwarning("No function", "Select a function.")
            return
        query = self.fr_find_var.get()
        if not query:
            messagebox.showwarning("Invalid input", "Enter a numeric value to find.")
            return
        try:
            val = float(query)
        except ValueError:
            messagebox.showerror("Error", "Find value must be numeric.")
            return
        df = self.loaded_data[func]
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        # Count occurrences across numeric columns
        count = int((df[numeric_cols] == val).sum().sum())
        self.fr_result_var.set(f"Found {count} occurrence(s) of {val} in {func}.")

    def _replace_values(self) -> None:
        func = self.fr_func_var.get()
        if not func or func not in self.loaded_data:
            messagebox.showwarning("No function", "Select a function.")
            return
        find_text = self.fr_find_var.get()
        replace_text = self.fr_replace_var.get()
        if not find_text:
            messagebox.showwarning("Invalid input", "Enter a numeric value to find.")
            return
        try:
            find_val = float(find_text)
            replace_val = float(replace_text)
        except ValueError:
            messagebox.showerror("Error", "Find and replace values must be numeric.")
            return
        df = self.loaded_data[func]
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        occurrences = (df[numeric_cols] == find_val).sum().sum()
        if occurrences == 0:
            self.fr_result_var.set(f"Value {find_val} not found in {func}.")
            return
        # Confirm replacement
        if not messagebox.askyesno("Confirm replacement", f"Replace {occurrences} occurrence(s) of {find_val} with {replace_val}?"):
            return
        df[numeric_cols] = df[numeric_cols].replace(find_val, replace_val)
        self.fr_result_var.set(f"Replaced {occurrences} occurrence(s) of {find_val} with {replace_val} in {func}.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _refresh_dropdowns(self) -> None:
        values = list(self.loaded_data.keys())
        for cb in [self.plot_func_dd, self.export_func_dd, self.compare_func1_dd, self.compare_func2_dd, self.fr_func_dd]:
            current = cb.get()
            cb['values'] = values
            if current in values:
                cb.set(current)
            else:
                cb.set('')
        # Update channel lists
        self._update_plot_channel_list()
        self._update_export_channel_list()
        self._refresh_common_channels()


def main() -> None:
    app = MSAnalyzerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()