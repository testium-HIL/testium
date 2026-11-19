# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur

namespace eval ::tmhandle {}

# Error trace cut before the frame of this file starting with marker.
proc ::tmhandle::UserTrace {info marker} {
    set cut [string last "\n    $marker" $info]
    if {$cut >= 0} {
        set info [string range $info 0 [expr {$cut - 1}]]
    }
    return $info
}

proc ::tmhandle::func_call {params} {
    set file [dict get $params file]
    set fname [dict get $params fname]
    set prms ""
    if {[dict exists $params params]} {
        set prms [dict get $params params]
    }

    set pfile $file
    if {[file pathtype $pfile] eq "relative"} {
        set pfile [file join [::tm::gd test_directory] $file]
    }
    if {![file isfile $pfile]} {
        error "Failed to load file: '$pfile' not found"
    }

    if {[catch {uplevel #0 [list source -encoding utf-8 $pfile]} msg opts]} {
        error "Error executing file '$pfile':\n[UserTrace [dict get $opts -errorinfo] "invoked from within\n\"source -encoding utf-8"]"
    }

    if {[uplevel #0 [list namespace which -command $fname]] eq ""} {
        error "Proc '$fname' not found in '$pfile'"
    }

    puts "Function executed from '$pfile'"
    ::tmutils::log "func_call proc found '$file', '$fname'"

    set code [catch {uplevel #0 [list $fname {*}$prms]} ret opts]
    ::tmutils::log "func_call returned code='$code', '$ret'"
    switch -exact -- $code {
        0 - 2 { return $ret }
        1 { error [UserTrace [dict get $opts -errorinfo] "(\"uplevel\" body line"] }
        default {
            error "Proc '$fname' ended with 'break' or 'continue' outside a loop"
        }
    }
}
