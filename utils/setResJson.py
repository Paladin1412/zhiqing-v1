"""
Special json encoder for numpy types
"""

import numpy as np
from flask import json


class MyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """

    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32,
                              np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):  # This is the fix
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def set_resjson(err=0, errmsg="OK", res_array=None):
    if res_array is None:
        res_array = []
    res_dict = {"err": err, "errmsg": errmsg,
                "count": len(res_array), "result_data": res_array}
    return json.dumps(res_dict, cls=MyEncoder)
