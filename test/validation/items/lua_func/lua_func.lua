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
    assert(param=='test parameter')
    return 0
end

function module.checkglobal2(index)
    return tm.gd("data_to_be_returned")[index+1]
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
    assert(tm.gd("_lua_delgd_test", "__deleted__") == "__deleted__")
    return 0
end

function module.return_nothing()
    -- Returns no value: ret is nil but no error.
end

function module.return_explicit_none()
    return nil
end

return module