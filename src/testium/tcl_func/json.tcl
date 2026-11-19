# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur

# JSON codec without tcllib.
# Decoding: array -> list, object -> dict, null -> empty string.
# Encoding: scalars are inferred, structures need a tagged fragment
# (see tm::list, tm::dict in tm.tcl).

namespace eval ::tmjson {
    # Prefix of an already encoded JSON fragment.
    variable TAG "\u0000J\u0000"
    # True when one character can hold a code point above U+FFFF.
    variable wide [expr {[scan [format %c 0x1F600] %c] == 0x1F600}]
}

# ---------- Decoding ----------

proc ::tmjson::decode {text} {
    set i 0
    set v [Value $text i]
    SkipWs $text i
    if {$i < [string length $text]} {
        error "JSON: unexpected data at offset $i"
    }
    return $v
}

proc ::tmjson::SkipWs {text iVar} {
    upvar 1 $iVar i
    regexp -start $i -indices {\A[ \t\r\n]*} $text m
    set i [expr {[lindex $m 1] + 1}]
}

proc ::tmjson::Value {text iVar} {
    upvar 1 $iVar i
    SkipWs $text i
    switch -exact -- [string index $text $i] {
        "\{" { return [Object $text i] }
        "\[" { return [Array $text i] }
        "\"" { return [String $text i] }
    }
    if {[regexp -start $i \
            {\A(?:true|false|null|-?[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)} \
            $text m]} {
        incr i [string length $m]
        if {$m eq "null"} { return "" }
        return $m
    }
    error "JSON: unexpected character at offset $i"
}

proc ::tmjson::Object {text iVar} {
    upvar 1 $iVar i
    incr i
    set d [dict create]
    SkipWs $text i
    if {[string index $text $i] eq "\}"} {
        incr i
        return $d
    }
    while 1 {
        SkipWs $text i
        if {[string index $text $i] ne "\""} {
            error "JSON: object key expected at offset $i"
        }
        set k [String $text i]
        SkipWs $text i
        if {[string index $text $i] ne ":"} {
            error "JSON: ':' expected at offset $i"
        }
        incr i
        dict set d $k [Value $text i]
        SkipWs $text i
        set c [string index $text $i]
        incr i
        if {$c eq "\}"} { return $d }
        if {$c ne ","} {
            error "JSON: ',' or '\}' expected at offset [expr {$i - 1}]"
        }
    }
}

proc ::tmjson::Array {text iVar} {
    upvar 1 $iVar i
    incr i
    set l [list]
    SkipWs $text i
    if {[string index $text $i] eq "\]"} {
        incr i
        return $l
    }
    while 1 {
        lappend l [Value $text i]
        SkipWs $text i
        set c [string index $text $i]
        incr i
        if {$c eq "\]"} { return $l }
        if {$c ne ","} {
            error "JSON: ',' or '\]' expected at offset [expr {$i - 1}]"
        }
    }
}

proc ::tmjson::String {text iVar} {
    upvar 1 $iVar i
    if {![regexp -start $i -indices {\A"((?:[^"\\]|\\.)*)"} $text m body]} {
        error "JSON: unterminated string at offset $i"
    }
    set raw [string range $text [lindex $body 0] [lindex $body 1]]
    set i [expr {[lindex $m 1] + 1}]
    if {[string first "\\" $raw] < 0} { return $raw }
    return [Unescape $raw]
}

proc ::tmjson::Unescape {raw} {
    variable wide
    set out ""
    set pos 0
    while {[set k [string first "\\" $raw $pos]] >= 0} {
        append out [string range $raw $pos [expr {$k - 1}]]
        set e [string index $raw [expr {$k + 1}]]
        set pos [expr {$k + 2}]
        switch -exact -- $e {
            n { append out "\n" }
            t { append out "\t" }
            r { append out "\r" }
            b { append out "\b" }
            f { append out "\f" }
            u {
                set hex [string range $raw $pos [expr {$pos + 3}]]
                if {![regexp {^[0-9a-fA-F]{4}$} $hex]} {
                    error "JSON: bad \\u escape '$hex'"
                }
                scan $hex %x code
                incr pos 4
                set low [string range $raw $pos [expr {$pos + 5}]]
                if {$wide && $code >= 0xD800 && $code <= 0xDBFF
                        && [regexp {^\\u([dD][c-fC-F][0-9a-fA-F]{2})$} $low -> lhex]} {
                    scan $lhex %x lcode
                    set code [expr {0x10000 + (($code - 0xD800) << 10) + ($lcode - 0xDC00)}]
                    incr pos 6
                }
                append out [format %c $code]
            }
            default { append out $e }
        }
    }
    append out [string range $raw $pos end]
    return $out
}

# ---------- Encoding ----------

proc ::tmjson::quote {s} {
    set s [string map [list \
        "\\" "\\\\" "\"" "\\\"" "\n" "\\n" "\r" "\\r" "\t" "\\t" \
        "\b" "\\b" "\f" "\\f"] $s]
    if {![regexp {[^\x20-\x7e]} $s]} {
        return "\"$s\""
    }
    set out ""
    foreach ch [split $s ""] {
        scan $ch %c code
        if {$code >= 0x20 && $code <= 0x7e} {
            append out $ch
        } elseif {$code > 0xFFFF} {
            set code [expr {$code - 0x10000}]
            append out [format "\\u%04x\\u%04x" \
                [expr {0xD800 + ($code >> 10)}] \
                [expr {0xDC00 + ($code & 0x3FF)}]]
        } else {
            append out [format "\\u%04x" $code]
        }
    }
    return "\"$out\""
}

proc ::tmjson::tagged {fragment} {
    variable TAG
    return "$TAG$fragment"
}

proc ::tmjson::is_tagged {v} {
    variable TAG
    return [expr {[string range $v 0 2] eq $TAG}]
}

# Encode a Tcl value: tagged fragment as is, empty string as null,
# number and true/false by inference, anything else as a string.
proc ::tmjson::encode {v} {
    if {[is_tagged $v]} {
        return [string range $v 3 end]
    }
    if {$v eq ""} {
        return "null"
    }
    if {$v eq "true" || $v eq "false"} {
        return $v
    }
    if {[regexp {^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?$} $v]} {
        return $v
    }
    return [quote $v]
}

proc ::tmjson::encode_list {l} {
    set parts [list]
    foreach e $l {
        lappend parts [encode $e]
    }
    return "\[[join $parts ,]\]"
}

proc ::tmjson::encode_dict {d} {
    set parts [list]
    dict for {k v} $d {
        lappend parts "[quote $k]:[encode $v]"
    }
    return "\{[join $parts ,]\}"
}
