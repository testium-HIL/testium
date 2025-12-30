
local tm = {}

local SUPPORTED_API = {
    "gd",
    "setgd",
    "delgd",
}

-- underlying function

function tm._init_api(rpc)
    tm._rpc = rpc

    local function _api_request(fname, ...)
        local args = {...}
        return tm._rpc:call_sync(fname, args)
    end

    for _, fname in ipairs(SUPPORTED_API) do
        -- create a closure that calls common_handler with fname
        tm[fname] = function(...)
            return _api_request(fname, ...)
        end
    end

end

return tm
