# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur

namespace eval ::tmutils {
    variable verbose 0
}

rename ::puts ::tmutils::native_puts

proc ::tmutils::log {msg} {
    variable verbose
    if {$verbose} {
        native_puts stdout "\[tcl_func server\] - $msg"
        flush stdout
    }
}

# puts to stdout or stderr goes to the testium log, other channels are
# left untouched.
proc ::puts {args} {
    set argc [llength $args]
    set nonewline 0
    set rest $args
    if {$argc >= 2 && [lindex $args 0] eq "-nonewline"} {
        set nonewline 1
        set rest [lrange $args 1 end]
    }
    set chan stdout
    if {[llength $rest] == 2} {
        set chan [lindex $rest 0]
    }
    if {[llength $rest] < 1 || [llength $rest] > 2
            || $chan ni {stdout stderr} || ![::tmrpc::connected]} {
        return [uplevel 1 [list ::tmutils::native_puts {*}$args]]
    }
    set message [lindex $rest end]
    if {!$nonewline} {
        append message "\n"
    }
    catch {::tmrpc::call print [::tmjson::quote $message]}
    return
}
