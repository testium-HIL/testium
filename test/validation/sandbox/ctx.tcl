proc set_state {value} {
    set ::ctx_value $value
    return $value
}

proc get_state {} {
    if {![info exists ::ctx_value]} {
        return fresh
    }
    return $::ctx_value
}
