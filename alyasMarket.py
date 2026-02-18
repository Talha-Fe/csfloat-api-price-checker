import os
import sys
import json
import time
import math
import requests
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv

try:
    import msvcrt
except:
    msvcrt = None

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
ENV_PATH = os.path.join(BASE_DIR, ".env")

if not os.path.exists(ENV_PATH):
    print("\n.can't find .env")
    api_input = input("Please ENTER CSFloat API key: ").strip()

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(f"CSFLOAT_API_KEY={api_input}")

    print(".env created.\n")

load_dotenv(ENV_PATH)


API_KEY = os.environ.get("CSFLOAT_API_KEY","").strip()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
API_URL = "https://csfloat.com/api/v1/listings"

EVENT_HISTORY = []

BANNER_RAW = r"""
          (     (              
          )\    )\(       )    
       ((((_)( ((_)\ ) ( /( (  
        )\ _ )\ _(()/( )(_)))\ 
        (_)_\(_) |)(_)|(_)_((_)
         / _ \ | | || / _` (_-<
        /_/ \_\|_|\_, \__,_/__/
                  |__/         

      ★ CSFLOAT API PRICE CHECKER ★
        M = MENU    |    Q = QUIT
============================================================
"""

def enable_ansi_on_windows():
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return

        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass

def rgb(r, g, b):
    return f"\x1b[38;2;{r};{g};{b}m"

def reset():
    return "\x1b[0m"

def hsv_to_rgb(h, s, v):
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)

def gradient_text_wave(text: str, phase: float):
    lines = text.splitlines(True) 
    widths = [len(l.rstrip("\n")) for l in lines if l.strip("\n") != ""]
    max_w = max(widths) if widths else 1

    out = []
    for y, line in enumerate(lines):
        if line == "\n":
            out.append("\n")
            continue

        raw = line.rstrip("\n")
        newline = "\n" if line.endswith("\n") else ""

        for x, ch in enumerate(raw):
            if ch == " ":
                out.append(" ")
                continue
            base = x / max_w
            wave = 0.07 * math.sin((x * 0.35) + (y * 0.9) + phase) 
            hue = (base + wave + phase * 0.03) % 1.0

            r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
            out.append(rgb(r, g, b) + ch)

        out.append(reset() + newline)

    return "".join(out)

def banner():
    phase = time.time()
    return gradient_text_wave(BANNER_RAW, phase)

enable_ansi_on_windows()

def now():
    return datetime.now().strftime("%H:%M:%S")

def log_event(msg):
    EVENT_HISTORY.append(f"[{now()}] {msg}")

def clear():
    os.system("cls" if os.name=="nt" else "clear")

def extract_listings(payload):
    if isinstance(payload,dict):
        if isinstance(payload.get("data"),list):
            return payload["data"]
        for v in payload.values():
            if isinstance(v,list):
                return v
    if isinstance(payload,list):
        return payload
    return []

def fetch_lowest_buy_now(item):

    headers={"Authorization":API_KEY}
    params={
        "market_hash_name":item,
        "sort_by":"lowest_price",
        "limit":50,
        "type":"buy_now"
    }

    r=requests.get(API_URL,headers=headers,params=params,timeout=20)

    if r.status_code!=200:
        return None,None,"HTTP"

    listings=extract_listings(r.json())

    buy_now=[
        l for l in listings
        if isinstance(l,dict)
        and l.get("type")=="buy_now"
        and isinstance(l.get("price"),int)
    ]

    if not buy_now:
        return None,None,"NO_BUY_NOW"

    best=min(buy_now,key=lambda x:x["price"])
    return best["price"]/100.0,best.get("id"),None

def read_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE,"r",encoding="utf-8") as f:
        return json.load(f)

def write_config(cfg):
    with open(CONFIG_FILE,"w",encoding="utf-8") as f:
        json.dump(cfg,f,indent=2)

def setup():
    clear()
    print(banner())
    print("First setup starting\n")

    interval=input("Delay Time [30]: ").strip()
    interval=int(interval) if interval.isdigit() else 30

    items=[]
    while True:
        n=input("Item name (ENTER Closes): ").strip()
        if not n: break
        t=float(input("Target USD: "))
        items.append({"market_hash_name":n,"target_usd":t})

    if not items:
        items=[{"market_hash_name":"AK-47 | Redline (Field-Tested)","target_usd":40}]

    cfg={"intervalSeconds":interval,"items":items}
    write_config(cfg)
    return cfg

def menu(cfg):
    while True:
        clear()
        print(banner())
        print("=== ALYAS ===")
        print("1) Current Items")
        print("2) Add Items")
        print("3) Delete Items")
        print("4) Change Delay")
        print("5) Save and Continue")
        print("Q) Quit")

        c=input("> ").lower()

        if c=="1":
            for i,it in enumerate(cfg["items"],1):
                print(i,it)
            input("Press ENTER to close... ^^")

        elif c=="2":
            n=input("Name: ")
            t=float(input("Target: "))
            cfg["items"].append({"market_hash_name":n,"target_usd":t})

        elif c=="3":
            i=int(input("No: "))-1
            cfg["items"].pop(i)

        elif c=="4":
            cfg["intervalSeconds"]=int(input("New Delay (in seconds): "))

        elif c=="5":
            write_config(cfg)
            return

        elif c=="q":
            exit()

def keypress():
    if not msvcrt:
        return None
    if msvcrt.kbhit():
        return msvcrt.getwch().lower()
    return None

def print_ui(rows,interval):

    clear()
    print(banner())
    print(f"Delay: {interval}s\n")

    print("{:<45}{:<10}{:<10}{:<10}".format("ITEM","LOWEST","TARGET","STATUS"))
    print("-"*80)

    for r in rows:
        print("{:<45}{:<10}{:<10}{:<10}".format(*r))

    if EVENT_HISTORY:
        print("\n========= EVENT HISTORY =========")
        for e in EVENT_HISTORY[-50:]:
            print(e)

def main():

    if not API_KEY:
        print("Missing API key...")
        input()
        return

    cfg=read_config() or setup()
    last_prices={}

    while True:

        k=keypress()
        if k=="m":
            menu(cfg)
        if k=="q":
            return

        interval=max(5,int(cfg.get("intervalSeconds",30)))
        rows=[]

        for it in cfg["items"]:

            name=it["market_hash_name"]
            target=float(it["target_usd"])

            log_event(f"Checking: {name}")

            price,lid,err=fetch_lowest_buy_now(name)

            if err:
                rows.append((name,"-","-","no_list"))
                continue

            prev=last_prices.get(name)
            changed=prev!=price if prev else False
            hit=price<=target

            status="ok"
            if hit: status="TARGET!"
            elif changed: status="changed"

            rows.append((name,f"{price:.2f}",f"{target:.2f}",status))

            if hit:
                log_event(f"TARGET FOUND {name} {price:.2f}")
                log_event(f"https://csfloat.com/item/{lid}")
            elif changed:
                log_event(f"{name} changed {prev}->{price}")

            last_prices[name]=price

        print_ui(rows,interval)

        end=time.time()+interval
        while time.time()<end:
            k=keypress()
            if k=="m":
                menu(cfg)
                break
            if k=="q":
                return
            time.sleep(0.1)

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print("CRASH:",e)
        input()


