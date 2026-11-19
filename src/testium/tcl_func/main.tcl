# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur

# tcl_func worker: JSON-RPC server executing the functions of the test scripts.

if {[package vcompare [info patchlevel] 8.6] < 0} {
    puts stderr "tcl_func: Tcl 8.6 or later is required, found [info patchlevel]"
    exit 1
}

set ::tm_dir [file dirname [file normalize [info script]]]
foreach f {utils json jsonrpc tm handle} {
    source -encoding utf-8 [file join $::tm_dir $f.tcl]
}

proc usage {} {
    ::tmutils::native_puts {Usage: tclsh main.tcl [options]

Options:
  --host <ip>        Listening address (default: 127.0.0.1)
  --port <port>      TCP port, 0 = chosen by the system (default: 0)
  --timeout <sec>    Time allowed for the client to connect (default: 60)
  --verbose          Detailed log
  --help             Show this help}
    exit 0
}

set host 127.0.0.1
set port 0
set timeout 60

for {set i 0} {$i < $argc} {incr i} {
    set a [lindex $argv $i]
    switch -exact -- $a {
        --host { set host [lindex $argv [incr i]] }
        --port { set port [lindex $argv [incr i]] }
        --timeout { set timeout [lindex $argv [incr i]] }
        --verbose { set ::tmutils::verbose 1 }
        --help { usage }
        default {
            ::tmutils::native_puts "Unknown option: $a"
            usage
        }
    }
}

set ::client ""
proc accept {chan addr cport} {
    if {$::client ne ""} {
        close $chan
        return
    }
    set ::client $chan
}

if {[catch {socket -server accept -myaddr $host $port} server]} {
    ::tmutils::native_puts stderr "tcl_func: cannot bind $host:$port: $server"
    exit 1
}
set port [lindex [fconfigure $server -sockname] 2]
::tmutils::log "listening on $host:$port for $timeout secs"

# Announce the bound port: the parent connects only once we listen.
::tmutils::native_puts stdout "__TESTIUM_RPC_PORT__=$port"
flush stdout

set timer [after [expr {int($timeout * 1000)}] {set ::client timeout}]
vwait ::client
after cancel $timer
close $server

if {$::client eq "timeout"} {
    ::tmutils::native_puts stderr "tcl_func: no client connected on $host:$port"
    exit 1
}

::tmutils::log "Client connected"
::tmrpc::attach $::client
::tmrpc::register func_call ::tmhandle::func_call
::tmrpc::register run_code ::tmhandle::run_code
::tmrpc::register complete ::tmhandle::complete
::tmrpc::loop

catch {close $::client}
::tmutils::log "Server stopped"
exit 0
