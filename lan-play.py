#!/usr/bin/env python

import sys, os
import re
import signal
import subprocess
import curses
import threading
import json
if sys.platform == "win32":
    import shutil
from curses import wrapper

lan_play_path = ""
pmtu = ""
relay = ""
lan_pid = 4194305

def statusbar(stdscr):
    height, width = stdscr.getmaxyx()
    stdscr.attron(curses.color_pair(1))
    statusbarstr = "Press 'q' to exit"
    stdscr.addstr(0, 0, statusbarstr)
    stdscr.addstr(0, len(statusbarstr), " " * (width - len(statusbarstr) - 1))
    stdscr.attroff(curses.color_pair(1))
    
def welcome_scr(stdscr):
    curses.curs_set(False)
    stdscr.addstr(1, 0, "1 - Launch latest config")
    stdscr.addstr(2, 0, "2 - Edit config")
    stdscr.addstr(3, 0, "3 - Browse servers")
    k = stdscr.getch()
    if(k == ord('2') or k == ord('3') or k==ord('q')):
        return k
    elif(k == ord('1')):
        get_last_serv("servers.json")
        return k
    else:
        return ord('0')

def config_scr(stdscr):
    global pmtu
    global relay
    curses.curs_set(True)
    curses.echo()
    stdscr.addstr(0, 0, "MTU (leave blank for default and set to 500 for AC:NH)\n\r")
    stdscr.addstr(">>> ")
    s = stdscr.getstr()
    if s == "": s = "500"
    pmtu = s.decode('UTF-8')
    stdscr.addstr("IP addr (paste with CRTL + SHIFT + V)\n\r")
    stdscr.addstr(">>> ")
    relay = ""
    while True:
        relay = stdscr.getstr().decode('UTF-8')
        if (relay != ""):
            break
        stdscr.addstr("Please enter an address\n\r")
        stdscr.addstr(">>> ")

    curses.noecho()
    curses.curs_set(False)
    return ord('1')

def split_chunks(l, n):
    n = max(1, n)
    return (l[i:i+n] for i in range(0, len(l), n))


def get_servers(path):
    with open(path) as json_file:
        json_data = json.load(json_file)["servers"]

    servers = [(d.get("name", d.get("relay")), d.get("relay"), d.get("pmtu", "")) for d in json_data]
    return servers

def get_last_serv(path):
    global pmtu
    global relay
    with open(path, 'r') as json_file:
        json_data = json.load(json_file)["last"]
    pmtu = json_data.get("pmtu", "500")
    relay = json_data.get("relay", "could_not_find_latest_relay")

def set_last_serv(path):
    global pmtu
    global relay
    with open(path, 'r') as json_file:
        json_data = json.load(json_file)
    json_data["last"]["pmtu"] = pmtu
    json_data["last"]["relay"] = relay
    with open(path, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)


def select_scr(stdscr):
    global pmtu
    global relay
    
    serv_list = get_servers("servers.json")

    #TODO : DICT
    k = -1
    cursor_pos = 2
    current_page = 0

    height, width = stdscr.getmaxyx()
    elements = height - 2
    pages = len(serv_list) // elements

    while(k!=10):
        stdscr.clear()

        height, width = stdscr.getmaxyx()
        elements = height - 2
        pages = len(serv_list) // elements
        page_list = list(split_chunks(serv_list, elements))[current_page]
        n = len(page_list)
        
        statusbar(stdscr)
        stdscr.addstr(1, 0, "Navigate with the arrow keys and confirm with ENTER " + str(current_page+1) +"/" + str(pages+1))

        
        for i in range(n):
            stdscr.addstr(i+2, 2, page_list[i][0])
        stdscr.addstr(cursor_pos, 0, ">")
        k = stdscr.getch()
        if(k == curses.KEY_UP and cursor_pos > 2): cursor_pos -=1
        if(k == curses.KEY_DOWN and cursor_pos < height-1 and cursor_pos < n+1): 
            cursor_pos +=1
        if(k == curses.KEY_LEFT and current_page > 0): current_page -=1
        if(k == curses.KEY_RIGHT and current_page < pages): current_page +=1
        if(k == ord('q')): return k

    res = current_page * elements + cursor_pos - 2
    relay = serv_list[res][1]
    mtu = serv_list[res][2]

    return ord('1')

def kill_process(stdscr, pid, ch):
    if stdscr.getch() == ch:
        os.kill(pid, signal.SIGTERM)


def process_scr(stdscr):
    global pmtu
    global relay
    global lan_pid
    global lan_play_path

    set_last_serv("./servers.json")

    if (pmtu == ""): cmd = lan_play_path + " --relay-server-addr " + relay
    else: cmd = lan_play_path + " --pmtu " + pmtu + " --relay-server-addr " + relay
    #cmd = "./test.sh"
    stdscr.addstr(1, 0, "Launching lan-play", curses.A_BOLD)
    stdscr.addstr(3, 0, "")

    proc = subprocess.Popen([cmd], shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    lan_pid = proc.pid
    print("\n\r")
    t = threading.Thread(target=kill_process, args=(stdscr, lan_pid, ord('q'),))
    t.start()
    
    while proc.poll() is None:
        #stdscr.addstr(str(proc.stdout.readline().decode('utf-8').rstrip().lstrip()) + "\r")
        print(str(proc.stderr.readline().decode('utf-8').rstrip().lstrip()) + "\r")

    print("Exited with return code " + str(proc.returncode) + "\r")
    print("Press any key to continue\r")
    stdscr.getch()


    return ord('4')


def draw_menu(stdscr):

    cursor_x = 0
    cursor_y = 0
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

    next_scr = ord('0')
    screens = {
        ord('q'): "finish",
        ord('0'): welcome_scr,
        ord('1'): process_scr,
        ord('2'): config_scr,
        ord('3'): select_scr,
        ord('4'): welcome_scr
    }


    stdscr.clear()
    stdscr.refresh()

    while (next_scr!=ord('q')):
        stdscr.clear()

        statusbar(stdscr)
        next_scr = screens[next_scr](stdscr)


def main():
    global lan_play_path
    if sys.platform == "linux" or sys.platform == "linux2":
        if os.path.isfile("lan-play-linux"):
            lan_play_path = "./lan-play-linux"
        else:
            sys.exit("[ERR] Make sure the lan-play-linux binary is in the same directory!")
    elif sys.platform == "win32":
        if shutil.which("lan-play-win64.exe"): lan_play_path = "lan-play-win64.exe"
        elif shutil.which("lan-play-win32.exe"): lan_play_path = "lan-play-win32.exe"
    curses.wrapper(draw_menu)

if __name__ == "__main__":
    main()