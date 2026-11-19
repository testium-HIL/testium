# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur

# testium API for Tcl test scripts.
# tm::list and tm::dict hide the Tcl commands inside this namespace:
# the code below calls ::list and ::dict explicitly.

namespace eval ::tm {}

# ---------- Typed values ----------

proc ::tm::list {l} {
    return [::tmjson::tagged [::tmjson::encode_list $l]]
}

proc ::tm::dict {d} {
    return [::tmjson::tagged [::tmjson::encode_dict $d]]
}

proc ::tm::str {v} {
    return [::tmjson::tagged [::tmjson::quote $v]]
}

proc ::tm::bool {v} {
    if {![string is boolean -strict $v]} {
        error "tm::bool: '$v' is not a boolean"
    }
    return [::tmjson::tagged [expr {$v ? "true" : "false"}]]
}

proc ::tm::null {} {
    return [::tmjson::tagged null]
}

# ---------- Global variables ----------

proc ::tm::gd {name args} {
    if {[llength $args] > 1} {
        error "wrong # args: should be \"tm::gd name ?default?\""
    }
    set params [::list [::tm::str $name]]
    if {[llength $args] == 1} {
        lappend params [lindex $args 0]
    }
    return [::tmrpc::call gd [::tmjson::encode_list $params]]
}

proc ::tm::setgd {name value} {
    ::tmrpc::call setgd [::tmjson::encode_list [::list [::tm::str $name] $value]]
    return
}

proc ::tm::delgd {name} {
    ::tmrpc::call delgd [::tmjson::encode_list [::list [::tm::str $name]]]
    return
}
