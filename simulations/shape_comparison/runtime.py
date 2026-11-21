"""Local OOMMF execution under a reduced Windows token; no solver patches."""
import os
from pathlib import Path
import subprocess
import time
import msvcrt
import win32api
import win32con
import win32event
import win32process
import win32security
import win32service
import pywintypes

ROOT = Path(__file__).resolve().parents[2]
TCL = Path('D:/Git/mingw64/bin/tclsh.exe')
OOMMF = ROOT / '.tools/oommf20b0/oommf/oommf.tcl'
_desktop_handles = None


def private_desktop(token):
    global _desktop_handles
    if _desktop_handles is None:
        user = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        acl = win32security.ACL()
        acl.AddAccessAllowedAce(win32security.ACL_REVISION, win32con.GENERIC_ALL, user)
        sa = pywintypes.SECURITY_ATTRIBUTES()
        sa.SECURITY_DESCRIPTOR.SetSecurityDescriptorDacl(True, acl, False)
        name = f'oommf_{os.getpid()}'
        previous = win32service.GetProcessWindowStation()
        station = win32service.CreateWindowStation(name, 0, win32con.GENERIC_ALL, sa)
        station.SetProcessWindowStation()
        try:
            desktop = win32service.CreateDesktop('solver', 0, win32con.GENERIC_ALL, sa)
        finally:
            previous.SetProcessWindowStation()
        _desktop_handles = station, desktop, name + '\\solver'
    return _desktop_handles[2]


def run(command, log, timeout=7200):
    env = os.environ.copy()
    env['PATH'] = str(ROOT / '.tools/oommf-runtime') + os.pathsep + str(TCL.parent) + os.pathsep + env['PATH']
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_ALL_ACCESS)
    admin = win32security.CreateWellKnownSid(win32security.WinBuiltinAdministratorsSid)
    restricted = win32security.CreateRestrictedToken(token, 1, [(admin, 0)], [], [])
    user = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    acl = win32security.ACL()
    acl.AddAccessAllowedAce(win32security.ACL_REVISION, win32con.GENERIC_ALL, user)
    win32security.SetTokenInformation(restricted, win32security.TokenDefaultDacl, acl)
    sa = pywintypes.SECURITY_ATTRIBUTES()
    sa.SECURITY_DESCRIPTOR.SetSecurityDescriptorDacl(True, acl, False)
    with Path(log).open('wb') as out, open(os.devnull, 'rb') as inp:
        hout, hin = msvcrt.get_osfhandle(out.fileno()), msvcrt.get_osfhandle(inp.fileno())
        os.set_handle_inheritable(hout, True)
        os.set_handle_inheritable(hin, True)
        si = win32process.STARTUPINFO()
        si.lpDesktop = private_desktop(token)
        si.dwFlags = win32con.STARTF_USESTDHANDLES | win32con.STARTF_USESHOWWINDOW
        si.wShowWindow = win32con.SW_HIDE
        si.hStdOutput = si.hStdError = hout
        si.hStdInput = hin
        start = time.monotonic()
        hp, ht, pid, tid = win32process.CreateProcessAsUser(
            restricted, None, subprocess.list2cmdline([str(x) for x in command]),
            sa, sa, True, win32con.CREATE_NO_WINDOW, env, str(ROOT), si)
        status = win32event.WaitForSingleObject(hp, int(timeout * 1000))
        if status == win32con.WAIT_TIMEOUT:
            subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            raise TimeoutError(f'Owned process {pid} exceeded {timeout}s; see {log}')
        code = win32process.GetExitCodeProcess(hp)
        for handle in (hp, ht, restricted, token):
            handle.Close()
    return dict(returncode=code, wall_seconds=time.monotonic()-start, pid=pid,
                command=[str(x) for x in command], restricted_admin_sid=True)


if __name__ == '__main__':
    print(run([TCL, OOMMF, '+version'], ROOT / '.tools/oommf-version.log', 30))
    print((ROOT / '.tools/oommf-version.log').read_text(errors='replace'))
