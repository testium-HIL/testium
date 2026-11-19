proc assertparam {param} {
    if {!$param} {
        error "assertion failed"
    }
    return 0
}

proc checkglobal {param} {
    if {$param ne "test parameter"} {
        error "unexpected parameter '$param'"
    }
    return 0
}

proc gd_scalar {index} {
    return [lindex [tm::gd data_to_be_returned] $index]
}

proc gd_dict {index} {
    return [tm::dict [lindex [tm::gd data_to_be_returned] $index]]
}

proc gd_list {index} {
    return [tm::list [lindex [tm::gd data_to_be_returned] $index]]
}

proc should_not_be_called {param} {
    error "this proc must not be called"
}

proc echo {param} {
    return $param
}

proc echo_list {param} {
    return [tm::list $param]
}

proc echo_nested {param} {
    lassign $param first second third
    return [tm::list [list $first $second [tm::dict $third]]]
}

proc as_string {param} {
    return [tm::str $param]
}

proc as_bool {param} {
    return [tm::bool $param]
}

proc as_null {} {
    return [tm::null]
}

proc pair_return {first second} {
    return [tm::list [list $first $second]]
}

proc dict_size {param} {
    return [dict size $param]
}

proc return_nothing {} {
}

proc print_lines {} {
    puts "line on stdout"
    puts stderr "line on stderr"
    puts -nonewline "no newline"
    return 0
}

proc fail_deep {value} {
    fail_inner $value
}

proc fail_inner {value} {
    error "bad value $value"
}

proc set_context_value {val} {
    tm::setgd _tcl_ctx_test_value $val
    return $val
}

proc get_context_value {} {
    return [tm::gd _tcl_ctx_test_value]
}

proc count_calls {} {
    return [incr ::tcl_func_call_count]
}

proc test_delgd {} {
    tm::setgd _tcl_delgd_test 42
    if {[tm::gd _tcl_delgd_test] != 42} {
        error "setgd failed"
    }
    tm::delgd _tcl_delgd_test
    if {[tm::gd _tcl_delgd_test __deleted__] ne "__deleted__"} {
        error "delgd failed"
    }
    return 0
}

proc setgd_types {} {
    tm::setgd _tcl_types [tm::dict [dict create \
        i 3 f 2.5 s text n [tm::str 12] b [tm::bool yes] z [tm::null] \
        l [tm::list {1 two}]]]
    return 0
}

namespace eval bench {
    proc voltage {} {
        return 3.3
    }
}
