import pygame
import math
import sys
import random
import json
import os

pygame.init()

info = pygame.display.Info()
SW = min(1600, info.current_w - 100)
SH = 140
COLS = SW // 16

BG = (5, 5, 10)
WALL_C = (180, 180, 200)
ENEMY_C = (255, 70, 70)
HP_C = (70, 255, 120)
MENU_C = (200, 200, 220)
SEL_C = (255, 220, 100)

SAVE_FILE = os.path.join(os.path.expanduser("~"), ".ascii_fps_save.json")

px = 1.5
py = 1.5
pa = 0.0
hp = 100
move_spd = 0.035
turn_spd = 0.003
mouse_sens = 1.0
FOV = math.pi / 3
PRAD = 0.25

MAP = []
MW = 0
MH = 0
ents = []
dbuf = []

state = 'menu'
menu_sel = 0
opt_sel = 0
can_continue = False
mouse_locked = False

ENEMY_CHAR = '웃'
HEALTH_CHAR = '+'

menu_buttons = []

def save_game():
    data = {}
    data['px'] = px
    data['py'] = py
    data['pa'] = pa
    data['hp'] = hp
    data['FOV'] = FOV
    data['mouse_sens'] = mouse_sens
    data['MAP'] = MAP
    data['MW'] = MW
    data['MH'] = MH
    data['ents'] = ents
    try:
        f = open(SAVE_FILE, 'w')
        json.dump(data, f)
        f.close()
        return True
    except:
        return False

def load_game():
    global px, py, pa, hp, FOV, MAP, MW, MH, ents, can_continue, mouse_sens
    try:
        f = open(SAVE_FILE, 'r')
        data = json.load(f)
        f.close()
        px = data['px']
        py = data['py']
        pa = data['pa']
        hp = data['hp']
        FOV = data.get('FOV', math.pi / 3)
        mouse_sens = data.get('mouse_sens', 1.0)
        MAP = data['MAP']
        MW = data['MW']
        MH = data['MH']
        ents = data['ents']
        can_continue = True
        return True
    except:
        return False

def gen_map(w, h):
    global MAP, MW, MH
    MW = w
    MH = h
    g = []
    for y in range(h):
        row = []
        for x in range(w):
            row.append('#')
        g.append(row)
    
    def carve(x, y):
        dirs = [(0,-2), (0,2), (-2,0), (2,0)]
        random.shuffle(dirs)
        for d in dirs:
            dx = d[0]
            dy = d[1]
            nx = x + dx
            ny = y + dy
            if nx >= 1 and nx < w-1 and ny >= 1 and ny < h-1:
                if g[ny][nx] == '#':
                    g[y + dy//2][x + dx//2] = '.'
                    g[ny][nx] = '.'
                    carve(nx, ny)
    
    g[1][1] = '.'
    carve(1, 1)
    
    for i in range(w * h // 8):
        x = random.randint(2, w-3)
        y = random.randint(2, h-3)
        if g[y][x] == '#':
            nb = 0
            if g[y-1][x] == '.': nb = nb + 1
            if g[y+1][x] == '.': nb = nb + 1
            if g[y][x-1] == '.': nb = nb + 1
            if g[y][x+1] == '.': nb = nb + 1
            if nb >= 2:
                g[y][x] = '.'
    
    MAP = []
    for row in g:
        MAP.append(''.join(row))

def spawn_ents(ne, nh):
    global ents
    ents = []
    empty = []
    for y in range(MH):
        for x in range(MW):
            if MAP[y][x] == '.':
                dist = (x - px) * (x - px) + (y - py) * (y - py)
                if dist > 9:
                    empty.append((x + 0.5, y + 0.5))
    random.shuffle(empty)
    
    for i in range(min(ne, len(empty))):
        e = {}
        e['type'] = 'enemy'
        e['x'] = empty[i][0]
        e['y'] = empty[i][1]
        e['alive'] = True
        ents.append(e)
    
    for i in range(ne, min(ne + nh, len(empty))):
        e = {}
        e['type'] = 'health'
        e['x'] = empty[i][0]
        e['y'] = empty[i][1]
        e['alive'] = True
        ents.append(e)

screen = pygame.display.set_mode((SW, SH), pygame.RESIZABLE)
pygame.display.set_caption("Dimension ONE")

fcache = {}
def gfont(sz):
    sz = int(sz)
    if sz < 8:
        sz = 8
    if sz > 200:
        sz = 200
    if sz not in fcache:
        fcache[sz] = pygame.font.SysFont("monospace", sz, bold=True)
    return fcache[sz]

def iswall(x, y):
    mx = int(x)
    my = int(y)
    if mx < 0 or mx >= MW or my < 0 or my >= MH:
        return True
    if MAP[my][mx] == '#':
        return True
    return False

def cast(ang):
    dx = math.cos(ang)
    dy = math.sin(ang)
    d = 0.0
    while d < 20.0:
        x = px + dx * d
        y = py + dy * d
        mx = int(x)
        my = int(y)
        if mx < 0 or mx >= MW or my < 0 or my >= MH:
            return d, '#'
        if MAP[my][mx] == '#':
            fx = x - mx
            fy = y - my
            if min(fx, 1-fx) < min(fy, 1-fy):
                return d, '█'
            else:
                return d, '▓'
        d = d + 0.02
    return 20.0, ' '

def cast_to_point(tx, ty):
    dx = tx - px
    dy = ty - py
    dist = math.sqrt(dx*dx + dy*dy)
    if dist < 0.01:
        return 0.0, False
    dx = dx / dist
    dy = dy / dist
    d = 0.0
    while d < dist - 0.1:
        x = px + dx * d
        y = py + dy * d
        mx = int(x)
        my = int(y)
        if mx < 0 or mx >= MW or my < 0 or my >= MH:
            return d, True
        if MAP[my][mx] == '#':
            return d, True
        d = d + 0.05
    return dist, False

def shade(d, c):
    s = 1.0 - d / 10.0
    if s < 0.15:
        s = 0.15
    r = int(c[0] * s)
    g = int(c[1] * s)
    b = int(c[2] * s)
    return (r, g, b)

def render():
    global dbuf
    screen.fill(BG)
    
    hud_cols = 12
    game_cols = COLS - hud_cols
    cw = SW / COLS
    cy = SH // 2
    
    dbuf = []
    for i in range(game_cols):
        dbuf.append(20.0)
    
    for col in range(game_cols):
        ang = pa - FOV/2 + (col / game_cols) * FOV
        d, ch = cast(ang)
        d = d * math.cos(ang - pa)
        if d < 0.1:
            d = 0.1
        dbuf[col] = d
        sz = 100 / d
        if sz < 8:
            sz = 8
        if sz > 100:
            sz = 100
        c = shade(d, WALL_C)
        if ch != ' ':
            f = gfont(sz)
            ts = f.render(ch, True, c)
            x = int(col * cw + cw/2 - ts.get_width()/2)
            screen.blit(ts, (x, cy - ts.get_height()//2))
    
    ent_render = []
    for e in ents:
        if e['alive'] == False:
            continue
        dx = e['x'] - px
        dy = e['y'] - py
        d = math.sqrt(dx*dx + dy*dy)
        _, blocked = cast_to_point(e['x'], e['y'])
        if blocked:
            continue
        diff = math.atan2(dy, dx) - pa
        while diff > math.pi:
            diff = diff - 2*math.pi
        while diff < -math.pi:
            diff = diff + 2*math.pi
        if abs(diff) < FOV/2:
            col = int(((diff + FOV/2) / FOV) * game_cols)
            if col >= 0 and col < game_cols:
                if d < dbuf[col]:
                    if e['type'] == 'enemy':
                        sz = 150 / d
                        if sz < 12:
                            sz = 12
                        if sz > 180:
                            sz = 180
                        ch = ENEMY_CHAR
                        c = shade(d, ENEMY_C)
                    else:
                        sz = 100 / d
                        if sz < 10:
                            sz = 10
                        if sz > 100:
                            sz = 100
                        ch = HEALTH_CHAR
                        c = shade(d, HP_C)
                    ent_render.append((d, col, ch, sz, c))
    
    ent_render.sort(key=lambda x: -x[0])
    
    crosshair_col = game_cols // 2
    
    for item in ent_render:
        d, col, ch, sz, c = item
        if col == crosshair_col:
            r = c[0] + 50
            g = c[1] + 50
            b = c[2] + 50
            if r > 255: r = 255
            if g > 255: g = 255
            if b > 255: b = 255
            c = (r, g, b)
        f = gfont(sz)
        ts = f.render(ch, True, c)
        x = int(col * cw + cw/2 - ts.get_width()/2)
        screen.blit(ts, (x, cy - ts.get_height()//2))
    
    hud_x = game_cols * cw + 10
    hf = gfont(28)
    
    if hp < 30:
        hp_c = (255, 80, 80)
    else:
        hp_c = (80, 255, 80)
    hp_s = hf.render(str(hp) + "%", True, hp_c)
    screen.blit(hp_s, (hud_x, cy - hp_s.get_height()//2))
    
    eleft = 0
    for e in ents:
        if e['type'] == 'enemy' and e['alive']:
            eleft = eleft + 1
    sf = gfont(22)
    es = sf.render("E:" + str(eleft), True, ENEMY_C)
    screen.blit(es, (hud_x + hp_s.get_width() + 15, cy - es.get_height()//2))
    
    gs = sf.render("♦", True, (200, 180, 100))
    screen.blit(gs, (hud_x + hp_s.get_width() + es.get_width() + 30, cy - gs.get_height()//2))
    
    pygame.display.flip()

def draw_menu(title, opts, sel):
    global menu_buttons
    screen.fill(BG)
    cy = SH // 2
    menu_buttons = []
    
    tf = gfont(32)
    ts = tf.render(title, True, SEL_C)
    screen.blit(ts, (20, cy - ts.get_height()//2))
    
    of = gfont(26)
    x = ts.get_width() + 50
    
    for i in range(len(opts)):
        opt = opts[i]
        if i == sel:
            c = SEL_C
            txt = "[" + opt + "]"
        else:
            c = MENU_C
            txt = opt
        os = of.render(txt, True, c)
        btn_rect = pygame.Rect(x, cy - os.get_height()//2, os.get_width(), os.get_height())
        menu_buttons.append((btn_rect, i))
        screen.blit(os, (x, cy - os.get_height()//2))
        x = x + os.get_width() + 25
    
    hf = gfont(14)
    hs = hf.render("◄ ► SPACE / CLICK", True, (80, 80, 100))
    screen.blit(hs, (SW - hs.get_width() - 10, cy - hs.get_height()//2))
    
    pygame.display.flip()

def draw_options():
    global menu_buttons
    screen.fill(BG)
    cy = SH // 2
    menu_buttons = []
    
    tf = gfont(28)
    ts = tf.render("OPTIONS", True, SEL_C)
    screen.blit(ts, (20, cy - ts.get_height()//2))
    
    of = gfont(22)
    fov_deg = int(FOV * 180 / math.pi)
    sens_pct = int(mouse_sens * 100)
    
    if opt_sel == 0:
        c1 = SEL_C
    else:
        c1 = MENU_C
    fs = of.render("FOV:<" + str(fov_deg) + ">", True, c1)
    fov_rect = pygame.Rect(ts.get_width() + 40, cy - fs.get_height()//2, fs.get_width(), fs.get_height())
    menu_buttons.append((fov_rect, 0))
    screen.blit(fs, (ts.get_width() + 40, cy - fs.get_height()//2))
    
    if opt_sel == 1:
        c2 = SEL_C
    else:
        c2 = MENU_C
    ss = of.render("SENS:<" + str(sens_pct) + "%>", True, c2)
    sens_rect = pygame.Rect(ts.get_width() + 40 + fs.get_width() + 20, cy - ss.get_height()//2, ss.get_width(), ss.get_height())
    menu_buttons.append((sens_rect, 1))
    screen.blit(ss, (ts.get_width() + 40 + fs.get_width() + 20, cy - ss.get_height()//2))
    
    if opt_sel == 2:
        c3 = SEL_C
        btxt = "[Back]"
    else:
        c3 = MENU_C
        btxt = "Back"
    bs = of.render(btxt, True, c3)
    back_rect = pygame.Rect(ts.get_width() + 40 + fs.get_width() + 20 + ss.get_width() + 20, cy - bs.get_height()//2, bs.get_width(), bs.get_height())
    menu_buttons.append((back_rect, 2))
    screen.blit(bs, (ts.get_width() + 40 + fs.get_width() + 20 + ss.get_width() + 20, cy - bs.get_height()//2))
    
    hf = gfont(14)
    hs = hf.render("▲▼ SELECT  ◄► ADJUST  SPACE/CLICK OK", True, (80, 80, 100))
    screen.blit(hs, (SW - hs.get_width() - 10, cy - hs.get_height()//2))
    
    pygame.display.flip()

def draw_about():
    screen.fill(BG)
    cy = SH // 2
    tf = gfont(24)
    ts = tf.render("ABOUT", True, SEL_C)
    screen.blit(ts, (20, cy - ts.get_height()//2))
    of = gfont(18)
    txt = "Based on squidi.net  |  WASD move  |  Mouse look  |  Click shoot  |  One-line ASCII raycaster"
    os = of.render(txt, True, MENU_C)
    screen.blit(os, (ts.get_width() + 30, cy - os.get_height()//2))
    pygame.display.flip()

def check_enemy_collision(x, y):
    for e in ents:
        if e['type'] == 'enemy' and e['alive']:
            dx = e['x'] - x
            dy = e['y'] - y
            d = math.sqrt(dx*dx + dy*dy)
            if d < 0.4:
                return True
    return False

def collides(x, y):
    for ox in [-PRAD, 0, PRAD]:
        for oy in [-PRAD, 0, PRAD]:
            if iswall(x + ox, y + oy):
                return True
    return False

def move(dx, dy):
    global px, py, hp
    nx = px + dx
    ny = py + dy
    
    if not collides(nx, ny) and not check_enemy_collision(nx, ny):
        px = nx
        py = ny
    elif not collides(nx, py) and not check_enemy_collision(nx, py):
        px = nx
    elif not collides(px, ny) and not check_enemy_collision(px, ny):
        py = ny
    
    for e in ents:
        if e['alive'] and e['type'] == 'health':
            dx = e['x'] - px
            dy = e['y'] - py
            d = math.sqrt(dx*dx + dy*dy)
            if d < 0.5:
                hp = hp + 25
                if hp > 100:
                    hp = 100
                e['alive'] = False

def shoot():
    for e in ents:
        if e['type'] != 'enemy':
            continue
        if e['alive'] == False:
            continue
        dx = e['x'] - px
        dy = e['y'] - py
        d = math.sqrt(dx*dx + dy*dy)
        diff = math.atan2(dy, dx) - pa
        while diff > math.pi:
            diff = diff - 2*math.pi
        while diff < -math.pi:
            diff = diff + 2*math.pi
        if abs(diff) < 0.15 and d < 8:
            _, blocked = cast_to_point(e['x'], e['y'])
            if not blocked:
                e['alive'] = False
                return True
    return False

def update_enemies():
    global hp
    for e in ents:
        if e['type'] != 'enemy':
            continue
        if e['alive'] == False:
            continue
        dx = px - e['x']
        dy = py - e['y']
        d = math.sqrt(dx*dx + dy*dy)
        if d < 0.6:
            hp = hp - 1
        elif d < 10:
            nx = e['x'] + (dx/d) * 0.012
            ny = e['y'] + (dy/d) * 0.012
            if iswall(nx, ny) == False:
                e['x'] = nx
                e['y'] = ny

def new_game():
    global px, py, pa, hp, can_continue
    gen_map(24, 24)
    spawn_ents(8, 5)
    px = 1.5
    py = 1.5
    pa = 0.0
    hp = 100
    can_continue = True
    save_game()

def check_menu_click(pos):
    for btn in menu_buttons:
        rect = btn[0]
        idx = btn[1]
        if rect.collidepoint(pos):
            return idx
    return -1

def main():
    global state, menu_sel, opt_sel, pa, hp, px, py, can_continue, SW, COLS, screen, SH, FOV, mouse_locked, mouse_sens
    
    load_game()
    
    clock = pygame.time.Clock()
    running = True
    main_opts = ["New", "Continue", "Options", "About", "Quit"]
    pause_opts = ["Resume", "Save", "Options", "Quit"]
    
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            
            elif ev.type == pygame.VIDEORESIZE:
                SW = ev.w
                if SW < 400:
                    SW = 400
                SH = 140
                COLS = SW // 16
                screen = pygame.display.set_mode((SW, SH), pygame.RESIZABLE)
            
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if state == 'game':
                    if ev.button == 1:
                        if mouse_locked:
                            shoot()
                        else:
                            pygame.mouse.set_visible(False)
                            pygame.event.set_grab(True)
                            mouse_locked = True
                
                elif state == 'menu':
                    clicked = check_menu_click(ev.pos)
                    if clicked >= 0:
                        menu_sel = clicked
                        opt = main_opts[menu_sel]
                        if opt == "New":
                            new_game()
                            state = 'game'
                        elif opt == "Continue" and can_continue:
                            state = 'game'
                        elif opt == "Options":
                            state = 'options'
                            opt_sel = 0
                        elif opt == "About":
                            state = 'about'
                        elif opt == "Quit":
                            running = False
                
                elif state == 'pause':
                    clicked = check_menu_click(ev.pos)
                    if clicked >= 0:
                        menu_sel = clicked
                        opt = pause_opts[menu_sel]
                        if opt == "Resume":
                            state = 'game'
                        elif opt == "Save":
                            save_game()
                        elif opt == "Options":
                            state = 'options'
                            opt_sel = 0
                        elif opt == "Quit":
                            state = 'menu'
                            menu_sel = 0
                
                elif state == 'options':
                    clicked = check_menu_click(ev.pos)
                    if clicked >= 0:
                        opt_sel = clicked
                        if opt_sel == 2:
                            save_game()
                            if can_continue:
                                state = 'pause'
                            else:
                                state = 'menu'
                
                elif state == 'about':
                    state = 'menu'
            
            elif ev.type == pygame.MOUSEMOTION:
                if state == 'game' and mouse_locked:
                    mx = ev.rel[0]
                    pa = pa + mx * turn_spd * mouse_sens
            
            elif ev.type == pygame.KEYDOWN:
                if state == 'menu':
                    if ev.key == pygame.K_LEFT:
                        menu_sel = (menu_sel - 1) % len(main_opts)
                    elif ev.key == pygame.K_RIGHT:
                        menu_sel = (menu_sel + 1) % len(main_opts)
                    elif ev.key == pygame.K_SPACE or ev.key == pygame.K_RETURN:
                        opt = main_opts[menu_sel]
                        if opt == "New":
                            new_game()
                            state = 'game'
                        elif opt == "Continue" and can_continue:
                            state = 'game'
                        elif opt == "Options":
                            state = 'options'
                            opt_sel = 0
                        elif opt == "About":
                            state = 'about'
                        elif opt == "Quit":
                            running = False
                
                elif state == 'pause':
                    if ev.key == pygame.K_LEFT:
                        menu_sel = (menu_sel - 1) % len(pause_opts)
                    elif ev.key == pygame.K_RIGHT:
                        menu_sel = (menu_sel + 1) % len(pause_opts)
                    elif ev.key == pygame.K_SPACE or ev.key == pygame.K_RETURN:
                        opt = pause_opts[menu_sel]
                        if opt == "Resume":
                            state = 'game'
                        elif opt == "Save":
                            save_game()
                        elif opt == "Options":
                            state = 'options'
                            opt_sel = 0
                        elif opt == "Quit":
                            state = 'menu'
                            menu_sel = 0
                    elif ev.key == pygame.K_ESCAPE:
                        state = 'game'
                
                elif state == 'options':
                    if ev.key == pygame.K_UP or ev.key == pygame.K_DOWN:
                        if ev.key == pygame.K_UP:
                            opt_sel = (opt_sel - 1) % 3
                        else:
                            opt_sel = (opt_sel + 1) % 3
                    elif ev.key == pygame.K_LEFT and opt_sel == 0:
                        FOV = FOV - math.pi/36
                        if FOV < math.pi/36:
                            FOV = math.pi/36
                    elif ev.key == pygame.K_RIGHT and opt_sel == 0:
                        FOV = FOV + math.pi/36
                    elif ev.key == pygame.K_LEFT and opt_sel == 1:
                        mouse_sens = mouse_sens - 0.1
                        if mouse_sens < 0.1:
                            mouse_sens = 0.1
                    elif ev.key == pygame.K_RIGHT and opt_sel == 1:
                        mouse_sens = mouse_sens + 0.1
                        if mouse_sens > 3.0:
                            mouse_sens = 3.0
                    elif ev.key == pygame.K_SPACE or ev.key == pygame.K_RETURN:
                        if opt_sel == 2:
                            save_game()
                            if can_continue:
                                state = 'pause'
                            else:
                                state = 'menu'
                    elif ev.key == pygame.K_ESCAPE:
                        save_game()
                        if can_continue:
                            state = 'pause'
                        else:
                            state = 'menu'
                
                elif state == 'about':
                    if ev.key == pygame.K_SPACE or ev.key == pygame.K_ESCAPE:
                        state = 'menu'
                
                elif state == 'game':
                    if ev.key == pygame.K_ESCAPE:
                        state = 'pause'
                        menu_sel = 0
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                        mouse_locked = False
                    elif ev.key == pygame.K_r:
                        gen_map(24, 24)
                        spawn_ents(8, 5)
                        px = 1.5
                        py = 1.5
                        hp = 100
        
        if state == 'game':
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]:
                move(math.cos(pa) * move_spd, math.sin(pa) * move_spd)
            if keys[pygame.K_s]:
                move(-math.cos(pa) * move_spd, -math.sin(pa) * move_spd)
            if keys[pygame.K_a]:
                move(math.cos(pa - math.pi/2) * move_spd, math.sin(pa - math.pi/2) * move_spd)
            if keys[pygame.K_d]:
                move(math.cos(pa + math.pi/2) * move_spd, math.sin(pa + math.pi/2) * move_spd)
            
            update_enemies()
            
            if hp <= 0:
                gen_map(24, 24)
                spawn_ents(8, 5)
                px = 1.5
                py = 1.5
                hp = 100
            
            eleft = 0
            for e in ents:
                if e['type'] == 'enemy' and e['alive']:
                    eleft = eleft + 1
            if eleft == 0:
                gen_map(24, 24)
                spawn_ents(10, 5)
                px = 1.5
                py = 1.5
            
            render()
        
        elif state == 'menu':
            if can_continue:
                opts = main_opts
            else:
                opts = ["New", "(Continue)", "Options", "About", "Quit"]
            draw_menu("Dimension ONE", opts, menu_sel)
        
        elif state == 'pause':
            draw_menu("PAUSED", pause_opts, menu_sel)
        
        elif state == 'options':
            draw_options()
        
        elif state == 'about':
            draw_about()
        
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":

    main()

