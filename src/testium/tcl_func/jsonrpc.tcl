# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur

# JSON-RPC 2.0 over one TCP connection, one JSON object per line.

namespace eval ::tmrpc {
    variable chan ""
    variable next_id 1
    variable methods
    array set methods {}
    variable pending
    array set pending {}
}

proc ::tmrpc::attach {c} {
    variable chan $c
    fconfigure $c -blocking 1 -translation lf -encoding utf-8 -buffering full
}

proc ::tmrpc::connected {} {
    variable chan
    return [expr {$chan ne ""}]
}

proc ::tmrpc::register {name cmd} {
    variable methods
    set methods($name) $cmd
}

proc ::tmrpc::Send {json} {
    variable chan
    ::tmutils::log "sending: '$json'"
    ::tmutils::native_puts $chan $json
    flush $chan
}

proc ::tmrpc::SendError {id message} {
    Send [::tmjson::encode_dict [dict create \
        jsonrpc [::tmjson::tagged "\"2.0\""] \
        error [::tmjson::tagged [::tmjson::quote $message]] \
        id $id]]
}

# Read and process one message. Returns 0 when the connection is closed.
proc ::tmrpc::Poll {} {
    variable chan
    if {[catch {gets $chan line} n] || $n < 0} {
        return 0
    }
    HandleMessage $line
    return 1
}

proc ::tmrpc::HandleMessage {raw} {
    variable pending
    ::tmutils::log "received: '$raw'"
    if {[catch {::tmjson::decode $raw} msg]} {
        SendError "" "received message parse error in tcl server: $msg"
        return
    }
    if {[dict exists $msg method]} {
        HandleRequest $msg
    } elseif {[dict exists $msg id]} {
        set pending([dict get $msg id]) $msg
    }
}

proc ::tmrpc::HandleRequest {req} {
    variable methods
    set name [dict get $req method]
    set id ""
    if {[dict exists $req id]} {
        set id [dict get $req id]
    }
    set params ""
    if {[dict exists $req params]} {
        set params [dict get $req params]
    }
    if {![info exists methods($name)]} {
        if {$id ne ""} {
            SendError $id "Method '$name' not registered in tcl server"
        }
        return
    }
    set failed [catch {{*}$methods($name) $params} ret]
    ::tmutils::log "Call returned failed='$failed', ret='$ret'"
    # A request without id is a notification: no answer.
    if {$id eq ""} {
        return
    }
    if {$failed} {
        SendError $id $ret
        return
    }
    if {[catch {::tmjson::encode $ret} encoded]} {
        SendError $id "cannot encode the returned value: $encoded"
        return
    }
    Send [::tmjson::encode_dict [dict create \
        jsonrpc [::tmjson::tagged "\"2.0\""] \
        result [::tmjson::tagged "\{\"returned_value\":$encoded\}"] \
        id $id]]
}

# Call a method of the peer. params is an encoded JSON fragment.
proc ::tmrpc::call {method params} {
    variable next_id
    variable pending
    set id $next_id
    incr next_id
    Send [::tmjson::encode_dict [dict create \
        jsonrpc [::tmjson::tagged "\"2.0\""] \
        method [::tmjson::tagged [::tmjson::quote $method]] \
        params [::tmjson::tagged $params] \
        id $id]]
    while {![info exists pending($id)]} {
        if {![Poll]} {
            error "connection to testium closed during the '$method' call"
        }
    }
    set resp $pending($id)
    unset pending($id)
    if {[dict exists $resp error]} {
        error [dict get $resp error]
    }
    if {[dict exists $resp result]} {
        return [dict get $resp result]
    }
    return ""
}

proc ::tmrpc::loop {} {
    while {[Poll]} {}
}
