"""
Advanced Mass Spec Parser and Plotter GUI
---------------------------------------

This module defines an enhanced graphical interface for working with mass‑
spectrometry ASCII files.  Users can load multiple ASCII files, parse the
FUNCTION blocks into DataFrames, view and select the resulting functions, and
generate publication‑quality plots with customizable parameters.  The GUI
organizes functionality into tabs using a Tkinter Notebook, making it easy to
switch between data loading and plotting options.

Key Features:
    • Load multiple ASCII files and parse them into CSVs and DataFrames.
    • Display a list of available functions across all loaded files.
    • Select functions and m/z values to generate interactive plots within the
      application.
    • Customize plotting parameters such as figure size and DPI.
    • Save CSVs and high‑resolution PNGs to a chosen output directory.

Usage:
    python mass_spec_gui_advanced.py

Dependencies:
    pandas, matplotlib, tkinter (included with standard Python), ttk, numpy

Author: ChatGPT
"""

import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def parse_mass_spec_file(file_path: str) -> Dict[int, pd.DataFrame]:
    """Parse a mass‑spec ASCII file into a dictionary of DataFrames keyed by function.

    Args:
        file_path: Path to the ASCII file.

    Returns:
        A dictionary mapping function numbers to DataFrames with columns:
            Scan (int), Retention Time (float), m/z (float), Intensity (float).
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    function_data: Dict[int, List[Dict[str, float]]] = {}
    current_func = None
    current_scan = None
    retention_time = None

    for line in lines:
        line = line.strip()
        func_match = re.match(r"FUNCTION\s+(\d+)", line, flags=re.IGNORECASE)
        if func_match:
            current_func = int(func_match.group(1))
            function_data[current_func] = []
            current_scan = None
            retention_time = None
            continue
        scan_match = re.match(r"Scan\s+(\d+)", line, flags=re.IGNORECASE)
        if scan_match and current_func is not None:
            current_scan = int(scan_match.group(1))
            continue
        rt_match = re.match(r"Retention\s+Time\s+([\d\.]+)", line, flags=re.IGNORECASE)
        if rt_match and current_func is not None:
            retention_time = float(rt_match.group(1))
            continue
        mz_int_match = re.match(r"([\d\.]+)\s+([\d\.]+)", line)
        if (
            mz_int_match
            and current_func is not None
            and current_scan is not None
            and retention_time is not None
        ):
            mz_val = float(mz_int_match.group(1))
            intensity = float(mz_int_match.group(2))
            function_data[current_func].append(
                {
                    "Scan": current_scan,
                    "Retention Time": retention_time,
                    "m/z": mz_val,
                    "Intensity": intensity,
                }
            )

    df_dict: Dict[int, pd.DataFrame] = {}
    for func, records in function_data.items():
        df_dict[func] = pd.DataFrame(records)
    return df_dict


class MassSpecGUI:
    """Advanced mass‑spec GUI using Tkinter Notebook with multiple tabs."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Mass Spec Analysis")
        root.geometry("900x600")

        # Data structures
        # Map (file_base_name, func_num) -> DataFrame
        self.loaded_data: Dict[Tuple[str, int], pd.DataFrame] = {}
        # Map file_base_name -> output directory used for saving
        self.output_dir: str | None = None

        # Notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.create_data_tab()
        self.create_plot_tab()
        self.create_view_tab()

    # --------------------------- Data Tab ---------------------------
    def create_data_tab(self) -> None:
        self.data_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.data_tab, text="Load & Parse")

        # File selection button
        select_btn = tk.Button(
            self.data_tab, text="Select ASCII Files…", command=self.select_files
        )
        select_btn.pack(pady=10)

        # Output directory selection
        dir_btn = tk.Button(
            self.data_tab, text="Select Output Directory…", command=self.select_output_dir
        )
        dir_btn.pack(pady=10)

        # Parse button
        parse_btn = tk.Button(
            self.data_tab, text="Parse Files", command=self.parse_files
        )
        parse_btn.pack(pady=10)

        # CSV loading button
        load_csv_btn = tk.Button(
            self.data_tab, text="Load CSV Files…", command=self.load_csv_files
        )
        load_csv_btn.pack(pady=10)

        # Listbox to show loaded functions
        self.func_listbox = tk.Listbox(self.data_tab, width=60, height=10)
        self.func_listbox.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Status label
        self.data_status = tk.Label(self.data_tab, text="No files loaded.")
        self.data_status.pack(pady=5)

    # --------------------------- Plot Tab ---------------------------
    def create_plot_tab(self) -> None:
        self.plot_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.plot_tab, text="Plot & Customize")

        # Dropdown for selecting loaded function
        self.selected_func = tk.StringVar()
        self.func_dropdown = ttk.Combobox(
            self.plot_tab, textvariable=self.selected_func, state="readonly", width=50
        )
        self.func_dropdown.pack(pady=5)
        self.func_dropdown.bind("<<ComboboxSelected>>", self.update_mz_list)

        # Frame for m/z list and options
        options_frame = ttk.Frame(self.plot_tab)
        options_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        mz_label = tk.Label(options_frame, text="Select m/z values:")
        mz_label.pack(anchor=tk.W)
        self.mz_listbox = tk.Listbox(options_frame, selectmode=tk.MULTIPLE, height=10)
        self.mz_listbox.pack(fill=tk.Y, expand=True)

        # Figure size options
        figsize_label = tk.Label(options_frame, text="Figure size (inches):")
        figsize_label.pack(anchor=tk.W, pady=(10, 0))
        size_frame = ttk.Frame(options_frame)
        size_frame.pack(anchor=tk.W)
        tk.Label(size_frame, text="Width:").grid(row=0, column=0)
        tk.Label(size_frame, text="Height:").grid(row=1, column=0)
        self.fig_width_var = tk.StringVar(value="8")
        self.fig_height_var = tk.StringVar(value="5")
        tk.Entry(size_frame, textvariable=self.fig_width_var, width=5).grid(row=0, column=1)
        tk.Entry(size_frame, textvariable=self.fig_height_var, width=5).grid(row=1, column=1)

        # DPI option
        dpi_label = tk.Label(options_frame, text="DPI:")
        dpi_label.pack(anchor=tk.W, pady=(10, 0))
        self.dpi_var = tk.StringVar(value="300")
        tk.Entry(options_frame, textvariable=self.dpi_var, width=5).pack(anchor=tk.W)

        # Plot button
        plot_btn = tk.Button(options_frame, text="Plot", command=self.plot_selected)
        plot_btn.pack(pady=10)

        # Canvas for showing plots
        self.figure_frame = ttk.Frame(self.plot_tab)
        self.figure_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Initialize an empty canvas
        self.canvas: FigureCanvasTkAgg | None = None

    # --------------------------- View CSV Tab ---------------------------
    def create_view_tab(self) -> None:
        """Create a tab to load and view arbitrary CSV files."""
        self.view_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.view_tab, text="CSV Viewer")

        # Button to open a CSV file
        open_csv_btn = tk.Button(
            self.view_tab, text="Open CSV File…", command=self.open_csv_for_view
        )
        open_csv_btn.pack(pady=5)

        # Treeview widget for displaying DataFrame
        self.csv_tree = ttk.Treeview(self.view_tab, show="headings")
        self.csv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbars for the treeview
        self.csv_scroll_y = ttk.Scrollbar(
            self.view_tab, orient="vertical", command=self.csv_tree.yview
        )
        self.csv_scroll_y.pack(side=tk.LEFT, fill=tk.Y)
        self.csv_tree.configure(yscrollcommand=self.csv_scroll_y.set)

        self.csv_scroll_x = ttk.Scrollbar(
            self.view_tab, orient="horizontal", command=self.csv_tree.xview
        )
        self.csv_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.csv_tree.configure(xscrollcommand=self.csv_scroll_x.set)

    # --------------------------- File & Parsing Logic ---------------------------
    def select_files(self) -> None:
        files = filedialog.askopenfilenames(
            parent=self.root,
            title="Select ASCII mass spec files",
            filetypes=[("Text files", "*.txt;*.dat;*.asc"), ("All files", "*.*")],
        )
        if files:
            self.files = list(files)
            self.data_status.config(text=f"Selected {len(self.files)} file(s).")
        else:
            self.files = []
            self.data_status.config(text="No files selected.")

    def select_output_dir(self) -> None:
        directory = filedialog.askdirectory(
            parent=self.root, title="Select output directory"
        )
        if directory:
            self.output_dir = directory
            self.data_status.config(text=f"Output directory set: {directory}")

    def parse_files(self) -> None:
        if not getattr(self, 'files', None):
            messagebox.showwarning("No files", "Please select at least one file.")
            return
        if not self.output_dir:
            messagebox.showwarning("No output directory", "Please select an output directory.")
            return

        total_funcs = 0
        self.loaded_data.clear()
        self.func_listbox.delete(0, tk.END)
        self.func_dropdown['values'] = ()

        for file_path in self.files:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                df_dict = parse_mass_spec_file(file_path)
                if not df_dict:
                    continue
                # Save CSVs and plots
                for func_num, df in df_dict.items():
                    # Save DataFrame to CSV
                    csv_name = f"{base_name}_Function_{func_num}.csv"
                    csv_dir = os.path.join(self.output_dir, "csv")
                    os.makedirs(csv_dir, exist_ok=True)
                    df.to_csv(os.path.join(csv_dir, csv_name), index=False)
                    # Save high‑res plot
                    plot_dir = os.path.join(self.output_dir, "plots")
                    os.makedirs(plot_dir, exist_ok=True)
                    plt.rcParams.update({
                        "font.family": "sans-serif",
                        "axes.labelsize": 14,
                        "axes.titlesize": 16,
                        "font.size": 12,
                        "lines.linewidth": 1.5,
                        "figure.dpi": 300,
                        "axes.grid": True,
                    })
                    plt.figure(figsize=(8, 5))
                    for mz_val, group_df in df.groupby("m/z"):
                        group_df = group_df.sort_values("Retention Time")
                        plt.plot(
                            group_df["Retention Time"],
                            group_df["Intensity"],
                            label=f"m/z {mz_val}",
                        )
                    plt.xlabel("Retention Time (min)")
                    plt.ylabel("Intensity (a.u.)")
                    plt.title(f"{base_name} – Function {func_num}")
                    plt.legend(title="m/z")
                    plt.tight_layout()
                    plot_path = os.path.join(plot_dir, f"{base_name}_Function_{func_num}.png")
                    plt.savefig(plot_path)
                    plt.close()

                    # Store DataFrame
                    self.loaded_data[(base_name, func_num)] = df
                    self.func_listbox.insert(tk.END, f"{base_name} – Function {func_num}")
                    total_funcs += 1
            except Exception as exc:
                messagebox.showerror("Error", f"Error processing {file_path}: {exc}")

        # Refresh display and dropdown values based on loaded data
        self.refresh_loaded_display()
        self.data_status.config(text=f"Loaded {total_funcs} function(s).")

    def refresh_loaded_display(self) -> None:
        """Refresh listbox and dropdown based on current loaded data."""
        # Clear listbox
        self.func_listbox.delete(0, tk.END)
        # Populate listbox and build dropdown value list
        dropdown_vals: List[str] = []
        for (base_name, func_num) in sorted(self.loaded_data.keys()):
            label = f"{base_name} – Function {func_num}"
            self.func_listbox.insert(tk.END, label)
            dropdown_vals.append(label)
        # Update plot dropdown values
        self.func_dropdown['values'] = dropdown_vals
        if dropdown_vals:
            self.func_dropdown.current(0)
        # Update m/z list for the first item
        self.update_mz_list()

    def load_csv_files(self) -> None:
        """Allow user to load existing CSV files into the application."""
        files = filedialog.askopenfilenames(
            parent=self.root,
            title="Select CSV files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not files:
            return
        for file_path in files:
            filename = os.path.basename(file_path)
            # Attempt to parse base name and function number from file name
            match = re.match(r"(.*)_Function_(\d+)\.csv", filename)
            if match:
                base_name = match.group(1)
                func_num = int(match.group(2))
            else:
                base_name = os.path.splitext(filename)[0]
                func_num = 0
            try:
                df = pd.read_csv(file_path)
                required_cols = {"Scan", "Retention Time", "m/z", "Intensity"}
                if not required_cols.issubset(df.columns):
                    messagebox.showwarning(
                        "Invalid CSV",
                        f"{filename} does not contain required columns: {required_cols}",
                    )
                    continue
                # Store the DataFrame
                self.loaded_data[(base_name, func_num)] = df
            except Exception as exc:
                messagebox.showerror(
                    "Error", f"Could not read {filename}: {exc}"
                )
        # Refresh display and update status
        self.refresh_loaded_display()
        self.data_status.config(
            text=f"Loaded {len(self.loaded_data)} function(s) in total."
        )

    # --------------------------- CSV Viewer Logic ---------------------------
    def open_csv_for_view(self) -> None:
        """Open a CSV file and display its contents in the viewer tab."""
        file_path = filedialog.askopenfilename(
            parent=self.root,
            title="Open CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            df = pd.read_csv(file_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open {os.path.basename(file_path)}: {exc}")
            return
        # Display DataFrame
        self.show_dataframe_in_tree(df)

    def show_dataframe_in_tree(self, df: pd.DataFrame) -> None:
        """Display a pandas DataFrame in the treeview widget."""
        # Clear existing contents
        for col in self.csv_tree.get_children():
            self.csv_tree.delete(col)
        self.csv_tree.delete(*self.csv_tree.get_children())
        # Configure columns
        columns = list(df.columns)
        self.csv_tree.configure(columns=columns)
        for col in columns:
            self.csv_tree.heading(col, text=col)
            self.csv_tree.column(col, width=max(80, len(col) * 10))
        # Insert rows
        for _, row in df.iterrows():
            values = [row[col] for col in columns]
            self.csv_tree.insert("", tk.END, values=values)

    # --------------------------- Plotting Logic ---------------------------
    def update_mz_list(self, _event=None) -> None:
        """Update the m/z listbox when a new function is selected from the dropdown."""
        selected = self.selected_func.get()
        if not selected:
            return
        try:
            # Extract base name and function number from the selected string
            base_name, func_label = selected.split(" – Function ")
            func_num = int(func_label)
        except ValueError:
            return
        df = self.loaded_data.get((base_name, func_num))
        if df is None:
            return
        mz_values = sorted(df["m/z"].unique())
        self.mz_listbox.delete(0, tk.END)
        for mz in mz_values:
            self.mz_listbox.insert(tk.END, mz)
        # Select all by default
        self.mz_listbox.select_set(0, tk.END)

    def plot_selected(self) -> None:
        """Plot the selected function with selected m/z values and options."""
        selected = self.selected_func.get()
        if not selected:
            messagebox.showwarning("No selection", "Please select a function from the dropdown.")
            return
        try:
            base_name, func_label = selected.split(" – Function ")
            func_num = int(func_label)
        except ValueError:
            messagebox.showerror("Error", "Invalid selection format.")
            return
        df = self.loaded_data.get((base_name, func_num))
        if df is None:
            messagebox.showerror("Error", "Selected function not found.")
            return

        # Retrieve selected m/z values
        mz_indices = self.mz_listbox.curselection()
        if not mz_indices:
            messagebox.showwarning("No m/z selected", "Please select at least one m/z value to plot.")
            return
        try:
            selected_mzs = [float(self.mz_listbox.get(i)) for i in mz_indices]
        except ValueError:
            messagebox.showerror("Error", "Invalid m/z value format.")
            return

        # Figure parameters
        try:
            fig_width = float(self.fig_width_var.get())
            fig_height = float(self.fig_height_var.get())
            dpi = int(self.dpi_var.get())
        except ValueError:
            messagebox.showerror("Error", "Figure size and DPI must be numeric.")
            return

        # Prepare plot
        fig = plt.Figure(figsize=(fig_width, fig_height), dpi=dpi)
        ax = fig.add_subplot(111)
        for mz_val in selected_mzs:
            group_df = df[df["m/z"] == mz_val].sort_values("Retention Time")
            ax.plot(
                group_df["Retention Time"],
                group_df["Intensity"],
                label=f"m/z {mz_val}",
            )
        ax.set_xlabel("Retention Time (min)")
        ax.set_ylabel("Intensity (a.u.)")
        ax.set_title(f"{base_name} – Function {func_num}")
        ax.legend(title="m/z")
        ax.grid(True)

        # Clear previous canvas if exists
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        # Embed new figure
        self.canvas = FigureCanvasTkAgg(fig, master=self.figure_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # --------------------------- CSV Viewing Logic ---------------------------
    def show_csv(self, _event=None) -> None:
        """Display the selected CSV DataFrame in the Treeview widget."""
        selected = self.view_selected_func.get()
        if not selected:
            return
        try:
            base_name, func_label = selected.split(" – Function ")
            func_num = int(func_label)
        except ValueError:
            return
        df = self.loaded_data.get((base_name, func_num))
        if df is None:
            return
        # Clear existing contents
        for col in self.csv_tree.get_children():
            self.csv_tree.delete(col)
        self.csv_tree.delete(*self.csv_tree.get_children())
        # Configure columns
        columns = list(df.columns)
        self.csv_tree.configure(columns=columns)
        for col in columns:
            self.csv_tree.heading(col, text=col)
            # Set column width proportional to column name length
            self.csv_tree.column(col, width=max(80, len(col) * 10))
        # Insert rows
        for _, row in df.iterrows():
            values = [row[col] for col in columns]
            self.csv_tree.insert("", tk.END, values=values)


def main() -> None:
    root = tk.Tk()
    app = MassSpecGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()