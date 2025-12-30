local utils = {}

utils.verbose = false

function utils.log(fmt, ...)
    if utils.verbose then
        -- print("[lua_func server]", ...)
        io.stdout:write(string.format("[lua_func server] - " .. fmt .. "\n", ...))
    end
end

utils.sep = package.config:sub(1,1)

function utils.join_paths(p1, p2)
    return p1 .. utils.sep .. p2
end

function utils.is_absolute_path(path)
    if not path or path == "" then return false end

    -- 1. Check for POSIX absolute path (starts with /)
    if path:sub(1, 1) == "/" then
        return true
    end

    -- 2. Check for Windows drive letter (e.g., C:\ or D:/)
    -- Pattern: %a (letter) followed by : (colon)
    if path:match("^%a:[/\\]") or path:match("^%a:$") then
        return true
    end

    -- 3. Check for Windows UNC/Network paths (starts with \\ or //)
    if path:match("^[/\\][/\\]") then
        return true
    end

    return false
end

function utils.is_relative_path(path)
    return not utils.is_absolute_path(path)
end

function utils.setup_remote_print(rpc)
    -- Store the original print if you still need to log to the server console
    _G.native_print = _G.native_print or _G.print

    -- Define the new local print
    _G.print = function (...)
        local args = table.pack(...)
        local output = {}

        for i = 1, args.n do
            table.insert(output, tostring(args[i]))
        end

        local message = table.concat(output, "\t")

        pcall(function()
            rpc:call_sync("print", message )
        end)
        -- Optional: Still print to the server's local console
        -- utils.log("[Remote Log Sent]: " .. message)
    end
end

return utils