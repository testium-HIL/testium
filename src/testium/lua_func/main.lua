-- =========================
-- Options par défaut
-- =========================
local config = {
    host = "0.0.0.0",
    port = 9000,
    timeout = 60,
    verbose = true,
}

local function usage()
    print([[
Usage: lua lua_func [options]

Options:
  --host <ip>        Adresse d'écoute (default: 0.0.0.0)
  --port <port>      Port TCP (default: 9000)
  --timeout <sec>    Timeout client en secondes (default: 60)
  --verbose          Logs détaillés
  --help             Affiche cette aide
]])
    os.exit(0)
end

-- =========================
-- Parsing des arguments
-- =========================
local i = 1
while i <= #arg do
    local a = arg[i]

    if a == "--host" then
        i = i + 1
        config.host = arg[i]

    elseif a == "--port" then
        i = i + 1
        config.port = tonumber(arg[i])

    elseif a == "--timeout" then
        i = i + 1
        config.timeout = tonumber(arg[i])

    elseif a == "--verbose" then
        config.verbose = true

    elseif a == "--help" then
        usage()

    else
        print("Unknown option:", a)
        usage()
    end

    i = i + 1
end

local socket = require("socket")
local JSONRPC = require("json-rpc") -- The module from the previous response
local utils = require("utils")

utils.verbose = config.verbose

-- Create the master socket
local server_sock = assert(socket.bind(config.host, config.port))
utils.log("listening on %s:%d", config.host, config.port)

server_sock:settimeout(config.timeout) -- Prevents hanging on dead connections

-- Main Server Loop
local client_sock, err = server_sock:accept()
if err then
    utils.log("connection failed: %s", err)
    os.exit(0)
end

client_sock:settimeout(10) -- Prevents hanging on dead connections

utils.log("Client connected!")

-- Initialize the RPC instance for this specific connection
local rpc = JSONRPC.new(function(data)
    client_sock:send(data .. "\n") -- Standard JSON-RPC uses newline delimiters over TCP
end)

utils.setup_remote_print(rpc)

-- Define Server Methods
rpc:register("echo", function(params)
    return params
end)

-- Example: Send a request TO the client immediately upon connection
rpc:call("greet", { msg = "Welcome to the server" }, function(err, res)
    if not err then print("Client replied to greeting:", res) end
end)

-- Communication Loop for this client
while true do
    local line, err = client_sock:receive() -- Read until newline
    if err == "closed" then
        utils.log("Connection closed:", err)
        break
    elseif err then
        socket.sleep(0.01)
    else
        rpc:handle_message(line)
    end
end

client_sock:close()
