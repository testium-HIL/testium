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

# Run a code snippet at global level.
proc ::tmhandle::run_code {params} {
    set code [dict get $params code]
    set rc [catch {uplevel #0 $code} ret opts]
    switch -exact -- $rc {
        0 - 2 { return $ret }
        1 {
            set info [UserTrace [dict get $opts -errorinfo] \
                "invoked from within\n\"uplevel #0 \$code\""]
            error [string map {"(\"uplevel\" body line" "(sandbox line"} $info]
        }
        default {
            error "'break' or 'continue' outside a loop"
        }
    }
}

# Names completing prefix, each one a replacement of the whole prefix.
# A prefix starting with $ completes a variable, any other a command.
proc ::tmhandle::complete {params} {
    set prefix [dict get $params prefix]
    set names [list]
    if {[string index $prefix 0] eq "\$"} {
        set stem [string range $prefix 1 end]
        foreach v [uplevel #0 [list info vars $stem*]] {
            lappend names "\$$v"
        }
    } else {
        foreach c [uplevel #0 [list info commands $prefix*]] {
            if {![string match ::* $prefix]} {
                set c [string trimleft $c :]
            }
            lappend names $c
        }
        set parent [namespace qualifiers $prefix]
        if {$parent eq "" && ![string match ::* $prefix]} {
            set children [namespace children ::]
            set strip 2
        } else {
            set children [expr {[namespace exists ::[string trimleft $parent :]]
                ? [namespace children ::[string trimleft $parent :]] : [list]}]
            set strip [expr {[string match ::* $prefix] ? 0 : 2}]
        }
        foreach ns $children {
            set name [string range $ns $strip end]
            if {[string match $prefix* $name]} {
                lappend names ${name}::
            }
        }
    }
    set out [list]
    foreach n [lsort -unique $names] {
        lappend out [::tm::str $n]
    }
    return [::tm::list $out]
}
