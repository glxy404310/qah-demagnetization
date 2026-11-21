"""Load the latest analysis code after the active computation worker exits."""
import argparse
import win32api
import win32con
import win32event

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--wait-pid',type=int,required=True)
    args=parser.parse_args()
    handle=win32api.OpenProcess(win32con.SYNCHRONIZE,False,args.wait_pid)
    win32event.WaitForSingleObject(handle,win32event.INFINITE)
    handle.Close()
    from report import build_report
    from progress import snapshot
    build_report()
    snapshot()
