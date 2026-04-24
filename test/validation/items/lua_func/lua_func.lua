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

function module.set_context_value(val)
    tm.setgd("_lua_ctx_test_value", val)
    return val
end

function module.get_context_value()
    return tm.gd("_lua_ctx_test_value")
end

function module.test_delgd()
    tm.setgd("_lua_delgd_test", 42)
    assert(tm.gd("_lua_delgd_test") == 42)
    tm.delgd("_lua_delgd_test")
    assert(tm.gd("_lua_delgd_test") == nil)
    return 0
end

return module