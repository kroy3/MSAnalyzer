"""
csv_viewer.py
--------------

Provides a Tkinter frame for viewing tabular data from pandas
DataFrames.  The viewer supports basic searching: entering a query
filters the rows displayed in the tree view.  Column names are used
for headings, and column widths adjust automatically based on header
length.

Example
-------

>>> import tkinter as tk
>>> import pandas as pd
>>> from csv_viewer import CSVViewer
>>> root = tk.Tk()
>>> viewer = CSVViewer(root)
>>> viewer.pack(fill=tk.BOTH, expand=True)
>>> df = pd.DataFrame({"A": [1,2,3], "B":["foo","bar","baz"]})
>>> viewer.display_dataframe(df)
>>> root.mainloop()

"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import pandas as pd


class CSVViewer(ttk.Frame):
    """A scrollable tree view with search functionality for DataFrames."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        # Search bar
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<KeyRelease>", self._filter_rows)
        # Treeview and scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self._tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self._tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        self._tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree = ttk.Treeview(
            tree_frame,
            columns=[],
            show="headings",
            yscrollcommand=self._tree_scroll_y.set,
            xscrollcommand=self._tree_scroll_x.set,
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        self._tree_scroll_y.config(command=self.tree.yview)
        self._tree_scroll_x.config(command=self.tree.xview)
        # Store original DataFrame for filtering
        self._full_df: pd.DataFrame | None = None

    def display_dataframe(self, df: pd.DataFrame) -> None:
        """Load a DataFrame into the viewer.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame to display.
        """
        self._full_df = df.copy()
        self._populate_tree(self._full_df)

    def _populate_tree(self, df: pd.DataFrame) -> None:
        """Populate the tree view with the contents of ``df``."""
        # Clear previous
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree['columns'] = list(df.columns)
        for col in df.columns:
            self.tree.heading(col, text=col)
            width = max(len(str(col)) * 8, 80)
            self.tree.column(col, width=width, anchor=tk.W)
        # Insert rows
        for _, row in df.iterrows():
            values = [row[col] for col in df.columns]
            self.tree.insert("", tk.END, values=values)

    def _filter_rows(self, _event: tk.Event) -> None:
        """Filter rows based on search query."""
        query = self.search_var.get().strip().lower()
        if self._full_df is None:
            return
        if not query:
            df = self._full_df
        else:
            # Filter rows containing the query in any column (as string)
            mask = self._full_df.apply(lambda row: row.astype(str).str.lower().str.contains(query).any(), axis=1)
            df = self._full_df[mask]
        self._populate_tree(df)