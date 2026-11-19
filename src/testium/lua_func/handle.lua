local json = require("cjson")
local utils = require("utils")
local tm = require("tm")

local unpack = unpack or table.unpack

local handle = {}

local function _get_func_by_path(file_path, func_name)
    -- 1. Load the file from the path
    -- loadfile returns a 'chunk' (a function that runs the file's code)
    local chunk, load_err = loadfile(file_path)

    if not chunk then
        return nil, "Failed to load file: " .. tostring(load_err)
    end

    -- 2. Execute the chunk to get the module's return value
    -- Most Lua modules end with 'return { ... }'
    local ok, module = pcall(chunk)

    if not ok then
        return nil, "Error executing file: " .. tostring(module)
    end

    -- 3. Validate the module is a table and contains the function
    if type(module) ~= "table" then
        return nil, "Module '" .. file_path .. "' did not return a table (returned "
            .. type(module) .. "). The .lua file must end with 'return M' (its module table)."
    end

    local target_func = module[func_name]
    if type(target_func) ~= "function" then
        return nil, "Function '" .. func_name .. "' not found in '" .. file_path .. "'"
    end

    return target_func
end

function handle.func_call(params)
    local file = params.file
    local fname = params.fname
    local prms = params.params
    local res = nil
    local succ, ret

    local pfile = file
    -- 1. modify the file path if it is relative
    if utils.is_relative_path(pfile) then
        local td = tm.gd("test_directory")
        pfile = utils.join_paths(td, file)
    end

    -- 2. retrieve the function "fname"
    local func, err = _get_func_by_path(pfile, fname)

    -- 3. Execute the function
    if err == nil then
        print(string.format("Function executed from '%s'", pfile))
        utils.log("func_call function found '%s', '%s'", file, fname)
        -- manage tuple output of a lua function
        -- xpcall + debug.traceback: report the call stack, not only the
        -- innermost error line. Closure keeps Lua 5.1 compatibility
        -- (xpcall has no vararg forwarding there). The trace is cut at
        -- the xpcall frame so testium internals do not show.
        err_res = {xpcall(function() return func(unpack(prms)) end,
                          function(e)
                              local tb = debug.traceback(tostring(e), 2)
                              local cut = tb:find("\n[^\n]*in %a+ 'xpcall'")
                              if cut then tb = tb:sub(1, cut - 1) end
                              return tb
                          end)}
        succ = table.remove(err_res, 1)
        if #err_res > 1 then
            ret = err_res
        else
            ret = unpack(err_res)
        end
        utils.log("func_call returned '%s', '%s'", tostring(succ), tostring(ret))

        if succ then
            res = ret
        else
            err = ret
        end
    end

    -- 4. Returns result
    return res, err
end

-- Value that cjson can encode: functions and userdata as text.
local function _plain(v, depth, seen)
    local t = type(v)
    if t == "table" then
        if seen[v] or depth > 20 then return tostring(v) end
        seen[v] = true
        local out = {}
        for k, e in pairs(v) do
            local key = k
            if type(key) ~= "number" then key = tostring(key) end
            out[key] = _plain(e, depth + 1, seen)
        end
        seen[v] = nil
        return out
    elseif t == "nil" or t == "boolean" or t == "number" or t == "string" then
        return v
    end
    return tostring(v)
end

local load_chunk = loadstring or load

-- Run a code snippet at global level. An expression gives its value.
function handle.run_code(params)
    local code = params.code
    local chunk, err = load_chunk("return " .. code, "=sandbox")
    if not chunk then
        chunk, err = load_chunk(code, "=sandbox")
    end
    if not chunk then
        return nil, tostring(err)
    end
    local res = {xpcall(chunk, function(e)
        local tb = debug.traceback(tostring(e), 2)
        local cut = tb:find("\n[^\n]*in %a+ 'xpcall'")
        if cut then tb = tb:sub(1, cut - 1) end
        return tb
    end)}
    local succ = table.remove(res, 1)
    if not succ then
        return nil, res[1]
    end
    if #res > 1 then
        return _plain(res, 0, {})
    end
    return _plain(res[1], 0, {})
end

-- Names completing prefix, each one a replacement of the whole prefix.
function handle.complete(params)
    local prefix = params.prefix or ""
    local head, sep, tail = prefix:match("^(.*)([%.:])([%w_]*)$")
    local scope = _G
    if head then
        for name in head:gmatch("[^%.:]+") do
            local ok, sub = pcall(function() return scope[name] end)
            if not ok or type(sub) ~= "table" then return {} end
            scope = sub
        end
    else
        head, sep, tail = "", "", prefix
    end
    local names = {}
    for k in pairs(scope) do
        if type(k) == "string" and k:sub(1, #tail) == tail then
            names[#names + 1] = head .. sep .. k
        end
    end
    table.sort(names)
    if #names == 0 then
        return setmetatable({}, json.empty_array_mt)
    end
    return names
end

return handle
