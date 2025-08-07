"""
parser.py
-----------

This module contains functions and classes for parsing mass‑spectrometry
data from ASCII and netCDF (CDF) formats.  The resulting data are
returned as pandas DataFrames with standard column names: ``Scan``,
``Retention Time``, ``Channel`` and ``Intensity``.  The term
``Channel`` replaces ``m/z`` in earlier versions to emphasise that
each value corresponds to a distinct ion channel (mass‑to‑charge
ratio) rather than a free‑form identifier.

The parser attempts to read netCDF files via the ``netCDF4`` package
if available.  If not, it falls back to ``scipy.io.netcdf_file``.  A
``ValueError`` is raised if the necessary variables (``scan_index``,
``point_count``, ``mass_values`` and ``intensity_values``) are
missing.

Usage
-----

>>> from parser import MassSpecParser
>>> result = MassSpecParser.parse_ascii("example.txt")
>>> df = result["example_Function_1"]
>>> print(df.head())

This module does not depend on Tkinter and can be imported in
headless environments.  See ``msanalyzer_gui.py`` for GUI usage.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple, Optional

import pandas as pd

try:
    import netCDF4  # type: ignore
except ImportError:
    netCDF4 = None  # type: ignore

try:
    from scipy.io import netcdf_file  # type: ignore
except ImportError:
    netcdf_file = None  # type: ignore


class MassSpecParser:
    """Parser for mass‑spectrometry data files.

    Provides static methods for reading ASCII and netCDF files.
    The returned mapping keys are labels of the form
    ``<basename>_Function_<n>``.  DataFrames contain integer
    ``Scan`` indices, floating point ``Retention Time`` values and
    ``Channel``/``Intensity`` pairs.
    """

    # Regular expressions for ASCII parsing
    _FUNC_RE = re.compile(r"^FUNCTION\s+(\d+)", re.IGNORECASE)
    _SCAN_RE = re.compile(r"^Scan\s+(\d+)", re.IGNORECASE)
    _RT_RE = re.compile(r"^Retention Time\s+([0-9]*\.?[0-9]+)", re.IGNORECASE)

    @staticmethod
    def parse_ascii(path: str) -> Dict[str, pd.DataFrame]:
        """Parse a multi‑function ASCII file.

        Parameters
        ----------
        path : str
            Path to the input ASCII file.

        Returns
        -------
        dict
            Mapping from function labels to DataFrames.  Each DataFrame
            has columns ``Scan``, ``Retention Time``, ``Channel`` and
            ``Intensity``.
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
                    continue
                m_func = MassSpecParser._FUNC_RE.match(line)
                if m_func:
                    current_function = int(m_func.group(1))
                    current_scan = None
                    current_rt = None
                    key = f"{basename}_Function_{current_function}"
                    functions.setdefault(key, [])
                    continue
                m_scan = MassSpecParser._SCAN_RE.match(line)
                if m_scan:
                    current_scan = int(m_scan.group(1))
                    continue
                m_rt = MassSpecParser._RT_RE.match(line)
                if m_rt:
                    try:
                        current_rt = float(m_rt.group(1))
                    except ValueError:
                        current_rt = None
                    continue
                # Parse m/z and intensity pairs
                if current_function is not None and current_scan is not None and current_rt is not None:
                    parts = re.split(r"\s+", line)
                    if len(parts) == 2:
                        try:
                            channel = float(parts[0])
                            intensity = float(parts[1])
                        except ValueError:
                            continue
                        key = f"{basename}_Function_{current_function}"
                        functions.setdefault(key, []).append((current_scan, current_rt, channel, intensity))
        result: Dict[str, pd.DataFrame] = {}
        for key, rows in functions.items():
            if not rows:
                continue
            df = pd.DataFrame(rows, columns=["Scan", "Retention Time", "Channel", "Intensity"])
            df["Scan"] = df["Scan"].astype(int)
            result[key] = df
        return result

    @staticmethod
    def parse_cdf(path: str) -> Dict[str, pd.DataFrame]:
        """Parse a netCDF (CDF) file containing mass‑spec data.

        The function first tries to use the ``netCDF4`` package.  If
        unavailable, it falls back to SciPy's ``netcdf_file``.  The file
        must contain the variables ``scan_index``, ``point_count``,
        ``mass_values`` and ``intensity_values``.  A variable
        ``scan_acquisition_time``, ``scan_time`` or ``retention_time``
        provides the retention times.

        Parameters
        ----------
        path : str
            Path to the CDF file.

        Returns
        -------
        dict
            A single‑item mapping from ``<basename>_Function_1`` to a
            DataFrame with columns ``Scan``, ``Retention Time``,
            ``Channel`` and ``Intensity``.
        """
        def _load_dataset(p: str):
            if netCDF4 is not None:
                return netCDF4.Dataset(p)
            if netcdf_file is not None:
                return netcdf_file(p, 'r')  # type: ignore[call-arg]
            raise ImportError("Neither netCDF4 nor scipy.io.netcdf_file is available to read CDF files")

        ds = _load_dataset(path)
        try:
            scan_index = ds.variables["scan_index"][:]
            point_count = ds.variables["point_count"][:]
            # m/z (channel) values
            if "mass_values" in ds.variables:
                mass_values = ds.variables["mass_values"][:]
            elif "mass_range" in ds.variables:
                mass_values = ds.variables["mass_range"][:]
            elif "mz" in ds.variables:
                mass_values = ds.variables["mz"][:]
            else:
                raise KeyError("Variable for mass values not found in CDF file")
            # intensity values
            if "intensity_values" in ds.variables:
                intensity_values = ds.variables["intensity_values"][:]
            elif "intensity" in ds.variables:
                intensity_values = ds.variables["intensity"][:]
            else:
                raise KeyError("Variable for intensity values not found in CDF file")
            # retention time values
            if "scan_acquisition_time" in ds.variables:
                rt_vals = ds.variables["scan_acquisition_time"][:]
            elif "scan_time" in ds.variables:
                rt_vals = ds.variables["scan_time"][:]
            elif "retention_time" in ds.variables:
                rt_vals = ds.variables["retention_time"][:]
            else:
                raise KeyError("Variable for retention time not found in CDF file")
        except Exception as exc:
            try:
                ds.close()
            except Exception:
                pass
            raise ValueError(f"CDF parsing error: {exc}")
        rows: List[Tuple[int, float, float, float]] = []
        n_scans = len(scan_index)
        for i in range(n_scans):
            start = int(scan_index[i])
            count = int(point_count[i])
            channels = mass_values[start : start + count]
            intensities = intensity_values[start : start + count]
            rt = float(rt_vals[i]) if i < len(rt_vals) else 0.0
            scan_number = i + 1
            for ch, inten in zip(channels, intensities):
                rows.append((scan_number, rt, float(ch), float(inten)))
        try:
            ds.close()
        except Exception:
            pass
        basename = os.path.splitext(os.path.basename(path))[0]
        key = f"{basename}_Function_1"
        df = pd.DataFrame(rows, columns=["Scan", "Retention Time", "Channel", "Intensity"])
        df["Scan"] = df["Scan"].astype(int)
        return {key: df}