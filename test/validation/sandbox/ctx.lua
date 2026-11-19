local module = {}

function module.set_state(value)
    ctx_value = value
    return value
end

function module.get_state()
    if ctx_value == nil then
        return "fresh"
    end
    return ctx_value
end

return module
