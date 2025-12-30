local json = require("cjson")

local JSONRPC = {}
JSONRPC.__index = JSONRPC

function JSONRPC.new(send_fn)
    local self = setmetatable({}, JSONRPC)
    self.send_raw = send_fn -- Function to transmit string data to transport (TCP/Websocket)
    self.methods = {}       -- Methods the server provides to the client
    self.pending = {}       -- Requests sent to client waiting for response
    self.next_id = 1
    return self
end

--- Register a method the client can call
function JSONRPC:register(name, callback)
    self.methods[name] = callback
end

--- Handle incoming raw data from the transport layer
function JSONRPC:handle_message(raw_data)
    local ok, msg = pcall(json.decode, raw_data)
    if not ok then return self:_send_error(nil, -32700, "Parse error") end

    -- 1. Check if it's a Response (has 'result' or 'error' and 'id')
    if msg.result ~= nil or msg.error ~= nil then
        return self:_handle_response(msg)
    end

    -- 2. Check if it's a Request
    if msg.method then
        return self:_handle_request(msg)
    end
end

--- INTERNAL: Handle requests from the client
function JSONRPC:_handle_request(req)
    local method = self.methods[req.method]
    if not method then
        if req.id then self:_send_error(req.id, -32601, "Method not found") end
        return
    end

    local ok, result = pcall(method, req.params)

    -- Only send response if it's not a Notification (notifications have no ID)
    if req.id then
        if ok then
            self:_send({ jsonrpc = "2.0", result = result, id = req.id })
        else
            self:_send_error(req.id, -32603, "Internal error: " .. tostring(result))
        end
    end
end

--- INTERNAL: Handle responses to requests WE sent
function JSONRPC:_handle_response(res)
    local callback = self.pending[res.id]
    if callback then
        callback(res.error, res.result)
        self.pending[res.id] = nil
    end
end

--- Call a method on the client
function JSONRPC:call(method, params, callback)
    local id = self.next_id
    self.next_id = self.next_id + 1

    if callback then
        self.pending[id] = callback
    end

    self:_send({
        jsonrpc = "2.0",
        method = method,
        params = params,
        id = id
    })
end

function JSONRPC:call_sync(method, params)
    local callco = coroutine.create(function(m, p)
        local co = coroutine.running()
        -- Call the async version, but use the callback to resume this coroutine
        self:call(m, p, function(err, res)
            coroutine.resume(co, err, res)
        end)

        -- Pause execution here until 'resume' is called
        return coroutine.yield()
    end)
    return coroutine.resume(callco, method, params)
end

function JSONRPC:_send(data)
    self.send_raw(json.encode(data))
end

function JSONRPC:_send_error(id, code, message)
    self:_send({
        jsonrpc = "2.0",
        error = { code = code, message = message },
        id = id
    })
end

return JSONRPC