# Import as little here as possible, because we are running as root!
import os
import pwd
import sys
from socket import socketpair

student_user = os.getenv("STUDENT_USER", "student")  # UNIX user to run user code as
grader_user = os.getenv("GRADER_USER", "grader")  # UNIX user to run grader as
student_path = os.getenv("STUDENT_PATH", "/submission/user")  # Submitted files
grader_path = os.getenv("GRADER_PATH", "/exercise")  # Unittest

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
stdin, stdout, stderr = os.pipe(), os.pipe(), os.pipe()
pid = os.fork()

if pid == 0:  # Child process: rpyc server running student code
    status = 250
    try:
        become(student_user)
        # Pipe I/O on fd level
        os.close(stdin[1])
        os.close(stdout[0])
        os.close(stderr[0])
        control[0].close()
        with control[1] as sock:
            status = 251
            from graderutils.remote import run_server
            sys.path[0] = student_path
            run_server()
        status = 0
    finally:
        os._exit(status)
else:  # Grader process
    become(grader_user)
    os.close(stdin[0])
    os.close(stdout[1])
    os.close(stderr[1])
    stdin = open(stdin[1], "wb")
    stdout = open(stdout[0], "rb")
    stderr = open(stderr[0], "rb")
    control[1].close()
    with control[0] as sock, stdin, stdout, stderr:
        from graderutils.remote import manage_server
        from graderutils.main import cli_main
        with manage_server(pid) as conn:
            sys.path[0] = grader_path
            cli_main()
