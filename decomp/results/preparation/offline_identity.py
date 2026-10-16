"""Experimental socket filter for an unsuccessful adapter-visibility probe.

This does not modify adapter identity. AF_UNIX serves the private X/Wine session;
NETLINK_ROUTE supports interface discovery. Network configuration capabilities
remain dropped by bubblewrap. IP, packet, Bluetooth and VM sockets are denied.
Wine also needs an IP datagram socket for local adapter ioctls, so this policy
does NOT establish a usable Keil host identity. Never use it for activation.
"""
import ctypes
import errno
import os
import socket
import tempfile


class Comparison(ctypes.Structure):
    _fields_ = [('arg', ctypes.c_uint), ('op', ctypes.c_int),
                ('datum_a', ctypes.c_uint64), ('datum_b', ctypes.c_uint64)]


def socket_filter():
    lib = ctypes.CDLL('libseccomp.so.2')
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    lib.seccomp_arch_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int,
                                         ctypes.c_uint, ctypes.POINTER(Comparison)]
    lib.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    ctx = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    if not ctx:
        raise RuntimeError('seccomp initialization failed')
    stream = tempfile.TemporaryFile()

    def checked(value):
        if value < 0:
            raise OSError(-value, os.strerror(-value))

    def deny(name, *comparisons):
        number = lib.seccomp_syscall_resolve_name(name.encode())
        if number < 0:
            raise RuntimeError(f'unknown syscall: {name}')
        values = (Comparison * len(comparisons))(*comparisons)
        checked(lib.seccomp_rule_add_array(ctx, 0x00050000 | errno.EPERM,
                                          number, len(values), values))
    try:
        checked(lib.seccomp_arch_add(ctx, 0x40000003))  # x86
        checked(lib.seccomp_arch_add(ctx, 0x4000003e))  # x32
        for name in ('socket', 'socketpair'):
            for domain in range(65):
                if domain not in (socket.AF_UNIX, socket.AF_NETLINK):
                    deny(name, Comparison(0, 4, domain, 0))  # EQ
            deny(name, Comparison(0, 5, 65, 0))  # GE
        # Restrict allowed netlink sockets to interface/routing queries.
        deny('socket', Comparison(0, 4, socket.AF_NETLINK, 0), Comparison(2, 1, 0, 0))  # NE
        deny('io_uring_setup')  # no async socket creation outside this filter
        checked(lib.seccomp_export_bpf(ctx, stream.fileno()))
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise
    finally:
        lib.seccomp_release(ctx)


def check_offline():
    for domain in (socket.AF_INET, socket.AF_INET6, socket.AF_PACKET):
        try:
            connection = socket.socket(domain, socket.SOCK_DGRAM)
        except PermissionError:
            continue
        else:
            connection.close()
            raise RuntimeError('network socket unexpectedly allowed')
    with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, socket.NETLINK_ROUTE):
        pass
