import json
import numpy as np
from datetime import datetime
import fitz

class RobustJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, fitz.Rect):
            return {"x0": obj.x0, "y0": obj.y0, "x1": obj.x1, "y1": obj.y1}
        return super().default(obj)
