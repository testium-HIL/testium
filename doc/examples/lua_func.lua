tm = require("tm")
socket = require("socket")

local module = {}

function module.func_to_be_executed(param)
    -- return tm.gd(param)
    return param
end

function module.long_wait(sec)
    socket.sleep(sec)
end

return module