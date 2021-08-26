import importlib
import os
import sys
from contextlib import contextmanager
from shutil import copytree
from signal import SIGINT
from tempfile import TemporaryDirectory
from time import sleep

import rpyc
from rpyc.core import SlaveService
from rpyc.utils.server import OneShotServer

from graderutils import GraderUtilsError


sock_path = "/tmp/rpyc.sock"
conn = None # Give other modules (e.g., iotester) access to conn by defining it as global variable


def run_server():
    OneShotServer(SlaveService, socket_path=sock_path).start()


@contextmanager
def manage_server(pid):
    global conn
    status = 0
    try:
        while not os.path.exists(sock_path):
            status = os.waitpid(pid, os.WNOHANG)[1]
            if status != 0:
                raise RuntimeError(f"Server did not start, exit status {status >> 8}")
            sleep(0.001)
        conn = rpyc.classic.unix_connect(sock_path)
        os.unlink(sock_path)
        with rpc_imports(conn):
            yield conn
    finally:
        if status == 0:
            status = os.waitpid(pid, os.WNOHANG)[1]
        if status == 0:
            os.kill(pid, SIGINT)
            os.waitpid(pid, 0)


@contextmanager
def tmpdir():
    origcwd = os.getcwd()
    with TemporaryDirectory(prefix="/tmp/") as tmpdir:
        try:
            copytree(origcwd, tmpdir, dirs_exist_ok=True)
            os.chdir(tmpdir)
            yield
        finally:
            os.chdir(origcwd)


# GraderImportError and GraderOpenError are defined here so that the remote server finds them
# and doesn't fall back to rpyc.core.vinegar serializer for exceptions during iotester tests
class GraderImportError(GraderUtilsError):
    pass


class GraderOpenError(GraderUtilsError):
    pass


class GraderConnClosedError(GraderUtilsError):
    pass


class RPCImport:
    def __init__(self, conn):
        self.conn = conn

    def redirect_stdio(self):
        self.conn.modules.sys.stdin = sys.stdin
        self.conn.modules.sys.stdout = sys.stdout
        self.conn.modules.sys.stderr = sys.stderr

    def find_module(self, fullname, path, target=None):
        # This method is run right before a module is imported and executed.
        # I/O is redirected here because IOTester replaces sys.stdin and
        # sys.stdout before running student code.
        self.redirect_stdio()
        self.module = getattr(self.conn.modules, fullname)
        return self

    def find_spec(self, name, path, target=None):
        # With rpyc _bootstrap._find_spec raises error and
        # falls back to _find_spec_legacy, so we just call it directly.
        # importlib.util.find_spec is not used because it tries to deduce path by itself.
        return importlib._bootstrap._find_spec_legacy(self, name, path)

    def create_module(self, spec):
        return self.module

    def exec_module(self, module):
        pass


@contextmanager
def rpc_imports(conn):
    importer = RPCImport(conn)
    sys.meta_path.append(importer)
    try:
        yield
    finally:
        sys.meta_path.remove(importer)
