-- =========================
-- Options par défaut
-- =========================
local config = {
    host = "0.0.0.0",
    port = 9000,
    timeout = 60,
    verbose = false,
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
local tm = require("tm")
local handle = require("handle")

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

utils.log("Client connected")

-- Initialize the RPC instance for this specific connection
local rpc = JSONRPC.new(client_sock)

tm._init_api(rpc)
utils.setup_remote_print(rpc)

rpc:register("func_call", handle.func_call)

-- Communication Loop for this client
rpc:loop()

client_sock:close()
utils.log("Server stopped")
