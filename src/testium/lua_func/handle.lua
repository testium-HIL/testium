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
        return nil, "Module did not return a table (returned " .. type(module) .. ")"
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
                              local cut = tb:find("\n[^\n]*in function 'xpcall'")
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

return handle
