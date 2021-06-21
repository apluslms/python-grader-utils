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

sock_path = "/tmp/rpyc.sock"


def run_server():
    OneShotServer(SlaveService, socket_path=sock_path).start()


@contextmanager
def manage_server(pid):
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


class RPCImport:
    def __init__(self, conn):
        self.conn = conn

    def find_module(self, fullname, path, target=None):
        self.module = getattr(self.conn.modules, fullname)
        return self

    def find_spec(self, name, path, target=None):
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
