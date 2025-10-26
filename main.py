# ASCII Oscilloscope with persistent trace + Y scale (RP2350 / MicroPython)
# - History buffer across the screen width -> true scrolling trace
# - Y-axis labels (5.0V, 2.5V, 0.0V)
# - Use ADC0 (GP26) or simulated signal
# Date 26-10-2025
# Version DEMO-1.0.0
# Open with a terminal (PuTTY/TeraTerm) at 115200 baud.

import sys, math, time
from machine import ADC

# -------- Settings --------
USE_ADC        = False     # True = read ADC0 (GP26), False = simulated signal
W, H           = 64, 20    # plot area width/height (characters)
LEFT_MARGIN    = 7         # room for Y-axis labels & bar
FPS            = 25        # frame rate target (lower if flicker)
DRAW_GRID      = True
DISABLE_REPL   = False     # True to detach REPL for a clean output

# Voltage scaling
VREF_DISPLAY   = 5.0       # Y-axis scale 0..5V (what we show on the left)
ADC_VREF       = 3.3       # electrical ADC reference (3.3V typical Pico/RP2350)

# -------- ADC init (optional) --------
adc = None
if USE_ADC:
    try:
        adc = ADC(26)      # GP26 = ADC0
    except:
        adc = None
        USE_ADC = False

# -------- ANSI helpers --------
def clear_screen(): sys.stdout.write("\x1b[2J")
def home_cursor():  sys.stdout.write("\x1b[H")

# -------- Signal read -> voltage (0..VREF_DISPLAY) --------
def read_voltage(t):
    if USE_ADC and adc is not None:
        v = adc.read_u16() / 65535.0 * ADC_VREF  # 0..3.3V typically
        # map actual 0..ADC_VREF into 0..VREF_DISPLAY
        v = (v / ADC_VREF) * VREF_DISPLAY
        if v < 0: v = 0.0
        if v > VREF_DISPLAY: v = VREF_DISPLAY
        return v
    # Simulated: nice-looking composite wave spanning ~15%..85% of VREF_DISPLAY
    mid = 0.5 * VREF_DISPLAY
    amp = 0.35 * VREF_DISPLAY
    v = mid + amp * math.sin(t*2.0) + 0.15*VREF_DISPLAY*math.sin(t*0.17+1.2)
    return max(0.0, min(VREF_DISPLAY, v))

# -------- Map voltage -> row index (0 = top, H-1 = bottom) --------
def v_to_row(v):
    # v: 0..VREF_DISPLAY  -> y: 0..H-1 (0 top)
    frac = 1.0 - (v / VREF_DISPLAY)          # invert for screen coordinates
    y = int(round(frac * (H-1)))
    if y < 0: y = 0
    if y > H-1: y = H-1
    return y

# -------- Frame renderer with history (persistent trace) --------
def draw_frame(y_history):
    home_cursor()
    lines = []

    # prebuild empty canvas
    for r in range(H):
        line = [' '] * (LEFT_MARGIN + W)

        # Y-axis labels & bar at LEFT_MARGIN-1
        bar_x = LEFT_MARGIN - 1
        if r == 0:
            lab = f"{VREF_DISPLAY:>4.1f}|"  # top label
            line[0:len(lab)] = list(lab)
        elif r == H//2:
            lab = f"{(VREF_DISPLAY/2):>4.1f}|"
            line[0:len(lab)] = list(lab)
        elif r == H-1:
            lab = f"{0.0:>4.1f}|"
            line[0:len(lab)] = list(lab)
        else:
            # vertical bar only
            if 0 <= bar_x < LEFT_MARGIN + W:
                line[bar_x] = '|'

        # grid lines in plot area
        if DRAW_GRID:
            if r == 0 or r == H-1:
                for c in range(LEFT_MARGIN, LEFT_MARGIN + W):
                    line[c] = '-'
            if r == H//2:
                for c in range(LEFT_MARGIN, LEFT_MARGIN + W):
                    # avoid overriding the axis bar
                    if line[c] == ' ':
                        line[c] = '.'

        lines.append(line)

    # plot the persistent trace from history
    # y_history has length W (left oldest -> right newest)
    prev_y = None
    for i, y in enumerate(y_history):
        x = LEFT_MARGIN + i
        if 0 <= y < H:
            lines[y][x] = '*'
            # draw a simple connector to previous point
            if prev_y is not None and x-1 >= LEFT_MARGIN:
                dy = y - prev_y
                step = 1 if dy > 0 else -1
                for yy in range(prev_y, y, step):
                    lines[yy][x-1] = '*'
        prev_y = y

    # dump to terminal
    out = "\n".join("".join(row) for row in lines) + "\n"
    sys.stdout.write(out)

# -------- Main loop --------
def main():
    if DISABLE_REPL:
        try:
            import uos
            uos.dupterm(None, 1)
        except:
            pass

    clear_screen(); home_cursor()
    mode = "ADC0 GP26" if USE_ADC else "SIM"
    sys.stdout.write(f"ASCII OSC | Mode: {mode} | Scale: 0..{VREF_DISPLAY:.1f}V | W={W} H={H} FPS={FPS}\n")
    time.sleep(0.2)

    # history buffer
    y_hist = [H//2] * W

    t = 0.0
    dt = 1.0 / FPS
    while True:
        v  = read_voltage(t)
        y  = v_to_row(v)
        # shift left and append newest on the right
        y_hist.pop(0)
        y_hist.append(y)

        draw_frame(y_hist)
        t += 0.12
        time.sleep(dt)

try:
    main()
except KeyboardInterrupt:
    pass
