tm = require("tm")

local module = {}

function module.donothing(param)
    return 0
end

function module.assertparam(param)
    assert(param)
    return 0
end

function module.checkglobal(param)
    local res = tm.gd(param)
    return res
end

function module.checkglobal2(index)
    return tm.gd("lua_data_to_be_returned")[index]
end

function module.should_not_be_called(param)
    assert(false)
end

function module.echo(param)
    return param
end

function module.tuple_return(first, second)
    return first, second
end


return module