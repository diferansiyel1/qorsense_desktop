import logging

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("FileLoadWorker")

class FileLoadWorker(QThread):
    """
    Background worker for loading generic files (CSV/Excel) to avoid freezing GUI
    on slow network/cloud drives.
    """
    finished = pyqtSignal(dict, str) # Emits (data_dict, filepath)
    error = pyqtSignal(str)          # Emits error message

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            logger.info(f"Starting background load for: {self.filepath}")

            import io
            import os
            import time

            file_size_mb = os.path.getsize(self.filepath) / (1024 * 1024)
            logger.info(f"File size: {file_size_mb:.2f} MB")

            if file_size_mb > 500:
                raise ValueError(f"Dosya çok büyük ({file_size_mb:.1f} MB). Maksimum limit 500 MB.")

            # --- CLOUD DRIVE STRATEGY ---
            # For small files (<50MB), we pre-read into RAM to prevent cloud timeouts.
            # For large files (>50MB), we skip this to avoid OOM crashes (Double RAM usage).

            if file_size_mb < 50:
                raw_data = None
                max_retries = 3

                for attempt in range(max_retries):
                    try:
                        with open(self.filepath, 'rb') as f:
                            raw_data = f.read()
                        break # Success
                    except OSError as e:
                        if e.errno == 60: # ETIMEDOUT
                            logger.warning(f"Timeout on attempt {attempt+1}. Retrying in 2s...")
                            time.sleep(2.0)
                        else:
                            raise e

                if raw_data is None:
                    raise TimeoutError("Bulut depolamadan dosya indirilemedi.")

                file_buffer = io.BytesIO(raw_data)
            else:
                # Direct pointer for large files
                logger.info("Large file detected - skipping pre-buffer to save memory.")
                file_buffer = self.filepath
            # -----------------------

            if self.filepath.endswith('.csv') or self.filepath.endswith('.txt'):
                try:
                    # First try standard CSV
                    df = pd.read_csv(file_buffer)

                    # If it looks like it failed (1 column), try other separators or engines
                    if len(df.columns) < 2:
                         file_buffer.seek(0)
                         # Explicitly check for whitespace delimiter common in text data files
                         try:
                             df_white = pd.read_csv(file_buffer, sep=r'\s+')
                             if len(df_white.columns) > 1:
                                 df = df_white
                             else:
                                 # Try semicolon
                                 file_buffer.seek(0)
                                 df_semi = pd.read_csv(file_buffer, sep=';')
                                 if len(df_semi.columns) > 1:
                                     df = df_semi
                         except:
                            pass # Fallback to original single-column DF if deeper checks fail

                    # If still 1 column, it might be a raw data file (value only)
                    # We accept it, but we'll flag it implicitly by its shape

                except:
                    file_buffer.seek(0)
                    # Last resort: python engine with automatic separator detection
                    df = pd.read_csv(file_buffer, sep=None, engine='python')
            else:
                df = pd.read_excel(file_buffer)

            value_col = None
            candidates = ['value', 'signal', 'data', 'sensor_value', 'v']
            cols_lower = {col.lower(): col for col in df.columns}

            for candidate in candidates:
                if candidate in cols_lower:
                    value_col = cols_lower[candidate]
                    break

            if value_col is None:
                numeric_cols = df.select_dtypes(include=['float', 'int']).columns.tolist()
                if len(numeric_cols) == 1:
                    value_col = numeric_cols[0]
                elif len(numeric_cols) == 0:
                    raise ValueError("No numeric data found.")
                else:
                    pass

            # Force numeric conversion for all columns that might contain data
            # This handles cases like "6.Ara" (December 6th in TR locale) appearing in numeric columns
            for col in df.columns:
                 # Try to convert to numeric, coercing errors to NaN
                 # We only do this if the column is object type
                 if df[col].dtype == 'object':
                     try:
                         # Check if it has at least SOME numbers
                         # Simple heuristic: try converting a sample
                         sample = df[col].dropna().iloc[:10]
                         if not sample.empty:
                             pd.to_numeric(sample, errors='raise')
                             # If sample works (or fails only on some), fully convert
                             df[col] = pd.to_numeric(df[col], errors='coerce')
                     except:
                         # If sample conversion completely fails, try coerce anyway if it's the only column
                         if len(df.columns) == 1:
                              df[col] = pd.to_numeric(df[col], errors='coerce')

            numeric_df = df.select_dtypes(include=['float', 'int'])
            if numeric_df.empty:
                # One last try: if all columns were object and we didn't convert them yet
                for col in df.columns:
                     df[col] = pd.to_numeric(df[col], errors='coerce')
                numeric_df = df.select_dtypes(include=['float', 'int'])

            if numeric_df.empty:
                raise ValueError("No numeric data found (check file format/delimiters).")

            result_data = {col: numeric_df[col].dropna().tolist() for col in numeric_df.columns}
            self.finished.emit(result_data, self.filepath)

        except Exception as e:
            logger.error(f"File load error: {e}")
            self.error.emit(str(e))
