"""Pure-Python Excel recalc via the `formulas` library (LibreOffice is blocked
in this sandbox). Loads an .xlsx, calculates, and exposes cell values by
sheet!coord. Also used to inject test scenarios and read results back."""
import os
import logging
import numpy as np
import formulas

logging.disable(logging.WARNING)

ERROR_TOKENS = ("#NAME?", "#DIV/0!", "#VALUE!", "#REF!", "#N/A", "#NUM!", "#NULL!")


class Calc:
    def __init__(self, path):
        self.book = "[" + os.path.basename(path) + "]"
        self.xl = formulas.ExcelModel().loads(path).finish()
        self.sol = self.xl.calculate()

    def _key(self, sheet, coord):
        return f"'{self.book}{sheet.upper()}'!{coord.upper()}"

    def get(self, sheet, coord):
        v = self.sol.get(self._key(sheet, coord))
        if v is None:
            return None
        val = getattr(v, "value", v)
        if isinstance(val, np.ndarray):
            if val.size == 0:
                return None
            val = val.ravel()[0]
        # normalise empty-string sentinel used by `formulas`
        if isinstance(val, str) and val == "":
            return ""
        try:
            if isinstance(val, float) and val.is_integer():
                return val
        except Exception:
            pass
        return val

    def scan_errors(self):
        hits = []
        for k, v in self.sol.items():
            val = getattr(v, "value", v)
            if isinstance(val, np.ndarray):
                if val.size == 0:
                    continue
                val = val.ravel()[0]
            if isinstance(val, str) and any(t in val for t in ERROR_TOKENS):
                hits.append((k, val))
        return hits
