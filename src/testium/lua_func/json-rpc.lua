local json = require("cjson")
local utils = require("utils")

local JSONRPC = {}
JSONRPC.__index = JSONRPC

function JSONRPC.new(sock)
    local self = setmetatable({}, JSONRPC)
    self.sock = sock  -- Function to transmit string data to transport (TCP/Websocket)
    self.methods = {} -- Methods the server provides to the client
    self.pending = {} -- Requests sent to client waiting for response
    self.next_id = 1

    self.sock:settimeout(0.2)
    return self
end

--- Register a method the client can call
function JSONRPC:register(name, callback)
    self.methods[name] = callback
end

--- Handle incoming raw data from the transport layer
function JSONRPC:handle_message(raw_data)
    utils.log("received: '%s'", raw_data)
    local ok, msg = pcall(json.decode, raw_data)
    if not ok then return self:_send_error(nil, "received message parse error in lua server") end

    -- 1. Check if it's a Response (has 'result' or 'error' and 'id')
    if (msg.id ~= nil) and (msg.result ~= nil or msg.error ~= nil) then
        self.pending[msg.id] = msg
        return
    end

    -- 2. Check if it's a Request
    if msg.method then
        return self:_handle_request(msg)
    end
end

--- INTERNAL: Handle requests from the client
function JSONRPC:_handle_request(req)
    local method = self.methods[req.method]
    local ok, ret
    local res, err
    if not method then
        if req.id then self:_send_error(req.id, string.format("Method '%s' not registered in lua server")) end
        return
    end
    ok, ret, err = pcall(method, req.params)
    utils.log("Call returned ok='%s', ret='%s'", tostring(ok), tostring(ret))

    -- Only send response if it's not a Notification (notifications have no ID)
    if req.id then
        if ok then
            res = ret
            if res == nil then
                self:_send_error(req.id, tostring(err))
            else
                self:_send({ jsonrpc = "2.0", result = { returned_value = res }, id = req.id })
            end
        else
            self:_send_error(req.id, tostring(err))
        end
    end
end

--- Call a method on the client
function JSONRPC:call(method, params)
    local id = self.next_id
    self.next_id = self.next_id + 1

    self:_send({
        jsonrpc = "2.0",
        method = method,
        params = params,
        id = id
    })

    -- ---- Wait for response (re-entrant loop)
    while true do
        self:poll()

        if self.pending[id] then
            local resp = self.pending[id]
            self.pending[id] = nil

            if resp.error then
                error(resp.error.message)
            end
            return resp.result
        end
    end
end

function JSONRPC:_send(data)
    local j = json.encode(data)
    utils.log("sending: '%s'", j)
    return self.sock:send(j .. "\n")
end

function JSONRPC:_send_error(id, message)
    self:_send({
        jsonrpc = "2.0",
        error = message,
        id = id
    })
end

function JSONRPC:poll()
    local line, err = self.sock:receive("*l")

    if line then
        self:handle_message(line)
    elseif err ~= "timeout" and err ~= nil then
        utils.log("Connection ended: %s", err)
        return false
    end
    return true
end

function JSONRPC:loop()
    while true do
        if not self:poll() then
            break
        end
    end
end

return JSONRPC
