import time, sys

def read_build_log(path):
    try:
        with open(path, 'rb') as f:
            raw = f.read()
        text = raw.decode('utf-8', errors='replace')
        lines = text.split('\n')
        return lines
    except FileNotFoundError:
        return None

def show_tail(path, n=15):
    lines = read_build_log(path)
    if lines is None:
        print('File not found:', path)
        return
    print(f'Lines: {len(lines)}')
    print(f'=== LAST {n} LINES ===')
    for l in lines[-n:]:
        s = l.strip()
        if s:
            print(s[:300])

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'build_fresh.txt'
    wait = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if wait > 0:
        time.sleep(wait)
    show_tail(path)