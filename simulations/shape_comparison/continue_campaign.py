"""Durable local continuation after an already running primary batch exits."""
import argparse
import os
import traceback
import win32api
import win32con
import win32event
from simulate import BASE, dump, analyze_case

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--wait-pid',type=int)
    args=parser.parse_args()
    dump(BASE/'controller.json',dict(pid=os.getpid(),wait_pid=args.wait_pid,phase='waiting' if args.wait_pid else 'starting'))
    if args.wait_pid:
        try:
            handle=win32api.OpenProcess(win32con.SYNCHRONIZE,False,args.wait_pid)
        except Exception:
            handle=None
        if handle:
            win32event.WaitForSingleObject(handle,win32event.INFINITE)
            handle.Close()
    try:
        # Import execution code only after the previous worker has exited.
        from run_campaign import campaign, status
        dump(BASE/'controller.json',dict(pid=os.getpid(),phase='running'))
        for path in sorted((BASE/'runs').glob('*/summary.json')):
            if (path.parent/'input.mif').exists():
                analyze_case(path.parent)
        campaign('all')
        dump(BASE/'controller.json',dict(pid=os.getpid(),phase='finished'))
    except Exception as error:
        status('FAILED',error=str(error),traceback=traceback.format_exc())
        dump(BASE/'controller.json',dict(pid=os.getpid(),phase='failed',error=str(error)))
        raise
