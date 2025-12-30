local utils = require("utils")
local tm = require("tm")

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
        return nil, "Function '" .. func_name .. "' not found in " .. file_path
    end

    return target_func
end

function handle.func_call(file, fname, params)
    local pfile = file
    -- 1. modify the file path if it is relative
    if utils.is_relative_path(file) then
        local td = tm.gd("test_directory")
        pfile = utils.join_paths(td, file)
    end
    -- 2. retrieve the function "fname"
    local func, err = _get_func_by_path(pfile, fname)

    -- 3. Execute the function
    local res = nil
    if err == nil then
        succ, res = pcall(func, table.unpack(params))
    end

    -- 4. Returns result
    return res, err
end

return handle
