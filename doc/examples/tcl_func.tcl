# Example Tcl script for the tcl_func test item (see example_tcl.tum).
# The tm:: procedures are always available: the testium Tcl worker loads
# them before sourcing this file.

# Basic call: adds its parameters. testium numbers arrive as text, so
# expr does the arithmetic; the result comes back as a testium number.
proc sum {a b c} {
    return [expr {$a + $b + $c}]
}

# Typed return value. tm::str, tm::bool and tm::list force the type of
# their argument, and tm::dict marks the whole dict: without the tags,
# the value would come back to testium as a single string.
proc measure {} {
    puts "measure: reading the (fake) sensor"
    dict set result voltage 3.3
    dict set result serial [tm::str 0012]
    dict set result ok [tm::bool 1]
    dict set result samples [tm::list {1 2 3}]
    return [tm::dict $result]
}

# Sharing state with the test: tm::setgd writes a testium global
# variable, tm::gd reads one back (the optional second argument is the
# default value when the variable does not exist).
proc produce {val} {
    tm::setgd tcl_shared_value $val
    return $val
}

proc consume {} {
    return [tm::gd tcl_shared_value missing]
}

# Persistent process: called twice with the same context_id, the global
# variable below survives between the calls. The script is sourced again
# on every call, so it must not reset ::call_count.
proc count_calls {} {
    return [incr ::call_count]
}
