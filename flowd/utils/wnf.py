import ctypes


g_WellKnownWnfNames = {
    "WNF_SHEL_QUIET_MOMENT_SHELL_MODE_CHANGED": 0xd83063ea3bf5075,
    "WNF_SHEL_QUIETHOURS_ACTIVE_PROFILE_CHANGED": 0xd83063ea3bf1c75
}
ZwUpdateWnfStateData = ctypes.windll.ntdll.ZwUpdateWnfStateData
ZwQueryWnfStateData = ctypes.windll.ntdll.ZwQueryWnfStateData


def format_state_name(wnf_name):
    return "{:x}".format(g_WellKnownWnfNames[wnf_name.upper()])


def do_read(state_name) -> int:
    _, _, data_buffer, buffer_size = read_wnf_data(int(state_name, 16))
    return int(data_buffer.raw[0])


def read_wnf_data(state_name):
    change_stamp = ctypes.c_ulong(0)
    data_buffer = ctypes.create_string_buffer(4096)
    buffer_size = ctypes.c_ulong(ctypes.sizeof(data_buffer))
    state_name = ctypes.c_longlong(state_name)
    res = ZwQueryWnfStateData(ctypes.byref(state_name),
                              0, 0,
                              ctypes.byref(change_stamp),
                              ctypes.byref(data_buffer),
                              ctypes.byref(buffer_size)
                              )
    read_access = 0 if res != 0 else 1
    buffer_size = ctypes.c_ulong(0) if res != 0 else buffer_size
    return read_access, change_stamp.value, data_buffer, buffer_size.value


# Writes the given data into the given state name
def do_write(state_name, data):
    state_name = ctypes.c_longlong(int(state_name, 16))
    data_buffer = ctypes.c_char_p(data)
    buffer_size = len(data)
    status = ZwUpdateWnfStateData(ctypes.byref(state_name), data_buffer, buffer_size, 0, 0, 0, 0)
    status = ctypes.c_ulong(status).value

    if status == 0:
        return True
    else:
        print('[Error] Could not write for this statename: 0x{:x}'.format(status))
        return False

