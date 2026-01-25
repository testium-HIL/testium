from interpreter.utils.api import SUPPORTED_API

import libs.testium as tm

# Fill the api_dict with the function of tm
api_dict = {k: getattr(tm, k) for k in SUPPORTED_API if hasattr(tm, k)}

def api_request(method, params):
    global api_dict

    if method in api_dict.keys():
        if params is None:
            params = []
        if not isinstance(params, list):
            params = [params]
        try:
            return {"result": api_dict[method](*params)}
        except Exception as e:
            return {"error": str(e)}
    elif method == "print":
        if isinstance(params, str):
            print(params, end="")
        elif isinstance(params, list):
            print(*params, end="")
        return {"result": 0}
    else:
        return {"error": "unsupported function"}
