# Import as little here as possible, because we are running as root!
import os
import pwd
import sys
from socket import socketpair

student_user = "student"
grader_user = "grader"

def become(user):
    """Switch to another user (need to be root first)."""
    u = pwd.getpwnam(user)
    os.environ["LOGNAME"] = os.environ["USER"] = u.pw_name
    os.environ["PWD"] = os.getcwd()
    os.environ["HOME"] = u.pw_dir
    os.environ["SHELL"] = u.pw_shell
    os.setregid(u.pw_gid, u.pw_gid)
    try:
        os.initgroups(user, u.pw_gid)
    except OverflowError:
        pass  # FIXME???
    os.setreuid(u.pw_uid, u.pw_uid)


assert os.name == "posix"
assert os.getuid() == 0, "graderutils must be run as root for uid switching"

control = socketpair()
pid = os.fork()

if pid == 0:  # Child process: rpyc server running student code
    status = 250
    try:
        become(student_user)
        sys.path[0] += "/student"
        control[0].close()
        with control[1] as sock:
            status = 251
            from graderutils.remote import run_server
            run_server()
        status = 0
    finally:
        os._exit(status)
else:  # Grader process
    become(grader_user)
    sys.path[0] += "/grader"
    control[1].close()
    with control[0] as sock:
        from graderutils.remote import manage_server
        from graderutils.main import cli_main
        with manage_server(pid) as conn:
            cli_main()
