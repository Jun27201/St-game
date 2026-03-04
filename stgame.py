import pygame
import math
import random
import asyncio
import sys  
import os
import json

# --- 1. 設定・定数 ---
WIDTH, HEIGHT = 600, 800
FPS = 60
WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
RED    = (255, 0, 0)
ORANGE = (255, 165, 0)
YELLOW = (255, 255, 0)
GREEN  = (0, 255, 0)
LIME   = (0, 255, 0)    # GREENと同じですが、より鮮やかな指定に使われます
BLUE   = (0, 0, 255)
CYAN   = (0, 255, 255)  # 水色（氷や光の演出に便利）
PURPLE = (128, 0, 128)
GOLD   = (255, 215, 0)
KOZUE  = (104, 190, 141)
RAINBOW_COLORS = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0), 
    (0, 255, 0), (0, 255, 255), (0, 0, 255), (128, 0, 128)
]
BG_COLOR_SPELL = (20, 20, 30)

current_boss_index = 0


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Touhou Style: Bomb Item Drop")
clock = pygame.time.Clock()

SAVE_FILE = "ranking.json"

def load_ranking():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # "ranking" キーの中身を返す。なければ空リスト
                return data.get("ranking", [])
        except Exception:
            return []
    return []

def save_ranking(ranking):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({"ranking": ranking}, f, ensure_ascii=False)
    except: pass

def update_ranking(ranking, score, name):
    ranking.append({"name": name, "score": score})
    # スコアの高い順にソートして上位5位を抽出
    ranking.sort(key=lambda x: x["score"], reverse=True)
    return ranking[:5]

def reset_ranking():
    """ランキングデータを完全に消去する"""
    if os.path.exists(SAVE_FILE):
        try:
            # 空のデータを書き込んで初期化
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump({"ranking": []}, f)
            return [] # 空のリストを返す
        except: pass
    return []


async def name_entry_screen(score):
    user_name = ""
    f_entry = pygame.font.SysFont("arial", 40, bold=True)
    entering = True
    
    while entering:
        screen.fill((20, 20, 40))
        # 描画処理
        txt1 = f_entry.render("NEW RANKING IN!", True, (255, 215, 0))
        txt2 = f_entry.render(f"SCORE: {score}", True, WHITE)
        txt3 = f_entry.render(f"NAME: {user_name}_", True, (0, 255, 255))
        screen.blit(txt1, (WIDTH//2 - txt1.get_width()//2, 200))
        screen.blit(txt2, (WIDTH//2 - txt2.get_width()//2, 280))
        screen.blit(txt3, (WIDTH//2 - txt3.get_width()//2, 400))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "Guest"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and user_name != "": entering = False
                elif event.key == pygame.K_BACKSPACE: user_name = user_name[:-1]
                elif len(user_name) < 8 and event.unicode.isalnum(): user_name += event.unicode
        
        pygame.display.flip()
        await asyncio.sleep(0)
    return user_name

# --- 2. アセットロード ---
def load_asset(path, size, fallback_color):
    try:
        # --- [2026-02-13] 修正: パス解決ロジックの追加 ---
        # 実行時か開発時かを判定してベースパスを取得
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
            
        # imagesフォルダを含めたフルパスを生成
        full_path = os.path.join(base_path, "images", path)
        # ---------------------------------------------

        img = pygame.image.load(full_path).convert_alpha()
        
        # --- アスペクト比維持の計算 (既存のまま) ---
        rect = img.get_rect()
        aspect_ratio = rect.width / rect.height
        
        if rect.width > rect.height:
            new_w = size
            new_h = int(size / aspect_ratio)
        else:
            new_h = size
            new_w = int(size * aspect_ratio)
            
        return pygame.transform.scale(img, (new_w, new_h))
        
    except Exception as e:
        # 読み込めない時の予備（正方形の塗りつぶし）
        print(f"Error loading {path} at {full_path if 'full_path' in locals() else 'unknown'}: {e}")
        surf = pygame.Surface((size, size))
        surf.fill(fallback_color)
        return surf

IMG_PLAYER = load_asset("player.png", 45, CYAN)
IMG_LIFE = load_asset("player.png", 25, CYAN)
IMG_BOMB = load_asset("bomb.png", 25, LIME)
IMG_BG = load_asset("background.png", WIDTH, (30, 30, 30))
IMG_BG.set_alpha(100)
        
        

# --- 3. クラス定義 ---
class PlayerBullet:
    def __init__(self, x, y):
        self.pos = [float(x), float(y)]
        self.angle = -math.pi / 2
        self.speed = 12  # 18から12に減速（お好みで調整してください）
        self.turn_speed = 0.15

    def update(self, targets):
        # 1. ターゲット（最も近い敵）を探す
        target = None
        min_dist = 9999
        for e in targets:
            dist = math.hypot(e.pos[0] - self.pos[0], e.pos[1] - self.pos[1])
            if dist < min_dist:
                min_dist = dist
                target = e

        # 2. ホーミング計算
        if target:
            target_angle = math.atan2(target.pos[1] - self.pos[1], target.pos[0] - self.pos[0])
            diff = (target_angle - self.angle + math.pi) % (math.pi * 2) - math.pi
            self.angle += max(min(diff, self.turn_speed), -self.turn_speed)

        # 3. 移動
        self.pos[0] += math.cos(self.angle) * self.speed
        self.pos[1] += math.sin(self.angle) * self.speed

        # 4. 【重要】当たり判定のチェック
        # 弾が速い場合、判定がシビアだと通り抜けるので、少し広め(radius + 15)にします
        for e in targets:
            dist = math.hypot(e.pos[0] - self.pos[0], e.pos[1] - self.pos[1])
            if dist < e.radius + 15: 
                return e  # 当たった敵のオブジェクトを返す
        
        return None  # どこにも当たっていない

    def draw(self):
        pygame.draw.circle(screen, KOZUE, (int(self.pos[0]), int(self.pos[1])), 6)
        pygame.draw.circle(screen, WHITE, (int(self.pos[0]), int(self.pos[1])), 3)

class EnemyBullet:
    def __init__(self, x, y, angle, speed, color, b_type="normal", radius=5, draw_type="circle"):
        self.pos, self.angle, self.speed, self.color = [float(x), float(y)], angle, speed, color
        self.type, self.radius, self.draw_type = b_type, radius, draw_type
        self.timer = 0
        self.is_dead = False # 炸裂した後に消すためのフラグ
        self.accel = 1.0  # 加速倍率 (1.0 = 等速)
        self.max_speed = 4.0
        self.wait_move = False # 静止フラグ
        self.max_timer = 90

    def update(self, p_pos, e_bullets): # 引数にリストを追加
        self.timer += 1
        
        # --- AOE（予兆弾）の専用ロジック ---
        if self.type == "aoe":
            # 1. 予兆期間中は判定を0にする（当たり判定なし）
            self.current_radius = 0 
            
            # 2. 寿命が来たら爆発して消える
            if self.timer >= self.max_timer:
                num = 16
                for i in range(num):
                    ang = i * (math.pi * 2 / num)
                    # 爆発後の実体弾を生成（こっちは normal タイプ）
                    e_bullets.append(EnemyBullet(self.pos[0], self.pos[1], ang, 3.5, self.color, radius=3))
                self.is_dead = True
                return
            
            # 予兆中は移動しない
            return
        
        # --- タイムラグ弾（殺意向上・再照準版） ---
        if self.type == "timelag":
            stop_duration = 60 # 1秒間停止
            
            if self.timer < stop_duration:
                # 停止中は自機をじっと見つめる（デバッグ時の予測線と一致させる）
                # 動き出す「直前」までターゲットを更新し続ける
                self.angle = math.atan2(p_pos[1] - self.pos[1], p_pos[0] - self.pos[0])
                return 
            
            # 停止時間を過ぎた瞬間に加速を開始
            if self.accel != 1.0 and self.speed < self.max_speed:
                # 初期速度が0の場合、最小速度 0.5 からスタート
                if self.speed == 0: self.speed = 0.5
                self.speed *= self.accel

        # --- 通常の加速処理 (timelag以外でも適用) ---
        elif self.accel != 1.0:
            if self.speed < self.max_speed:
                self.speed *= self.accel
        
        current_speed = self.speed

        # --- 特殊ギミック：氷 ---
        if self.type == "ice_break":
            if 30 < self.timer < 70: current_speed = 0
            elif self.timer == 70:
                num = 12
                for i in range(num):
                    ang = i * (math.pi * 2 / num) + self.angle
                    e_bullets.append(EnemyBullet(self.pos[0], self.pos[1], ang, 2.0, CYAN, radius=3))
                self.is_dead = True
        
        if self.type == "solar_flare":
            if 40 < self.timer < 90:
                current_speed *= 0.8 # 急減速
            elif self.timer == 90:
                # 巨大弾が「爆発」して全方位にレーザーを放つ
                num_rays = 12
                for i in range(num_rays):
                    ang = i * (math.pi * 2 / num_rays)
                    e_bullets.append(EnemyBullet(self.pos[0], self.pos[1], ang, 5.0, GOLD, draw_type="laser", radius=4))
                self.is_dead = True # 巨大弾自体は消滅
        
        elif self.type == "zigzag":
            if self.timer % random.randint(20, 40) == 0:
                self.angle += random.choice([math.pi/2, -math.pi/2])
                
        move_speed = current_speed
        
        if self.type == "heavy":
            # 重い弾：少しずつ下に落ちるような重力演出
            self.pos[1] += 0.5 

        # 移動反映
        self.pos[0] += math.cos(self.angle) * move_speed
        self.pos[1] += math.sin(self.angle) * move_speed
        
        # 周期的に速度を反転させる (例: 120フレームごとに反転)
        # self.timer が 120, 240, 360... の瞬間に反転
        if self.type == "pendulum" and self.timer % 120 == 0:
            self.speed *= -1  # 速度を逆にする
        
        

    def draw(self):
        # 色決定
        is_frozen = (self.type == "ice_break" and 30 < self.timer < 70)
        is_waiting = (self.type == "timelag" and self.timer < 60)
        color = WHITE if (is_frozen or (is_waiting and self.timer % 10 < 5)) else self.color
        
        if self.type == "aoe":
            r = self.radius
            # 半透明用のSurface作成
            aoe_surf = pygame.Surface((int(r * 2 + 10), int(r * 2 + 10)), pygame.SRCALPHA)
            aoe_surf.fill((0, 0, 0, 0)) # 透明で塗りつぶし
            
            center = (int(r + 5), int(r + 5))
            ratio = min(1.0, self.timer / self.max_timer)
            
            # --- 半透明の描画 (Aの値を100程度に下げる) ---
            # 外側の塗りつぶし (RGBA: A=80)
            pygame.draw.circle(aoe_surf, (*self.color, 80), center, int(r))
            # 縁取り (RGBA: A=150)
            pygame.draw.circle(aoe_surf, (*self.color, 150), center, int(r), 2)
            # チャージ円
            pygame.draw.circle(aoe_surf, (255, 255, 255, 100), center, int(r * ratio), 1)

            screen.blit(aoe_surf, (int(self.pos[0] - center[0]), int(self.pos[1] - center[1])))
        
        
        if self.draw_type == "laser":
    
            is_big_laser = (self.radius > 10)
            
            # 判定（self.pos）がこの線の中にあるように、長さをあえて短く(150程度)する
            # これを連射することで、隙間のない「当たり判定の棒」になります
            length = 150 if is_big_laser else 30
            back_len = 20 # 根元の隙間埋め
            
            start_x = self.pos[0] - math.cos(self.angle) * back_len
            start_y = self.pos[1] - math.sin(self.angle) * back_len
            end_x = self.pos[0] + math.cos(self.angle) * length
            end_y = self.pos[1] + math.sin(self.angle) * length
            
            # 外側の光
            pygame.draw.line(screen, color, (start_x, start_y), (end_x, end_y), int(self.radius * 2))
            # 内側の芯
            pygame.draw.line(screen, WHITE, (start_x, start_y), (end_x, end_y), int(self.radius * 0.7))
            
        else:
            # 通常弾
            pygame.draw.circle(screen, WHITE, (int(self.pos[0]), int(self.pos[1])), self.radius + 2)
            pygame.draw.circle(screen, color, (int(self.pos[0]), int(self.pos[1])), self.radius)
            
    
       
            
class Item:
    def __init__(self, x, y, itype="score", is_collecting=False):
        self.pos, self.vel = [x, y], [random.uniform(-2, 2), -5]
        self.itype = itype # "score" or "bomb"
        self.is_collecting = is_collecting
    def update(self, p_pos):
        if self.is_collecting:
            ang = math.atan2(p_pos[1]-self.pos[1], p_pos[0]-self.pos[0])
            self.pos[0] += math.cos(ang)*15; self.pos[1] += math.sin(ang)*15
        
        # 自動回収判定
        elif p_pos[1] < 450:
            ang = math.atan2(p_pos[1]-self.pos[1], p_pos[0]-self.pos[0])
            self.pos[0] += math.cos(ang)*12; self.pos[1] += math.sin(ang)*12
        else:
            self.vel[1] += 0.2; self.pos[0] += self.vel[0]; self.pos[1] += self.vel[1]
            
    def draw(self):
        color = GOLD if self.itype == "score" else LIME
        pygame.draw.rect(screen, color, (self.pos[0]-7, self.pos[1]-7, 14, 14))
        if self.itype == "bomb":
            f = pygame.font.SysFont("arial", 12, bold=True)
            screen.blit(f.render("B", True, BLACK), (self.pos[0]-4, self.pos[1]-7))

# --- 4. 敵・スペルカード ---
class SpellCard:
    def __init__(self, name, hp, color, limit_time=60):
        self.name, self.max_hp, self.bg_color = name, hp, BG_COLOR_SPELL
        self.limit_time = limit_time * 60
        self.timer = self.limit_time
    def get_danger_ratio(self): return 1.0 - (self.timer / self.limit_time)
    def update_timer(self):
        if self.timer > 0: self.timer -= 1
        return self.timer <= 0
    def draw_bg(self, surf): surf.fill(self.bg_color)

class ProminenceX(SpellCard):
    def __init__(self): super().__init__("炎符「プロミネンス・極圏壁」", 2250, (60, 10, 10), 40)
    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        interval = max(6, 16 - int(d * 10))
        if t % interval == 0:
            rot = t * (0.02 + d * 0.03)
            for i in range(-10, 13):
                if -2 < i < 2: continue
                e_bullets.append(EnemyBullet(boss.pos[0]+math.cos(rot)*i*50, boss.pos[1]+math.sin(rot)*i*25, rot+1.57, 1.2 + d, RED))

class SolarFlareBurst(SpellCard):
    def __init__(self): super().__init__("烈符「焦熱のソーラーフレア」", 2800, (70, 30, 0), 45)
    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        if t % 2 == 0:
            ways = 4
            for i in range(ways):
                ang = (t * 0.1) + (i * (math.pi * 2 / ways))
                speed = 2.0 + math.sin(t * 0.05) * 1.0 + (d * 1.5)
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, speed, GOLD))
        if t % 40 == 0:
            ways = 24
            for i in range(ways):
                ang = (i * (math.pi * 2 / ways)) - (t * 0.02)
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, 2.5, WHITE))
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang + 0.1, 2.0, ORANGE))

class MilkyWay(SpellCard):
    def __init__(self): super().__init__("銀河「スターダスト・流転旋律」", 3200, (10, 10, 50), 50)
    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        
        # --- ギミック1: 周囲からの「巨大重力弾」 (サテライト射出) ---
        # ボスの周囲を回る4つの発生源から、低速で巨大な弾を出す
        for i in range(4):
            orbit_ang = t * 0.03 + (i * math.pi / 2)
            dist = 140 + math.sin(t * 0.02) * 40 # 発生源自体が寄ったり離れたりする
            sx = boss.pos[0] + math.cos(orbit_ang) * dist
            sy = boss.pos[1] + math.sin(orbit_ang) * dist
            
            if t % 20 == 0:
                # 半径15の巨大弾。これは「避ける対象」ではなく「移動を制限する壁」
                e_bullets.append(EnemyBullet(sx, sy, orbit_ang, 1.0 + d, GOLD, radius=15))

        # --- ギミック2: 本体からの「大小混合・多重螺旋」 ---
        # 密度の高い小弾の中に、時折「中弾」を混ぜてリズムを狂わせる
        if t % 3 == 0:
            # 2方向に、逆回転する螺旋
            for i in range(2):
                base_ang = t * 0.15 * (1 if i == 0 else -1)
                # サイン波で「うねり」を入れ、単調な直線移動を排除
                wavy_ang = base_ang + math.sin(t * 0.1) * 0.6
                size = 8 if t % 12 == 0 else 3 # 4回に1回、中玉を混ぜる
                speed = 4.0 + d * 3.0
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], wavy_ang, speed, RAINBOW_COLORS[t % 7], radius=size))

        # --- ギミック3: 【最重要】再照準・加速スナイプ ---
        # 「自機に飛んでこない」を解消。動き出す瞬間に自機を確実に狙う
        if t % 60 == 0:
            count = 16 + int(d * 12)
            for i in range(count):
                # ボスの周囲に、綺麗な円状にまず「設置」する
                deploy_ang = i * (math.pi * 2 / count)
                deploy_r = 200
                tx = boss.pos[0] + math.cos(deploy_ang) * deploy_r
                ty = boss.pos[1] + math.sin(deploy_ang) * deploy_r
                
                # 最初は速度0 (b_type="timelag")
                b = EnemyBullet(tx, ty, 0, 0, WHITE, b_type="timelag", radius=4)
                
                # 動き出す直前の猶予時間
                b.timer = -45 # 0.75秒後に動き出す
                
                # 【ここが解決策】
                # 本来ならBulletクラス内で動き出す瞬間に計算すべきですが、
                # 簡易的に、このタイミングで「未来の自機位置」を予測して角度をセット
                # (プレイヤーが動くことを前提に、少し角度に幅を持たせる)
                b.angle = math.atan2(p_pos[1] - ty, p_pos[0] - tx)
                b.accel = 1.12 + (d * 0.03) # 急加速
                b.max_speed = 11.0 # 超高速
                e_bullets.append(b)

class GhostlyOrbit(SpellCard):
    def __init__(self): super().__init__("霊符「常世を巡る久遠の輪舞」", 4000, (30, 0, 40), 60)
    
    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        
        # --- レイヤー1: 六角形の幾何学の檻（ボスの周囲） ---
        # 巨大弾(radius=15)を六角形状に配置し、回転させる
        if t % 100 == 0:
            sides = 6
            for i in range(sides):
                # 回転角。時間とともに回る
                ang = i * (math.pi * 2 / sides) + (t * 0.02)
                dist = 200 + math.sin(t * 0.05) * 50 # 檻が伸縮する
                bx = boss.pos[0] + math.cos(ang) * dist
                by = boss.pos[1] + math.sin(ang) * dist
                
                # 巨大弾は「動く壁」としてその場に少し停滞
                b = EnemyBullet(bx, by, ang, 0.5 + d, LIME, b_type="timelag", radius=15)
                b.timer = -60 # 1秒間その場で威嚇
                e_bullets.append(b)

        # --- レイヤー2: 【凶悪】再捕捉・加速スナイプ（大小混合） ---
        # ボスの周りに「設置」され、動き出す瞬間に自機を確実に狙う
        if t % 45 == 0:
            num_snipes = 8 + int(d * 8)
            for i in range(num_snipes):
                spawn_ang = i * (math.pi * 2 / num_snipes)
                # ボスのすぐ側で生成
                sx = boss.pos[0] + math.cos(spawn_ang) * 80
                sy = boss.pos[1] + math.sin(spawn_ang) * 80
                
                # 弾のサイズをバラバラにして視認性を狂わせる
                size = random.choice([3, 5, 8])
                b = EnemyBullet(sx, sy, 0, 0, WHITE, b_type="timelag", radius=size)
                
                # 動き出すまでの時間
                b.timer = -40 - (i * 2) 
                # 加速度を高く設定。動き出した瞬間、逃げ場を奪う
                b.accel = 1.1 + (d * 0.05)
                b.max_speed = 9.0 + (d * 3.0)
                # 角度は EnemyBullet.update 内で自機方向へ再計算される
                e_bullets.append(b)

        # --- レイヤー3: 画面全体を覆う「多層サイン波」 ---
        # 規則的な幾何学の中に「揺らぎ」を作り、単調さを排除
        if t % 4 == 0:
            # 常に2方向に回転しながらバラまく
            for i in range(2):
                base_ang = t * 0.1 * (1 if i == 0 else -1)
                # 角度をサイン波でうねらせる
                wavy_ang = base_ang + math.sin(t * 0.07) * 0.8
                speed = 2.5 + d * 2.0
                # 虹色の弾で万華鏡のような視覚効果
                color = RAINBOW_COLORS[t % 7]
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], wavy_ang, speed, color, radius=3))
                
class AquaPressure(SpellCard):
    def __init__(self): super().__init__("「海符「アビスプレッシャー」", 2800, (0, 20, 50), 45)
    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio() # 0.0 ～ 1.0
        
        # 1. 巨大な水弾：HPが減るほど回転（t*0.01*d）が加わり、弾速も上がる
        if t % 50 == 0:
            for i in range(8):
                ang = i * (math.pi * 2 / 8) + t * (0.01 + d * 0.02)
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, 2.0 + d, BLUE, radius=15))
        
        # 2. 水流レーザー：HPが減るほど発射間隔が短くなる (15 -> 7)
        interval = max(15, 30 - int(d * 15))
        if t % interval == 0:
            ang = math.atan2(p_pos[1]-boss.pos[1], p_pos[0]-boss.pos[0])
            spread = 0.3 + (d * 0.3)
            for i in range(-1, 2):
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang + i*spread, 7.0 + d * 2, CYAN, draw_type="laser", radius=3))

class LeviathanRay(SpellCard):
    def __init__(self): 
        super().__init__("「極符「絶対零度の結晶光線」", 2700, (0, 40, 60), 50)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()

        # 1. 【炸裂する氷晶】
        # 画面にランダムに放たれ、停止したあとに砕け散る
        if t % 30 == 0:
            for i in range(3 + int(d * 3)): # HP減少で数が増える
                ang = random.uniform(0, math.pi * 2)
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, 3.0 + d, BLUE, b_type="ice_break", radius=8))

        # 2. 【絶対零度の鎖】画面の端から挟み込むレーザー
        if t % 90 == 0:
            for x in [0, WIDTH]:
                for i in range(5):
                    y = (HEIGHT // 5) * i + (t % 100)
                    ang = 0 if x == 0 else math.pi
                    e_bullets.append(EnemyBullet(x, y, ang, 2.0 + d, WHITE, draw_type="laser", radius=3))

        # 3. 【追尾する冷気】自機をゆっくり追いかける中玉
        if t % 100 == 0:
            ang = math.atan2(p_pos[1]-boss.pos[1], p_pos[0]-boss.pos[0])
            e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, 1.5, CYAN, radius=12))

class PhotonSmasher(SpellCard):
    def __init__(self): super().__init__("「煌符「フォトニック・オーバードライブ」", 2700, (50, 50, 0), 50)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()

        # 1. 【光のカーテン】サイン波でうねる全方位レーザー
        # HPが減るほど、うねりの振幅と回転速度がアップ
        if t % 15 == 0:
            ways = 18
            for i in range(ways):
                # サイン波を使って、発射角度を常にゆらゆらさせる
                wave = math.sin(t * 0.05) * 0.5
                ang = (i * (math.pi * 2 / ways)) + (t * 0.02) + wave
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, 3.5 + d, GOLD, draw_type="laser", radius=3))

        # 2. 【太陽の欠片】螺旋状に配置され、途中で「加速」する大玉
        # 普通の螺旋に見えて、後から飛んできた弾が追い越してくるので避けづらい
        if t % 6 == 0:
            ang = t * 0.2
            # HPが減るほど加速率(d*2.5)が高まる
            speed = 1.5 + (t % 30) * 0.1 + d * 1.5
            e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, speed, ORANGE, radius=10))

        # 3. 【フレア・バースト】特定のタイミングで放たれる自機狙いの交差弾
        # プレイヤーが横移動で避けるのを制限する
        if t % 80 == 0:
            target_ang = math.atan2(p_pos[1]-boss.pos[1], p_pos[0]-boss.pos[0])
            for i in range(-3, 4): # 7方向の扇状弾
                if i == 0: continue # 真ん中をあえて空けて、プレイヤーを誘導する
                # 速度の違う弾を2つ重ねて、奥行きを作る
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], target_ang + i*0.2, 5.0, WHITE, radius=6))
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], target_ang + i*0.2, 7.0, RED, draw_type="laser", radius=4))

                
class SupernovaGigant(SpellCard):
    def __init__(self): 
        super().__init__("「星符「亡き太陽の終焉」", 2200, (60, 0, 0), 50)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio() * 0.7

        # 1. 【中心核の脈動】巨大弾の空中炸裂（既存）
        if t % 120 == 0:
            count = 4 + int(d * 4)
            for i in range(count):
                ang = i * (math.pi * 2 / count) + t * 0.05
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, 2.0, GOLD, b_type="solar_flare", radius=25))

        # 2. 【光の螺旋】（修正箇所：ways をループに使用）
        # HPが減るほど ways (密度) が 12 から 30 へ増加
        ways = 6 + int(d * 10) 
        if t % 6 == 0:
            base_ang = (t * 0.05) + math.sin(t * 0.02) * 1.0
            for i in range(ways): # ここで ways を使用！
                # 全方位に均等に割り振った角度を計算
                final_ang = base_ang + (i * (math.pi * 2 / ways))
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], final_ang, 2.5 + d * 2, ORANGE, radius=4))

        # 3. 【コロナの噴出】自機狙い（既存）
        interval = max(15, 40 - int(d * 25))
        if t % interval == 0:
            target_ang = math.atan2(p_pos[1]-boss.pos[1], p_pos[0]-boss.pos[0])
            for i in range(-1, 2):
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], target_ang + i*0.15, 4.5, RED, draw_type="laser", radius=3))

        # 4. 【ソーラープロミネンス】左右からの包囲網
        # HPが半分を切ると発動。ボスの肩あたりから巨大な弧を描いて弾が降り注ぐ
        if d > 0.5 and t % 15 == 0:
            # 左側からの噴出
            left_ang = math.pi / 4 + math.sin(t * 0.02) * 0.5
            e_bullets.append(EnemyBullet(boss.pos[0] - 50, boss.pos[1], left_ang, 2.5 + d, PURPLE, radius=6))
            
            # 右側からの噴出
            right_ang = math.pi * 3 / 4 - math.sin(t * 0.02) * 0.5
            e_bullets.append(EnemyBullet(boss.pos[0] + 50, boss.pos[1], right_ang, 2.5 + d, PURPLE, radius=6))
            
# --- 1. 霧の妖精王女「ネフェル」 ---
class RainbowOverTheRainbow(SpellCard):
    def __init__(self):
        super().__init__("虹符「七色のカレイドスコープ」", 2500, (20, 20, 30), 60)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio() * 0.7
        
        # --- パターン1: リサジュー曲線による「光の花」 ---
        # 自機は狙わず、常に決まった幾何学軌道を描く
        if t % 2 == 0:
            # 2つの異なる周期のサイン合成で複雑な模様を作る
            ang = t * 0.1
            dist = 150 + math.sin(t * 0.05) * 100
            bx = boss.pos[0] + math.cos(ang) * dist
            by = boss.pos[1] + math.sin(ang * 0.5) * dist # 軌道を歪ませて「花」にする
            
            color = RAINBOW_COLORS[(t // 10) % 7]
            # 弾はその場から放射状にゆっくり広がる
            e_bullets.append(EnemyBullet(bx, by, ang, 1.2, color, radius=3))

        # --- パターン2: 黄金螺旋の展開（画面全体の回転） ---
        if t % 40 == 0:
            count = 32
            for i in range(count):
                # 黄金角に近い角度で展開し、美しい螺旋を作る
                ang = i * (math.pi * 2 / count) + (t * 0.02)
                # zigzagを使って、一定距離でカクッと曲がる幾何学的な動き
                b = EnemyBullet(boss.pos[0], boss.pos[1], ang, 2.5 + d, WHITE, b_type="zigzag", radius=2)
                e_bullets.append(b)

        # --- パターン3: 正多角形の結界（逃げ道を限定する幾何学の壁） ---
        if t % 120 == 0:
            poly_sides = 6 # 六角形の結界
            for i in range(poly_sides):
                base_ang = i * (math.pi * 2 / poly_sides) + (t * 0.01)
                # 1辺につき10発の弾を並べて「線」を作る
                for j in range(10):
                    offset_dist = j * 40
                    # 辺に沿って弾を配置
                    bx = boss.pos[0] + math.cos(base_ang) * 200 + math.cos(base_ang + math.pi/2) * (offset_dist - 200)
                    by = boss.pos[1] + math.sin(base_ang) * 200 + math.sin(base_ang + math.pi/2) * (offset_dist - 200)
                    
                    # 結界の弾はゆっくりと外側へ
                    e_bullets.append(EnemyBullet(bx, by, base_ang, 0.8, CYAN, radius=4))
                
class CrystalizeAbsoluteZero(SpellCard):
    def __init__(self):
        super().__init__("氷符「絶対零度のクリスタライズ」", 2800, (20, 20, 30), 60)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio() * 0.7

        # --- パターン1: 氷の幾何学結晶（六角形の壁） ---
        if t % 120 == 0:
            for i in range(6):
                base_ang = i * (math.pi * 2 / 6)
                for j in range(10): # 1辺に10発
                    dist = 50 + j * 20
                    bx = boss.pos[0] + math.cos(base_ang) * dist
                    by = boss.pos[1] + math.sin(base_ang) * dist
                    e_bullets.append(EnemyBullet(bx, by, base_ang + math.pi/2, 1.0 + d, (200, 255, 255), radius=4))

        # --- パターン2: 巨大氷塊の設置（分裂） ---
        interval = max(40, 80 - int(d * 40))
        if t % interval == 0:
            # iを使って3方向に巨大弾
            for i in range(3):
                ang = math.atan2(p_pos[1]-boss.pos[1], p_pos[0]-boss.pos[0]) + (i-1)*0.5
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, 2.0, (150, 255, 255), b_type="ice_break", radius=10))

        # --- パターン3: 雪のようなバラマキ ---
        if t % 10 == 0:
            rx = random.randint(0, WIDTH)
            e_bullets.append(EnemyBullet(rx, 0, math.pi/2, 1.2 + d, (255, 255, 255), radius=2))

# --- 2. 宵闇の裁定者「ルナ・エクリプス」 ---
class MoonCraterHopping(SpellCard):
    def __init__(self):
        # ここで名前、HP、色、制限時間を親クラスに渡す
        # これにより、Enemyクラス側で spell_class() と呼ぶだけで動くようになります
        super().__init__("月符「静寂なる静海への誘い」", 3000, (20, 20, 30), 60)

    def update(self, boss, p_pos, e_bullets, t):
        # 難易度係数 d (0.0 ～ 0.7)
        d = self.get_danger_ratio() * 0.7
        
        # --- レイヤー1：天蓋の幾何学 (薄青) ---
        # 密度を下げ(10->7)、弾速を少し落としました
        if t % 50 == 0:
            count = 7 + int(d * 5)
            for i in range(count):
                sx = (WIDTH // count) * i
                angle = math.pi/2 + math.sin(t * 0.05 + i) * 0.5
                e_bullets.append(EnemyBullet(sx, 0, angle, 1.5 + d, (100, 100, 255), radius=3))

        # --- レイヤー2：【緩和】連鎖ヘキサ・スナイプ ---
        # 全体の発生スパンを 200 -> 240 フレームに延長
        if t % 240 == 0:
            sides = 6
            # 二重、三重になるのを抑え、最大でも二重までに調整
            layers = 1 + int(d * 1.5)
            for L in range(layers):
                dist = 240 + (L * 60)
                for i in range(sides):
                    ang = i * (math.pi * 2 / sides) + (L * 0.5)
                    tx = p_pos[0] + math.cos(ang) * dist
                    ty = p_pos[1] + math.sin(ang) * dist
                    
                    b = EnemyBullet(tx, ty, 0, 0, (255, 50, 50), b_type="timelag", radius=5)
                    
                    # --- 間隔の調整 ---
                    # i * 15 から i * 20 に拡大。約0.33秒に1発のペース。
                    # 最初の1発が出るまでの余裕(60)も増やしました
                    b.timer = -(60 + i * 20 + L * 80) 
                    
                    b.accel = 1.08 # 加速度を大幅に低下 (1.18 -> 1.08)
                    b.max_speed = 8.0 # 最高速を抑制 (14.0 -> 8.0)
                    e_bullets.append(b)

        # --- レイヤー3：【削減】左右のルナ・スライサー ---
        # 5列あった弾を 3列に減らし、上下の隙間を大きく空けました
        if t % 100 == 0:
            for side in [0, WIDTH]:
                ang = 0 if side == 0 else math.pi
                for j in range(5): # 5 -> 3
                    sy = 150 + j * 180 + (t % 100)
                    e_bullets.append(EnemyBullet(side, sy, ang, 1.0 + d, (150, 50, 200), radius=6))

        if t % 2 == 0:
            # 3方向に同時に展開することで、隙間のない螺旋を描く
            for i in range(3):
                rot = t * 0.15 + (i * math.pi * 2 / 3)
                # 弾速をわざと遅く（2.0 -> 1.5）することで、画面に長時間残り、
                # ボスの周りに「滞留する魔力の渦」のような視覚効果を生みます。
                speed = 1.5 + math.sin(t * 0.02) * 0.5 # 速度に揺らぎを入れ、幾何学を複雑化
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], rot, speed, (40, 40, 120), radius=3))
                
class GravityBlackHole(SpellCard):
    def __init__(self):
        super().__init__("影符「常闇に溶ける不確定な境界」", 3200, (20, 20, 40), 60)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio() * 0.5 # 補正を 0.7 -> 0.5 に下げて発狂をマイルドに

        # --- パターン1: ブラックホール核の生成 ---
        # 100 -> 150フレームに。レーザー爆発の頻度を下げて安地を確保しやすくします
        if t % 150 == 0:
            for side in [-1, 1]:
                bx = boss.pos[0] + side * 220
                by = boss.pos[1] + 50
                # 速度を 1.0 -> 0.7 に下げて、爆発までの位置を高く保つ（逃げ場を広く）
                b = EnemyBullet(bx, by, math.pi/2, 0.7, (80, 0, 120), b_type="solar_flare", radius=18)
                e_bullets.append(b)

        # --- パターン2: 収束する「事象の地平線」 ---
        # 4 -> 8フレームに。弾幕の密度を半分にして、隙間を広げます
        if t % 8 == 0:
            ways = 4 + int(d * 3) # 5 -> 4 に微減
            for i in range(ways):
                ang = (t * 0.04) + (i * (math.pi * 2 / ways)) # 回転を少し遅く
                # 外へ向かう通常弾（速度を一定に近づける）
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, 1.8 + d, PURPLE, radius=4))
                
                # 【逆走弾の緩和】 頻度を 20 -> 40 に落とし、ボスの中心ではなく「少しズレた場所」へ
                if t % 40 == 0:
                    bx = boss.pos[0] + math.cos(ang) * 450
                    by = boss.pos[1] + math.sin(ang) * 450
                    # 中心(boss.pos)からわざと 0.5ラジアン ズラして、自機への直撃を防ぐ
                    rev_ang = math.atan2(boss.pos[1]-by, boss.pos[0]-bx) + 0.5
                    b = EnemyBullet(bx, by, rev_ang, 1.2, (120, 0, 220), b_type="timelag", radius=3)
                    b.timer = -40 # 溜め時間を増やして、避ける準備をさせる
                    e_bullets.append(b)

        # --- パターン3: 中心からの重力レーザー ---
        # 40 -> 60フレームに。3-way -> 2-way(自機の両サイド)へ変更
        if t % 60 == 0:
            target_ang = math.atan2(p_pos[1]-boss.pos[1], p_pos[0]-boss.pos[0])
            # 0(中央)を抜いて、左右に飛ばすことで「動かなければ当たらない」時間を作ります
            for offset in [-0.3, 0.3]: 
                e_bullets.append(EnemyBullet(
                    boss.pos[0], boss.pos[1], target_ang + offset, 3.5, (180, 0, 255), 
                    draw_type="laser", radius=2
                ))

# --- 3. 雷鳴の武人「ライゴウ」 ---
class ThunderBoltStrike(SpellCard):
    def __init__(self):
        super().__init__("鳴符「八雷神の咆哮」", 3500, (255, 255, 0), 60)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        
        # --- ビット（子機）の位置計算 ---
        # ボスの周りを8の字、または左右に浮遊するポイントを定義
        bit_dist = 120 + math.sin(t * 0.05) * 30
        bits = [
            (boss.pos[0] - bit_dist, boss.pos[1] + math.cos(t * 0.03) * 50), # 左ビット
            (boss.pos[0] + bit_dist, boss.pos[1] + math.sin(t * 0.03) * 50)  # 右ビット
        ]

        # 1. 【ビットからのクロス・レーザー】
        # 左右のビットから自機を挟み撃ちするようにレーザーを放つ
        if t % 60 == 0:
            for bx, by in bits:
                # 自機への角度を計算
                ang = math.atan2(p_pos[1] - by, p_pos[0] - bx)
                # 左右から交差する黄色い閃光
                e_bullets.append(EnemyBullet(bx, by, ang, 12.0, YELLOW, draw_type="laser", radius=3))

        # 2. 【ビット展開：放電サークル】
        # ビットが通った軌跡に、正方形を描くように弾を設置する
        if t % 15 == 0:
            for bx, by in bits:
                # 4方向（十字）に弾を飛ばし、擬似的な「ひし形」の陣形を作る
                for i in range(4):
                    ang = i * (math.pi / 2) + (t * 0.02)
                    # ビットからゆっくりと広がる青白い火花
                    e_bullets.append(EnemyBullet(bx, by, ang, 1.5 + d, CYAN, radius=2))

        # 3. 【ボス本体：垂直ストライク】
        # ボス本体からは「予兆」を伴う垂直の雷を落とす
        if t % 80 == 0:
            # プレイヤーの現在のX座標を狙って、上から予告線
            target_x = p_pos[0]
            # 予告として細いレーザー
            e_bullets.append(EnemyBullet(target_x, 0, math.pi/2, 20.0, WHITE, draw_type="laser", radius=1))
            
            # HPが低い場合、その左右にもおまけの雷を落とす
            if d > 0.5:
                for offset in [-60, 60]:
                    e_bullets.append(EnemyBullet(target_x + offset, 0, math.pi/2, 20.0, YELLOW, draw_type="laser", radius=2))

        # 4. 【幾何学的な放電：スパーク・チェイン】
        # 画面中央付近に「停滞する弾」をビットから撃ち出し、一瞬止まってから自機へ加速
        if t % 100 == 0:
            for bx, by in bits:
                ang = math.atan2(p_pos[1] - by, p_pos[0] - bx)
                # timelag 属性により、一度止まってから急加速する「雷の鋭さ」を表現
                e_bullets.append(EnemyBullet(bx, by, ang, 4.0, WHITE, "timelag"))

class Tetravortex(SpellCard): # クラス名もカッコよく
    def __init__(self):
        # 演出の色も (200, 255, 100) から、より高電圧な (0, 255, 200) へ微調整
        super().__init__("虚符「九界崩壊・ゼロの共鳴」", 3500, (0, 255, 200), 60)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        
        # 4つのビットの位置（さらに高速回転させて「回路」感を出す）
        # bit_dist を大きく揺らすことで、幾何学模様が収縮・拡大する
        bit_dist = 180 + math.cos(t * 0.05) * 80
        bits = []
        for i in range(4):
            ang = i * (math.pi / 2) + t * 0.04 # 回転を鋭く
            bx = boss.pos[0] + math.cos(ang) * bit_dist
            by = boss.pos[1] + math.sin(ang) * bit_dist
            bits.append((bx, by))

        # 【回路形成：リンク・ライトニング】
        # ビット間に一瞬でレーザーが走り、そのあと「直角」に弾が散る
        if t % 30 == 0:
            for i in range(4):
                x1, y1 = bits[i]
                x2, y2 = bits[(i + 1) % 4]
                ang = math.atan2(y2 - y1, x2 - x1)
                # 速度を上げ、b_type="zigzag" の折れを「鋭い稲妻」に見せる
                e_bullets.append(EnemyBullet(x1, y1, ang, 4.0 + d * 4, CYAN, b_type="zigzag"))

        # 【中心：虚空の特異点】
        # ボス本体からは、ビットの回転とは「逆」に、カクカクした低速弾を設置
        if t % 15 == 0:
            base_ang = -t * 0.03
            for i in range(4):
                ang = base_ang + (i * math.pi / 2)
                e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, 1.5 + d, LIME, b_type="zigzag"))

# --- 4. 豊穣の守護神「ガイヤ」 ---
class SquareDistraction(SpellCard):
    def __init__(self):
        # 名前も幾何学に特化。色は純粋なエメラルドグリーン (0, 255, 128)
        super().__init__("晶符「翠玉のフラグメント」", 4200, (0, 255, 128), 60)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        
        # --- 1. 幾何学の骨組み：ローテーティング・スクエア ---
        # 4つのビットが「正方形」の頂点となり、常に回転しながら大きさを変える
        angle_base = t * 0.02
        # 周期的に収縮（脈動）させることで迷宮のような圧迫感を生む
        size = 200 + math.sin(t * 0.04) * 100
        
        corners = []
        for i in range(4):
            ang = angle_base + (i * math.pi / 2) # 90度ずつ
            bx = boss.pos[0] + math.cos(ang) * size
            by = boss.pos[1] + math.sin(ang) * size
            corners.append((bx, by))

        # --- 2. 枠線からの放電：インワード・シュート ---
        # 正方形の「辺」の上から、中心（自機付近）へ向かって垂直に弾が出る
        # これにより「全方位」ではなく「四角い壁」が迫ってくる感覚になる
        if t % 8 == 0:
            for i in range(4):
                p1 = corners[i]
                p2 = corners[(i + 1) % 4]
                
                # 辺の上のランダムな点（または一定間隔）から発射
                # ここでは等間隔に配置して「格子」を表現
                num_on_side = 3
                for n in range(num_on_side):
                    # 辺上の座標
                    ratio = (n + 1) / (num_on_side + 1)
                    sx = p1[0] + (p2[0] - p1[0]) * ratio
                    sy = p1[1] + (p2[1] - p1[1]) * ratio
                    
                    # 辺に対して垂直な角度（内側向き）
                    edge_ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
                    fire_ang = edge_ang - math.pi / 2
                    
                    # 弾速をわざと遅くして、四角い形を維持したまま迫らせる
                    e_bullets.append(EnemyBullet(sx, sy, fire_ang, 1.5 + d, (150, 255, 200), radius=3))

        # --- 3. 空間の亀裂：プリズム・レーザー ---
        # 300フレームごとに、正方形の対角線をレーザーが結ぶ。
        # 幾何学的な「切断」を視覚化する演出。
        if t % 150 > 100:
            if t % 10 == 0:
                # 対角線のビット同士を結ぶ
                pairs = [(0, 2), (1, 3)]
                for i, j in pairs:
                    x1, y1 = corners[i]
                    x2, y2 = corners[j]
                    ang = math.atan2(y2 - y1, x2 - x1)
                    e_bullets.append(EnemyBullet(x1, y1, ang, 15.0, WHITE, draw_type="laser", radius=2))

        # --- 4. 弾幕の一時停止と再加速：グリッド・フリーズ ---
        # 画面に撃ち出された「四角い弾の列」を、ビットが光った瞬間に一時停止させる
        # (EnemyBullet側に 'timelag' 属性がある想定)
        if t % 200 == 100:
            # 既に飛んでいる弾の「加速」をリセットし、幾何学模様を空中で静止させる
            # この演出は、EnemyBulletのリスト全体を走査する処理がメイン側にあるとより効果的
            pass


class GeometricTectonics(SpellCard):
    def __init__(self):
        super().__init__("花符「幻視する庭園」", 5000, (255, 150, 200), 60)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        
        # --- 自機周辺：蕾の包囲網（難易度調整版） ---
        if t % 80 == 0: # 出現頻度を下げて余裕を作る
            bit_num = 8 # 弾の数
            radius = 180 # 少し遠くに出現
            rot_offset = t * 0.05
            
            for i in range(bit_num):
                # 【重要】難易度を下げるギミック：
                # 8個中2個分（90度分）を空けて、明確な「脱出口」を作る
                if i % bit_num in [0, 1]: continue 
                
                ang = rot_offset + (i * math.pi * 2 / bit_num)
                bx = p_pos[0] + math.cos(ang) * radius
                by = p_pos[1] + math.sin(ang) * radius
                
                # 弾の生成
                # 当たり判定(radius)を 3 に小さくし、速度も 1.0 程度に抑える
                e_bullets.append(EnemyBullet(
                    bx, by, ang + math.pi, 1.0 + d * 0.5, 
                    (255, 150, 255), b_type="timelag", radius=3
                ))

        # --- ボス本体：花開く幾何学模様 ---
        if t % 30 == 0:
            ways = 16
            for i in range(ways):
                # 黄金比っぽい回転を加えた全方位弾
                ang = i * (math.pi * 2 / ways) + (t * 0.02)
                e_bullets.append(EnemyBullet(
                    boss.pos[0], boss.pos[1], ang, 2.0, 
                    (100, 255, 150), radius=4
                ))

        # --- 3. ギミック：散りゆく残り香（オーガニック・トレース） ---
        # ボスの左右から、画面中央を「撫でる」ように曲線を描く弾の列。
        # 自機狙いではなく、画面を大きく横切る「蔦」の演出。
        if t % 60 == 0:
            for side in [-1, 1]:
                sx = boss.pos[0] + side * 200
                sy = boss.pos[1] - 50
                # 螺旋を描きながら、ゆっくりと画面下部へ
                for i in range(5):
                    ang = math.pi/2 + (side * 0.5) + (i * 0.1)
                    e_bullets.append(EnemyBullet(
                        sx, sy, ang, 1.5, (150, 255, 100), radius=3
                    ))
            
# --- 5. 時の観測者「クロノス」 ---
class StopWatchParadox(SpellCard):
    def __init__(self):
        super().__init__("時符「常世へ誘う久遠の秒針」", 4500, (200, 200, 255), 60)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        time_left = 60 - (t / 60)

        # ==========================================
        # ギミック：終焉のカウントダウン（残り10秒以下）
        # ==========================================
        if time_left <= 10:
            # 1. 全弾吸い込み（変更なし）
            for b in e_bullets:
                dx, dy = boss.pos[0] - b.pos[0], boss.pos[1] - b.pos[1]
                dist = math.sqrt(dx**2 + dy**2)
                if dist > 20:
                    b.angle = math.atan2(dy, dx) + 0.3
                    b.speed = 10.0
                else:
                    b.is_dead = True

            # 2. 最終レーザー：中央固定・判定強化版
            if time_left < 3:
                # 画面中央(通常 400x600 なら 200, 300)への角度を固定で計算
                # または math.pi / 2 (真下) などに固定
                fixed_angle = math.pi / 2 
                
                # 5フレームに1回、判定を持った「レーザーの破片」を連射する
                # これにより、一本の太い「当たり判定の帯」が作られます
                if t % 3 == 0:
                    laser = EnemyBullet(
                        boss.pos[0], boss.pos[1], fixed_angle, 4.0, 
                        (100, 150, 255), b_type="normal", radius=40, draw_type="laser"
                    )
                    e_bullets.append(laser)
            return
        # ==========================================
        # 通常時：咲夜風・幾何学ナイフ弾幕
        # ==========================================
        
        # 1. ボス本体：殺人ナイフ（密度を下げて避けやすく）
        if t % 35 == 0: # 30 -> 45 に間隔を広げた
            ways = 12 + int(d * 4) # 弾数を減らした
            base_ang = t * 0.02
            for i in range(ways):
                ang = base_ang + (i * math.pi * 2 / ways)
                e_bullets.append(EnemyBullet(
                    boss.pos[0], boss.pos[1], ang, 3.0, 
                    (255, 255, 255), b_type="normal", radius=2, draw_type="laser"
                ))

        # 2. 自機周辺：パーフェクト・フリーズ
        # 360フレーム(6秒)に一度。最も美しいが、最も危険なため安地を広く。
        if t % 360 == 0:
            num = 10 # 12 -> 8 に減らして隙間を大きく
            radius = 180
            for i in range(num):
                # 咲夜の「手品」のように、上下左右に広い逃げ道を作る
                if i % 2 == 0: continue 
                
                ang = (i * math.pi * 2 / num)
                bx = p_pos[0] + math.cos(ang) * radius
                by = p_pos[1] + math.sin(ang) * radius
                to_p_ang = math.atan2(p_pos[1] - by, p_pos[0] - bx)
                
                e_bullets.append(EnemyBullet(
                    bx, by, to_p_ang, 1.2, 
                    (150, 150, 255), b_type="timelag", radius=2, draw_type="laser"
                ))

        # 3. 特殊演出：クロック・ディレイ（サイドからの狙い）
        if t % 60 == 0: # 40 -> 60 に緩和
            for side in [-1, 1]:
                sx = boss.pos[0] + side * 200
                ang_to_p = math.atan2(p_pos[1] - boss.pos[1], p_pos[0] - sx)
                e_bullets.append(EnemyBullet(
                    sx, boss.pos[1], ang_to_p, 4.0, 
                    (200, 200, 255), radius=2, draw_type="laser"
                ))

# 例：加速を限定的に使う「タイム・アクセラレーション」
class TimeAcceleration(SpellCard):
    def __init__(self):
        super().__init__("空符「虚空を駆ける不帰の閃光", 3200, (20, 20, 30), 60)
        self.gears = [] # ビット（歯車）の座標管理用

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        
        # --- ギミック1: 「時を刻む歯車ビット」 (画面の四方にビットを設置) ---
        # 3秒に一度、画面の四隅付近に「歯車」を再配置
        if t % 180 == 0:
            self.gears = [
                (100, 150), (300, 150), # 上部左右
                (100, 450), (300, 450)  # 下部左右
            ]
            # 設置の瞬間にエフェクト（全方位へ火花）
            for gx, gy in self.gears:
                for i in range(8):
                    ang = i * math.pi / 4
                    e_bullets.append(EnemyBullet(gx, gy, ang, 1.0, (200, 200, 255), radius=1))

        # --- ギミック2: 「歯車からの屈折レーザー」 (ビット連動攻撃) ---
        # 設置した歯車から、時計回りに回転しながらナイフを「掃射」する
        if t % 30 == 0:
            for idx, (gx, gy) in enumerate(self.gears):
                # 歯車ごとに回転方向を変えて、複雑な交差を作る
                rot_speed = 0.1 if idx % 2 == 0 else -0.1
                base_ang = (t * rot_speed)
                
                # 歯車1つにつき3方向へ発射
                for i in range(3):
                    ang = base_ang + (i * math.pi * 2 / 3)
                    # 速度が「サインカーブ」を描き、伸び縮みするナイフ
                    speed = 2.0 + math.sin(t * 0.05) * 1.5
                    b = EnemyBullet(gx, gy, ang, speed, (200, 255, 200), radius=2, draw_type="laser")
                    
                    # このナイフは途中で「停止」して「再加速」する
                    b.type = "stutter_knife" 
                    e_bullets.append(b)

        # --- ギミック3: 「中央の巨大な日時計」 (ボス本体からの多層螺旋) ---
        if t % 40 == 0:
            ways = 16 + int(d * 12)
            for i in range(ways):
                # 12時、3時...と時計の目盛りを打つように発射
                ang = (i * math.pi * 2 / ways) + (math.sin(t * 0.01) * 0.5)
                # 銀色(WHITE)と紫(150, 0, 255)を交互に混ぜる
                col = (255, 255, 255) if i % 2 == 0 else (180, 100, 255)
                
                b = EnemyBullet(boss.pos[0], boss.pos[1], ang, 1.5, col, radius=2, draw_type="laser")
                # 加速と逆行を併せ持つ
                b.type = "pendulum_complex"
                e_bullets.append(b)

        # --- 弾の個別ロジックアップデート ---
        for b in e_bullets:
            b_type = getattr(b, "type", None)
            
            # ギミック2：カクカクと止まりながら進むナイフ
            if b_type == "stutter_knife":
                if 40 < b.timer % 80 < 60:
                    b.speed *= 0.8 # 一時減速（停滞）
                elif b.timer % 80 == 61:
                    b.speed = 3.5  # 一気に再加速

            # ギミック3：複雑な往復（ペンデュラム）
            elif b_type == "pendulum_complex":
                # 120フレームかけて、ゆっくり進んで、急激に戻る
                if b.timer % 120 == 60:
                    b.speed = -4.0 # 鋭く逆走
                    b.color = (255, 255, 100) # 逆走中は金色（時計の針）
                elif b.timer % 120 == 0:
                    b.speed = 1.5
                    b.color = b.color # 元の色に戻る

# --- 6. 終焉の熾天使「セラフィム」 ---
class HeavensGate(SpellCard):
    def __init__(self):
        # 背景を深い琥珀色に設定し、金色の弾を際立たせる
        super().__init__("煌符「アイディアル・ホワイトアウトの静寂」", 3600, (40, 30, 0), 60)
        self.aoe_zones = []
        
    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        
        # --- レイヤー1: 「天使の羽衣」 (ボス本体からの曲線) ---
        if t % 90 == 0:
            ways = 6 + int(d * 4)
            for i in range(ways):
                base_ang = i * (math.pi * 2 / ways) + (t * 0.01)
                for j in range(12):
                    ang = base_ang + math.sin(j * 0.2) * 0.4
                    speed = 1.2 + (j * 0.1)
                    col = (255, 255, 250) if j % 2 == 0 else (255, 215, 100)
                    e_bullets.append(EnemyBullet(boss.pos[0], boss.pos[1], ang, speed, col, radius=2))

        # --- レイヤー2: 【新規】ビット起点・多層幾何学「ヘキサ・ゲート」 ---
        # ボスの周囲を回る4つのビットから、異なるタイミングで幾何学模様を放つ
        bit_count = 4
        orbit_radius = 120 + math.sin(t * 0.03) * 30 # ビットの軌道自体が収縮
        for i in range(bit_count):
            # ビットの現在位置
            bit_ang = (t * 0.02) + (i * math.pi * 2 / bit_count)
            bx = boss.pos[0] + math.cos(bit_ang) * orbit_radius
            by = boss.pos[1] + math.sin(bit_ang) * orbit_radius

            # ビットから放たれる「星型」の軌道
            if t % 40 == 0:
                # ビットごとに少し角度をずらした多方向放射
                shoot_ways = 2
                for j in range(shoot_ways):
                    # ビットの回転方向とは逆に回る弾幕
                    sang = bit_ang + (j * math.pi * 2 / shoot_ways) - (t * 0.05)
                    # 速度が時間で変化する「脈動弾」
                    speed = 2.0 + math.sin(t * 0.1) * 0.5
                    e_bullets.append(EnemyBullet(bx, by, sang, speed, (255, 250, 200), radius=3))

        # --- レイヤー3: 「収束する聖印」 (ビット位置への収束) ---
        if t % 120 == 0:
            # ビットの軌道上に光の輪を生成
            for i in range(bit_count):
                bit_ang = (t * 0.02) + (i * math.pi * 2 / bit_count)
                cx = boss.pos[0] + math.cos(bit_ang) * (orbit_radius + 90)
                cy = boss.pos[1] + math.sin(bit_ang) * (orbit_radius + 90)
                
                num = 8
                for j in range(num):
                    ang = j * (math.pi * 2 / num)
                    tx = cx + math.cos(ang) * 60
                    ty = cy + math.sin(ang) * 60
                    # ビット（中心）へ向かって収束
                    to_center = ang + math.pi
                    b = EnemyBullet(tx, ty, to_center, 1.2, (255, 255, 255), radius=2)
                    b.type = "glitter"
                    e_bullets.append(b)

        # --- レイヤー4: 「ゴッド・レイ」 (ビットからの屈折レーザー) ---
        # ボスからではなく、ビットから交差するように放つ
        if t % 40 == 0:
            for i in range(bit_count):
                bit_ang = (t * 0.02) + (i * math.pi * 2 / bit_count)
                bx = boss.pos[0] + math.cos(bit_ang) * orbit_radius
                by = boss.pos[1] + math.sin(bit_ang) * orbit_radius
                
                # 外側へ向かって放たれる細い光
                e_bullets.append(EnemyBullet(bx, by, bit_ang, 5.5, (255, 255, 255), radius=1, draw_type="laser"))
        
        # --- レイヤー5：AoE爆発（シンプル版） ---
        if t % 250 == 0:
            for _ in range(1 + int(d * 2)):
                # 生成を最大10回試行（場所が見つからない場合の無限ループ防止）
                for _attempt in range(10):
                    tx = p_pos[0] if random.random() < 0.6 else random.randint(100, WIDTH-100)
                    ty = p_pos[1] if random.random() < 0.6 else random.randint(100, HEIGHT-100)
                    
                    new_radius = 70 + d * 30
                    
                    # すでに画面にあるAOEとの距離をチェック
                    is_overlapping = False
                    for eb in e_bullets:
                        if getattr(eb, "type", "") == "aoe":
                            # 既存のAOEの半径と新しい半径を足した距離より近いか
                            # 1.2倍などの係数をかけると、少し余裕を持って配置されます
                            dist = math.hypot(eb.pos[0] - tx, eb.pos[1] - ty)
                            if dist < (eb.radius + new_radius) * 0.8: # 0.8倍で少しだけ重ねる（完全に離すなら1.0）
                                is_overlapping = True
                                break
                    
                    # 重なっていなければ生成して試行終了
                    if not is_overlapping:
                        aoe = EnemyBullet(tx, ty, 0, 0, (255, 150, 0), b_type="aoe", radius=new_radius)
                        e_bullets.append(aoe)
                        break

        

class GenesisRay(SpellCard):
    def __init__(self):
        super().__init__("極符「万象を拒絶する虚無の福音", 4000, (5, 0, 15), 99)
        self.bits = []
        for i in range(8):
            self.bits.append({"x": 200, "y": 250, "phase": i * (math.pi / 4)})

    def get_rainbow_color(self, h):
        h = h % 360
        if h < 120: return (255, int(h * 2), 50)
        if h < 240: return (50, 255, int((h - 120) * 2))
        return (int((h - 240) * 2), 50, 255)

    def update(self, boss, p_pos, e_bullets, t):
        d = self.get_danger_ratio()
        
        # --- 1. ビット：追従速度を落とし、逃げ道を作る ---
        for i, bit in enumerate(self.bits):
            # 修正：半径を少し広げ(220->250)、追従速度を(0.04->0.02)に半減
            radius = 250 - d * 50
            target_x = p_pos[0] + math.cos(t * 0.03 + bit["phase"]) * radius
            target_y = p_pos[1] + math.sin(t * 0.03 + bit["phase"]) * radius
            
            bit["x"] += (target_x - bit["x"]) * 0.02 # 追従を遅くして、振り切りやすく
            bit["y"] += (target_y - bit["y"]) * 0.02

            # 弾幕：発射間隔をさらに広げる (16 -> 24)
            if t % 24 == 0:
                ang = math.atan2(bit["y"] - boss.pos[1], bit["x"] - boss.pos[0]) + math.pi/2
                ang += math.sin(t * 0.05) * 0.2
                hue = (t * 0.5 + i * 45) % 360
                color = self.get_rainbow_color(hue)
                
                # 修正：初速を少し抑える (1.2 -> 1.0)
                b = EnemyBullet(bit["x"], bit["y"], ang, 1.0 + d * 1.0, color, radius=2)
                b.type = "gravity_light"
                e_bullets.append(b)

        # --- 2. 核心ギミック： 重力の影響範囲を限定する ---
        gravity_cycle = t % 240
        for b in e_bullets:
            if getattr(b, "type", None) == "gravity_light":
                if 0 < gravity_cycle < 120:
                    b.pos[0] += 0.5 # 流れる速度をマイルドに (0.8 -> 0.5)
                else:
                    b.pos[0] -= 0.5
                
                # 修正：重力の影響を受ける距離を短く(200->150)し、引き寄せ力を弱める
                dist_p = math.hypot(p_pos[0] - b.pos[0], p_pos[1] - b.pos[1])
                if dist_p < 150:
                    acc_p = math.atan2(p_pos[1] - b.pos[1], p_pos[0] - b.pos[0])
                    # 反発力を少し強めて、弾が勝手に避けてくれる感覚を出す
                    force = math.sin(t * 0.05) * 0.4 * d
                    b.pos[0] += math.cos(acc_p) * force
                    b.pos[1] += math.sin(acc_p) * force

        # --- 3. ボス本体： 「次元の楔」を「見せる」 ---
        if t % 120 == 0: # 間隔を長く (100 -> 120)
            for _ in range(1): # 数を減らす (2 -> 1)
                side = random.choice([0, WIDTH])
                # 修正：弾速を大幅に落とす (5.0 -> 3.0) 代わりに、少し太くして視認性アップ
                b = EnemyBullet(side, random.randint(0, HEIGHT), 
                               math.atan2(p_pos[1]-random.randint(0, HEIGHT), p_pos[0]-side), 
                               3.0, WHITE, radius=2, draw_type="laser")
                e_bullets.append(b)
        
        # --- 4. 【追加】聖印展開：幾何学の檻（ジオメトリック・プリズン） ---
        # 160フレームごとに、ビットがその場で幾何学模様を描きながら弾を放つ
        if t % 220 == 0:
            for i, bit in enumerate(self.bits):
                # ビットごとに頂点数を変えず、3か4に固定して安置を増やす
                vertices = 3 if i % 2 == 0 else 4 
                for v in range(vertices):
                    # 発射角度
                    base_ang = (t * 0.01) + (v * math.pi * 2 / vertices)
                    
                    # 辺を構成する弾の数を減らす (5 -> 3)
                    num_edge_bullets = 3
                    for j in range(num_edge_bullets):
                        # 初速をさらに落とす (1.2 -> 0.8)
                        speed = 0.8 + (j * 0.2)
                        
                        hue = (t * 0.3 + i * 30 + v * 20) % 360
                        color = self.get_rainbow_color(hue)
                        
                        # 弾のサイズを小さくして、隙間を通リやすくする (radius 3 -> 2)
                        b = EnemyBullet(bit["x"], bit["y"], base_ang, speed, color, radius=2)
                        b.type = "geometric" 
                        e_bullets.append(b)

        # --- 5. 【調整】中央からの「福音の波動」 ---
        # 画面中央からの弾幕を、より「見てから避けられる」ように修正
        if t % 100 == 0: # 間隔を長く (80 -> 100)
            # 弾数を固定し、danger_ratio(d) による増加を抑える
            ways = 8 + int(d * 4) 
            for i in range(ways):
                ang = i * (math.pi * 2 / ways) + math.sin(t * 0.02)
                # 色を薄い黄色に変更して、重力弾（虹色）と混同しないようにする
                color = (255, 255, 200) 
                
                # 加速を削除し、低速で一定に流れるようにする
                b = EnemyBullet(boss.pos[0], boss.pos[1], ang, 0.7, color, radius=2)
                # b.accel = 0.01 # 削除：加速があると予測しづらいため
                e_bullets.append(b)
            
BOSS_DATA = {
    "flare": {"img": load_asset("boss2.png", 100, RED), "spells": [SolarFlareBurst, ProminenceX]},
    "spirit": {"img": load_asset("boss1.png", 100, BLUE), "spells": [MilkyWay, GhostlyOrbit]},
    "leviathan": {"img": load_asset("boss3.png", 110, BLUE), "spells": [AquaPressure, LeviathanRay]},
    "helios": {"img": load_asset("boss4.png", 120, GOLD), "spells": [PhotonSmasher, SupernovaGigant]},
    "nefer":     {"img": load_asset("boss5.png", 100, CYAN),    "spells": [RainbowOverTheRainbow, CrystalizeAbsoluteZero]},
    "eclipse":   {"img": load_asset("boss6.png", 100, PURPLE),"spells": [GravityBlackHole, MoonCraterHopping]},
    "raigo":     {"img": load_asset("boss7.png", 100, YELLOW),  "spells": [ThunderBoltStrike, Tetravortex]},
    "gaia":      {"img": load_asset("boss8.png", 110, GREEN),    "spells": [SquareDistraction, GeometricTectonics]},
    "chronos":   {"img": load_asset("boss9.png", 120, WHITE),  "spells": [StopWatchParadox, TimeAcceleration]},
    "seraphim":  {"img": load_asset("boss10.png", 130, GOLD),   "spells": [HeavensGate, GenesisRay]}
}
BOSS_ORDER = ["leviathan", "helios", "nefer" ,"flare", "spirit" , "eclipse", "raigo", "gaia", "chronos","seraphim"]

class Enemy:

    def __init__(self, x, type_id, boss_key=None):
        self.type_id, self.boss_key, self.pos = type_id, boss_key, [float(x), -100.0]
        self.timer, self.radius, self.is_spell = 0, 50, False # 最初からボス半径に
        self.inv, self.normal_pattern_idx = 0, 0
        
        # ボスラッシュ前提なので type_id == "boss" の処理に集約
        self.data = BOSS_DATA[boss_key]
        self.image = self.data["img"]
        self.spell_index = 0
        self._load_phase()

    def _load_phase(self):
        # 1. BOSS_DATAからスペルカードクラスを取得
        spell_class = self.data["spells"][self.spell_index]
        
        # 2. クラスをインスタンス化（引数なしで実行）
        # 各スペルクラスの __init__ 内で定義された名前やHPが self.current_spell に格納されます
        self.current_spell = spell_class()
        
        # 3. スペルカードか通常攻撃かに応じてHPと名前をセット
        if self.is_spell:
            self.max_hp = self.current_spell.max_hp
            self.phase_name = self.current_spell.name
        else:
            # 通常攻撃（非スペル）時のHP設定（例：700）
            self.max_hp = 700
            self.phase_name = ""
            
        self.hp = self.max_hp
        self.timer = 0
        self.inv = 70 # 出現時/切り替え時の無敵時間
        self.normal_pattern_idx = random.randint(0, 2)
        
        

    def update(self, p_pos, e_bullets):
        self.timer += 1
        
        if self.pos[1] < 150:
            self.pos[1] += 2
            return True # 降りている間は無敵＆攻撃なし
        
        # --- ボス攻撃ロジック ---
        if not self.is_spell:
            # 通常時は少し左右に揺れる
            self.pos[0] = WIDTH//2 + math.sin(self.timer*0.02)*150
            self.pos[1] = 150
            self._execute_normal_pattern(p_pos, e_bullets)
        else:
            # スペルカード時は中央で集中
            self.pos[0], self.pos[1] = WIDTH//2, 150
            self.current_spell.update(self, p_pos, e_bullets, self.timer)
            # 制限時間切れチェック
            if self.current_spell.update_timer(): self.hp = 0
            
        # --- フェーズ終了判定 ---
        if self.hp <= 0:
            was_spell = self.is_spell 
            if not was_spell: 
                self.is_spell = True
                self._load_phase()
                return "NORMAL_END"
            else:
                self.spell_index += 1
                self.is_spell = False
                if self.spell_index < len(self.data["spells"]):
                    self._load_phase()
                    return "SPELL_END"
                else:
                    return "BOSS_KILLED" 
        return True

    def _execute_normal_pattern(self, p_pos, e_bullets):
        t = self.timer
        if self.normal_pattern_idx == 0:
            if t % 25 == 0:
                for i in range(16):
                    ang = i * (math.pi / 8) + t * 0.02
                    e_bullets.append(EnemyBullet(self.pos[0], self.pos[1], ang, 3.5, GOLD))
        elif self.normal_pattern_idx == 1:
            if t % 6 == 0 and (t % 60) < 30:
                ang = math.atan2(p_pos[1]-self.pos[1], p_pos[0]-self.pos[0])
                e_bullets.append(EnemyBullet(self.pos[0], self.pos[1], ang, 6, CYAN))
        elif self.normal_pattern_idx == 2:
            if t % 4 == 0:
                e_bullets.append(EnemyBullet(self.pos[0], self.pos[1], t*0.1, 4, LIME))
                e_bullets.append(EnemyBullet(self.pos[0], self.pos[1], -t*0.1, 4, PURPLE))

    def draw(self):
        screen.blit(self.image, self.image.get_rect(center=self.pos))
        if self.type_id == "boss":
            r, ratio = 85, max(0, self.hp / self.max_hp)
            color = RED if self.is_spell else GOLD
            pygame.draw.arc(screen, color, (self.pos[0]-r, self.pos[1]-r, r*2, r*2), math.pi/2, math.pi/2 + (math.pi*2 * ratio), 5)


async def title_screen():
    selected = 0
    menu_items = ["START GAME", "RANKING", "QUIT"]
    f_title = pygame.font.SysFont("arial", 80, bold=True)
    f_menu = pygame.font.SysFont("arial", 40)
    f_info = pygame.font.SysFont("arial", 20)
    
    # 最新のランキングを読み込んで1位を表示用にする
    ranking = load_ranking()
    top_score = ranking[0]['score'] if ranking else 0
    top_name = ranking[0]['name'] if ranking else "None"

    while True:
        screen.fill((10, 10, 30)) # 深い紺色の背景
        
        # --- タイトルロゴ ---
        title_surf = f_title.render("GEMINI SHOOTER", True, (255, 255, 255))
        screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 150))
        
        # --- ハイスコア情報 ---
        hs_info = f_info.render(f"TOP RECORD: {top_score:,} by {top_name}", True, (255, 215, 0))
        screen.blit(hs_info, (WIDTH//2 - hs_info.get_width()//2, 250))

        # --- メニュー選択 ---
        for i, item in enumerate(menu_items):
            color = (255, 255, 255) if i == selected else (100, 100, 100)
            if i == selected:
                # 選択中のアイテムを少し光らせる演出
                item_text = f"> {item} <"
            else:
                item_text = item
                
            surf = f_menu.render(item_text, True, color)
            screen.blit(surf, (WIDTH//2 - surf.get_width()//2, 400 + i * 60))

        # --- 操作説明 ---
        guide = f_info.render("UP/DOWN: Select  ENTER: Confirm", True, (150, 150, 150))
        screen.blit(guide, (WIDTH//2 - guide.get_width()//2, HEIGHT - 50))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(menu_items)
                    # se_select.play() # SEがあればここで鳴らす
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(menu_items)
                if event.key == pygame.K_RETURN:
                    # se_confirm.play()
                    if selected == 0: return "START"
                    if selected == 1: 
                        # ランキング画面を一時的に表示（後述）
                        await show_ranking_only()
                    if selected == 2:
                        pygame.quit(); sys.exit()
                
               

        await asyncio.sleep(0)
        clock.tick(60)

async def show_ranking_only():
    """ランキングのみを表示する専用画面"""
    f_title = pygame.font.SysFont("arial", 50, bold=True)
    f_rank = pygame.font.SysFont("monospace", 30) # 等幅フォントで整列
    f_guide = pygame.font.SysFont("arial", 25)
    
    while True:
        screen.fill((10, 10, 40)) # 少し明るい紺色
        
        # タイトル描画
        title_surf = f_title.render("TOP 5 RANKING", True, (255, 215, 0))
        screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 80))
        
        # データのロード
        ranking = load_ranking()
        
        # ランキングの描画
        for i in range(5):
            y_pos = 200 + i * 50
            if i < len(ranking):
                entry = ranking[i]
                name = entry['name'][:8].ljust(8)
                score = f"{entry['score']:,}".rjust(12)
                color = (255, 255, 255) if i > 0 else (255, 215, 0)
                line = f"{i+1}. {name} {score}"
            else:
                color = (100, 100, 100)
                line = f"{i+1}. --------            0"
            
            rank_surf = f_rank.render(line, True, color)
            screen.blit(rank_surf, (WIDTH//2 - rank_surf.get_width()//2, y_pos))

        # 操作説明
        guide_surf = f_guide.render("Press [ESC] or [ENTER] to Return", True, (200, 200, 200))
        screen.blit(guide_surf, (WIDTH//2 - guide_surf.get_width()//2, 500))

        

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                # 戻る操作
                if event.key in [pygame.K_ESCAPE, pygame.K_RETURN]:
                    return 
                

        await asyncio.sleep(0)
        clock.tick(60)

async def game_over_screen(final_score, high_score, retry_count, ranking=None):
    # rankingが渡されなかった場合のフォールバック
    if ranking is None:
        ranking = []

    f_large = pygame.font.SysFont("arial", 60, bold=True)
    f_small = pygame.font.SysFont("arial", 30)
    f_reset = pygame.font.SysFont("arial", 20, bold=True)
    f_score = pygame.font.SysFont("arial", 45)
    f_record = pygame.font.SysFont("arial", 40, bold=True)
    f_rank = pygame.font.SysFont("monospace", 24) # 等幅フォントで綺麗に整列
    
    is_new_record = any(entry['score'] == final_score for entry in ranking[:1])
    blink_timer = 0
    reset_hold_timer = 0
    
    while True:
        screen.fill((20, 0, 0)) # 背景色
        
        # --- 1. GAME OVER & 今回のスコア ---
        txt = f_large.render("GAME OVER", True, RED)
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 60))
        
        score_txt = f_score.render(f"FINAL SCORE: {final_score:,}", True, WHITE)
        screen.blit(score_txt, (WIDTH//2 - score_txt.get_width()//2, 130))

        # NEW RECORD 点滅演出
        if is_new_record:
            blink_timer += 1
            if (blink_timer // 20) % 2 == 0:
                record_surf = f_record.render("NEW RECORD!", True, (255, 255, 0))
                screen.blit(record_surf, (WIDTH//2 - record_surf.get_width()//2, 180))

        # --- 2. ランキング表示セクション ---
        rank_y_start = 240
        rank_title = f_small.render("- TOP 5 RANKING -", True, (200, 200, 200))
        screen.blit(rank_title, (WIDTH//2 - rank_title.get_width()//2, rank_y_start))

        for i in range(5):
            y_pos = rank_y_start + 40 + (i * 35)
            # データの有無で表示を切り替え
            if i < len(ranking):
                entry = ranking[i]
                name_str = entry['name'][:8].ljust(8) # 8文字左詰め
                score_str = f"{entry['score']:,}".rjust(12) # 12文字右詰め
                color = (255, 215, 0) if i == 0 else WHITE # 1位は金色
                
                # 今回のスコアと同じならハイライト（自分の順位を強調）
                if entry['score'] == final_score:
                    pygame.draw.rect(screen, (60, 60, 100), (WIDTH//2-160, y_pos-2, 320, 32))
            else:
                name_str = "--------"
                score_str = "-----------0"
                color = (100, 100, 100)

            rank_line = f_rank.render(f"{i+1}. {name_str} {score_str}", True, color)
            screen.blit(rank_line, (WIDTH//2 - rank_line.get_width()//2, y_pos))

        # --- 3. 操作説明（リトライ回数など） ---
        instruction_y = 500
        if retry_count > 0:
            retry_txt = f_small.render(f"Press [R] to Retry (Remains: {retry_count})", True, WHITE)
        else:
            retry_txt = f_small.render("[NO RETRIES LEFT]", True, (100, 100, 100))
            
        restart_txt = f_small.render("Press [S] to Start from Level 1", True, (0, 255, 255))
        quit_txt = f_small.render("Press [Q] to Quit", True, (150, 150, 150))
        
        screen.blit(retry_txt, (WIDTH//2 - retry_txt.get_width()//2, instruction_y))
        screen.blit(restart_txt, (WIDTH//2 - restart_txt.get_width()//2, instruction_y + 40))
        screen.blit(quit_txt, (WIDTH//2 - quit_txt.get_width()//2, instruction_y + 80))
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_x]:
            reset_hold_timer += 1
            # ゲージの描画
            bar_width = min(200, reset_hold_timer * 1.2) # 3秒弱で満タン
            pygame.draw.rect(screen, (100, 0, 0), (WIDTH//2 - 100, HEIGHT - 50, 200, 10))
            pygame.draw.rect(screen, (255, 0, 0), (WIDTH//2 - 100, HEIGHT - 50, bar_width, 10))
            
            reset_msg = f_reset.render("HOLDING [X] TO RESET RANKING...", True, RED)
            screen.blit(reset_msg, (WIDTH//2 - reset_msg.get_width()//2, HEIGHT - 80))
            
            if reset_hold_timer >= 180: # 60fps * 3秒
                ranking = reset_ranking()
                reset_hold_timer = 0
                print("Ranking Reset by User")
        else:
            reset_hold_timer = 0
            # 通常時のガイド表示
            guide_txt = f_reset.render("Hold [X] to Reset Ranking", True, (100, 100, 100))
            screen.blit(guide_txt, (WIDTH//2 - guide_txt.get_width()//2, HEIGHT - 40))
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "QUIT", high_score
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and retry_count > 0: return "RETRY", high_score
                if event.key == pygame.K_s: return "RESTART", high_score
                if event.key == pygame.K_q: return "QUIT", high_score
                
        await asyncio.sleep(0)
        clock.tick(60)

# --- 5. メインロジック ---
async def game_main():
    global lives, score, next_extend_score,current_boss_index
    
    f_ui = pygame.font.SysFont("msgothic", 20, bold=True)
    f_msg = pygame.font.SysFont("arial", 40, bold=True)
    
    retry_level = 1
    high_score = 0
    frame = 0
    debug_mode = False
    
    def draw_ui(player, boss_obj, announcement, debug_mode):
        # スコア
        screen.blit(f_ui.render(f"SCORE: {player['score']}", True, WHITE), (10, 10))
        # 残機・ボム
        for i in range(player["lives"]): screen.blit(IMG_LIFE, (20+i*30, HEIGHT-60))
        for i in range(player["bombs"]): screen.blit(IMG_BOMB, (20+i*30, HEIGHT-30))
        
        # ボス情報
        if boss_obj and boss_obj.phase_name:
            txt = f_ui.render(boss_obj.phase_name, True, WHITE)
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 50))
            if boss_obj.is_spell:
                sec = boss_obj.current_spell.timer // 60
                color = RED if sec < 10 else WHITE
                screen.blit(f_ui.render(f"TIME: {sec:02}", True, color), (WIDTH - 100, 20))
                pygame.draw.rect(screen, (50, 50, 50), (200, 20, 200, 10))
                pygame.draw.rect(screen, color, (200, 20, 200 * (boss_obj.current_spell.timer / boss_obj.current_spell.limit_time), 10))
        
        # アナウンス
        if announcement["timer"] > 0:
            txt_surf = f_msg.render(announcement["text"], True, announcement["color"])
            screen.blit(txt_surf, (WIDTH//2 - txt_surf.get_width()//2, HEIGHT//2 - 50))

        # デバッグモード（仕様維持）
        if debug_mode:
            debug_txt = "DEBUG: [1-0]Jump Boss  [S]Skip  [K]Kill Zako"
            screen.blit(f_ui.render(debug_txt, True, RED), (WIDTH-450, HEIGHT-30))
        else:
            screen.blit(f_ui.render("Z: BOMB / SHIFT: SLOW", True, (150, 150, 150)), (WIDTH-250, HEIGHT-30))

    async def play_death_effect(player_pos):
        """被弾時の爆発・暗転演出"""
        flash = pygame.Surface((WIDTH, HEIGHT))
        flash.fill(WHITE)
        flash.set_alpha(200)
        screen.blit(flash, (0, 0))
        pygame.display.flip()
        await asyncio.sleep(0.1)

        for r in range(5, 150, 15):
            pygame.draw.circle(screen, (255, 50, 0), player_pos, r, 3)
            pygame.display.flip()
            await asyncio.sleep(0.03)
    
    
    def update_player(player, p_bullets, frame):
        keys = pygame.key.get_pressed()
        # 低速移動(Shift)と通常移動
        speed = 0.8 if keys[pygame.K_LSHIFT] else 7
        
        if keys[pygame.K_LEFT] and player["pos"][0] > 20: player["pos"][0] -= speed
        if keys[pygame.K_RIGHT] and player["pos"][0] < WIDTH-20: player["pos"][0] += speed
        if keys[pygame.K_UP] and player["pos"][1] > 20: player["pos"][1] -= speed
        if keys[pygame.K_DOWN] and player["pos"][1] < HEIGHT-20: player["pos"][1] += speed
        
        # メインショット（4フレームに1回）
        if frame % 4 == 0:
            p_bullets.append(PlayerBullet(player["pos"][0], player["pos"][1]-20))
            
        # 無敵時間のカウントダウン
        if player["inv"] > 0:
            player["inv"] -= 1

    while True:  # リトライの大外ループ
        action = await title_screen()
        # 1. ここで「今からやるレベル」をセット
        level = retry_level
        total_score = 0
        
        if action == "START":
            player = {
                "pos": [300, 700],
                "lives": 3,
                "score": total_score,
                "next_extend": 500000,
                "extend_interval": 1000000,
                "bombs": 3,
                "bomb_timer": 0,
                "inv": 0,
                "hit_radius": 3,
                "spell_bonus_active": True,
                "bomb_used": False,
                "retries": 3
            }
            
            enemies, e_bullets, p_bullets, items = [], [], [], []
            announcement = {"text": "", "timer": 0, "color": WHITE}
            cutin_timer, cutin_text, cutin_image = 0, "", None
        
        
            def add_score(amount):
                player["score"] += amount
                while player["score"] >= player["next_extend"]:
                    if player["lives"] < 3:
                        player["lives"] += 1
                    else:
                        player["score"] += 50000 # カンストボーナス
                    
                    # 次の目標スコアを更新
                    player["next_extend"] += player["extend_interval"]
            
            
    
            def spawn():
                idx = (level - 1) % len(BOSS_ORDER) 
                enemies.append(Enemy(300, "boss", BOSS_ORDER[idx]))
        
            spawn()
            game_active = True
            
    
            while game_active:
                
                
                boss_obj = next((e for e in enemies if e.type_id == "boss"), None)
                if boss_obj and boss_obj.is_spell: 
                    boss_obj.current_spell.draw_bg(screen)
                else: 
                    screen.fill(BLACK)
                    screen.blit(IMG_BG, (0,0))
        
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: pygame.quit(); return
                    if event.type == pygame.KEYDOWN:
                        # Dキーでデバッグモード切替
                        if event.key == pygame.K_d: 
                            debug_mode = not debug_mode
                        
                        # Zキーでボム
                        if event.key == pygame.K_z and player["bombs"] > 0 and player["bomb_timer"] == 0:
                            player["bombs"] -= 1
                            player["bomb_timer"], player["inv"] = 120, 180
                            player["bomb_used"] = True
                            
                            player["bomb_origin"] = list(player["pos"])
                            for eb in e_bullets: items.append(Item(eb.pos[0], eb.pos[1], is_collecting=True))
                            e_bullets.clear()
        
                        # --- デバッグモード専用操作 ---
                        if debug_mode:
                            if event.key == pygame.K_k: # 雑魚敵を全滅
                                [setattr(e, 'hp', 0) for e in enemies if e.type_id=="zako"]
                            if event.key == pygame.K_s: # 現在のボス/フェーズをスキップ
                                [setattr(e, 'hp', 0) for e in enemies]
                            
                            # 数字キーで各ボスへダイレクトジャンプ
                            # 1: Flare, 2: Spirit, 3: Leviathan, 4: Helios
                            boss_keys = ["leviathan", "helios", "nefer" ,"eclipse", "raigo", "flare", "spirit" ,  "gaia", "chronos","seraphim"]
                            for i in range(len(boss_keys)):
                                key_name = f"K_{i+1}" if i < 9 else "K_0"
                
                                if event.key == getattr(pygame, key_name):
                                    enemies.clear()      # 現在の敵を消去
                                    e_bullets.clear()
                                    cutin_timer = 0    
                                    # ボスが出るレベルに調整（i=9の時は10体目として計算）
                                    level = (i + 1) * 2
                                    retry_level = level  
                                    enemies.append(Enemy(300, "boss", boss_keys[i]))
                                    print(f"DEBUG: Jump to {boss_keys[i]} (Key: {key_name})")
        
                update_player(player, p_bullets, frame)
                
                if player["bomb_timer"] > 0:
                    player["bomb_timer"] -= 1
                    
                
                if announcement["timer"] > 0:
                    announcement["timer"] -= 1
                    
                    
                # --- 東方風スペルカード演出 ---
                if cutin_timer > 0 and cutin_image:
                    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    alpha = min(255, cutin_timer * 8) 
        
                    # 魔法陣風の円
                    pygame.draw.circle(s, (255, 200, 50, alpha // 4), (WIDTH // 2, HEIGHT // 2), 200, 5)
                    pygame.draw.circle(s, (255, 200, 50, alpha // 6), (WIDTH // 2, HEIGHT // 2), 180, 2)
                    screen.blit(s, (0, 0))
        
                    # --- 立ち絵のアスペクト比維持リサイズ ---
                    orig_rect = cutin_image.get_rect()
                    aspect_ratio = orig_rect.width / orig_rect.height
                    
                    # 高さを400に固定し、横幅を比率に合わせて計算
                    new_h = 400
                    new_w = int(new_h * aspect_ratio)
                    
                    boss_large = pygame.transform.scale(cutin_image, (new_w, new_h))
                    boss_large.set_alpha(min(200, alpha))
                    
                    # スライド演出（右からスッと入る）
                    slide_x = (cutin_timer / 120.0) * 100 
                    # 右端から new_w 分だけ内側に入った位置に表示
                    screen.blit(boss_large, (WIDTH - new_w + 50 + slide_x, 150))
        
                    # --- 3. スペルカード名の帯と文字 ---
                    bar_h = 60
                    bar = pygame.Surface((WIDTH, bar_h), pygame.SRCALPHA)
                    bar.fill((0, 0, 0, 180))
                    screen.blit(bar, (0, HEIGHT - 150))
        
                    sc_font_size = 36
                    if len(cutin_text) > 15: # 文字数が多い場合
                        sc_font_size = 24
                    
                    font_sc = pygame.font.SysFont("msgothic", sc_font_size, bold=True)
                    text_surf = font_sc.render(cutin_text, True, (255, 255, 200))
                    
                    # 表示位置
                    text_x = WIDTH - text_surf.get_width() - 20
                    screen.blit(text_surf, (text_x, HEIGHT - 140))
                    
                    font_sm = pygame.font.SysFont("msgothic", 18)
                    bonus_txt = font_sm.render("", True, (255, 215, 0))
                    screen.blit(bonus_txt, (WIDTH - bonus_txt.get_width() - 20, HEIGHT - 165))
        
                    cutin_timer -= 1
        
                
                # 敵の更新
                # --- 敵の更新と当たり判定 ---
                
                # --- 1. まず全ての弾を「一度だけ」動かし、当たり判定を行う ---
                for pb in p_bullets[:]:
                    # 画面上の全敵(enemies)に対してホーミング＆当たり判定
                    hit_enemy = pb.update(enemies) 
                    
                    if hit_enemy:
                        hit_enemy.hp -= 5
                        add_score(10)
                        if pb in p_bullets: p_bullets.remove(pb)
                        continue # 当たったので次の弾へ
    
                    # 画面外に出た弾を削除
                    if not (-50 < pb.pos[0] < WIDTH+50 and -50 < pb.pos[1] < HEIGHT+50):
                        if pb in p_bullets: p_bullets.remove(pb)
                
                for e in enemies[:]:
                    res = e.update(player["pos"], e_bullets)
                    
                
                    if res in ["NORMAL_END", "SPELL_END", "BOSS_KILLED"]:
                            # 画面上のすべての敵弾をスコアアイテムに変換して吸い込み
                            for eb in e_bullets:
                                items.append(Item(eb.pos[0], eb.pos[1], itype="score", is_collecting=True))
                            e_bullets.clear()
                       
            
                            # --- スペルカード開始時のカットイン設定 ---
                            if res == "NORMAL_END":
                                cutin_timer = 120
                                cutin_text = e.phase_name
                                cutin_image = e.image
                                
                                player["spell_bonus_active"] = True
                                player["bomb_used"] = False
                            
                            
                            # --- 弾をアイテムに変換する条件 ---
                            if res == "NORMAL_END":
                                cutin_timer, cutin_text, cutin_image = 120, e.phase_name, e.image
                                player["spell_bonus_active"], player["bomb_used"] = True, False
            
                            if res in ["SPELL_END", "BOSS_KILLED"]:
                                # --- スペルボーナス判定（2026-02-13仕様維持） ---
                                # 条件：スペル開始から終了まで「被弾していない」かつ「ボムを使っていない」
                                if player["spell_bonus_active"] and not player["bomb_used"]:
                                    
                                    # フルパワー（残機3かつボム3）ならさらに高得点
                                    is_perfect = (player["lives"] >= 3 and player["bombs"] >= 3)
                                    
                                    if is_perfect:
                                        bonus = 500000
                                        msg = "FULL POWER SPELL GET!!"
                                    else:
                                        bonus = 300000
                                        msg = "SPELL BONUS GET!!"
                                    
                                    add_score(bonus)
                                    announcement.update({"text": msg, "color": (255, 215, 0), "timer": 120})
                                else:
                                    # 被弾(spell_bonus_active=False) または ボム使用(bomb_used=True) の場合
                                    announcement.update({"text": "BONUS FAILED...", "color": (200, 100, 100), "timer": 90})
            
                                # 共通：弾をアイテムに変換
                                for eb in e_bullets:
                                    items.append(Item(eb.pos[0], eb.pos[1], itype="score", is_collecting=True))
                                e_bullets.clear()
            
                            if res == "BOSS_KILLED" :
                                add_score(10000)
                                # 撃破アイテムを生成（is_collecting=Trueで吸い込み開始）
                                items.append(Item(e.pos[0], e.pos[1], itype="score", is_collecting=True))
                                if e in enemies: enemies.remove(e)
                                continue
                            
                        
                    
        
                    
        
                
        
                        # --- 敵弾の更新内 ---
                hit_this_frame = False
                for b in e_bullets[:]:
                    b.update(player["pos"], e_bullets)
                    
                    if getattr(b, "is_dead", False):
                        if b in e_bullets: e_bullets.remove(b)
                        continue
                    
                    # 画面外判定
                    if not (-100 < b.pos[0] < WIDTH+100 and -100 < b.pos[1] < HEIGHT+100):
                        if b in e_bullets: e_bullets.remove(b)
                        continue
                    
                    if getattr(b, "type", "") == "aoe":
                        continue
    
                    # 当たり判定
                    dist = math.hypot(b.pos[0] - player["pos"][0], b.pos[1] - player["pos"][1])
                    
                    dist = math.hypot(b.pos[0] - player["pos"][0], b.pos[1] - player["pos"][1])
                    if dist < b.radius * 0.5 + 3:
                        if debug_mode:
                            print(f"[2026-02-13 DEBUG] HIT: {b.type} at {int(b.pos[0])},{int(b.pos[1])}")
                            announcement.update({"text": "DEBUG HIT!!", "color": RED, "timer": 20})
                            if b in e_bullets: e_bullets.remove(b)
                        elif player["inv"] <= 0:
                            hit_this_frame = True
                            
                for it in items[:]:
                    it.update(player["pos"]) # ここで自機に近づく
                    # 取得判定
                    if math.hypot(it.pos[0] - player["pos"][0], it.pos[1] - player["pos"][1]) < 30:
                        if it.itype == "score": add_score(500)
                        elif it.itype == "life": player["lives"] = min(3, player["lives"] + 1)
                        elif it.itype == "bomb": player["bombs"] = min(3, player["bombs"] + 1)
                        items.remove(it)
                    elif it.pos[1] > HEIGHT + 50:
                        items.remove(it)
    
                # 4. 次のレベルへ進む判定（★これが重要）
                if not enemies:
                    level += 1
                    # ボス撃破後のインターバル演出などが必要ならここに追加
                    
                    spawn()
                            
                # --- 被弾処理 ---
                if hit_this_frame:
                    for eb in e_bullets: items.append(Item(eb.pos[0], eb.pos[1], is_collecting=True))
                    e_bullets.clear()
                    
                    if player["lives"] <= 0:
                        await play_death_effect(player["pos"])
                        
                        ranking = load_ranking() 
                        
                        # 2. ランクイン判定と名前入力
                        is_rank_in = len(ranking) < 5 or player["score"] > (ranking[-1]["score"] if ranking else 0)
                        if is_rank_in:
                            new_name = await name_entry_screen(player["score"])
                            ranking = update_ranking(ranking, player["score"], new_name)
                            save_ranking(ranking)
                            high_score = ranking[0]["score"] # 1位をハイスコアに更新
                    
                        # ★ここが重要！ 引数に ranking を追加します
                        choice, _ = await game_over_screen(player["score"], high_score, player["retries"], ranking)
                        
                        if choice == "RETRY":
                            # リトライ回数を1減らす
                            player["retries"] -= 1
                            
                            # 復活処理
                            player["lives"] = 3
                            player["bombs"] = 3
                            player["inv"] = 180
                            player["pos"] = [WIDTH // 2, HEIGHT - 100]
                            continue # ボス戦を継続
                            
                        elif choice == "RESTART":
                            # --- 【修正】最初からやり直すための初期化 ---
                            player["lives"] = 3
                            player["score"] = 0
                            player["retries"] = 3
                            player["bombs"] = 3
                            player["inv"] = 60
                            player["pos"] = [300, 700]
                            
                            # ステージや敵のリストも空にする
                            enemies.clear()
                            e_bullets.clear()
                            p_bullets.clear()
                            items.clear()
                            
                            # 3. 【重要】ステージの進行度を最初に戻す
                            # ステージ進行を管理している変数（frame, stage_timer など）を 0 に！
                            level = 1       # レベルを1に
                            retry_level = 1 # リトライ基準も1に
                            frame = 0       # フレームカウントをリセット
                            
                            # 4. 最初の敵（またはボス）を生成
                            spawn()         # これを呼ばないと誰もいない画面で始まってしまう
                            
                            continue # ループの最初に戻ってゲーム開始！
                            pass
    
                        elif choice == "QUIT":
                            game_active = False
                    else:
                        player["lives"] -= 1
                        player["inv"], player["spell_bonus_active"] = 120, False
    
                # --- 描画セクション（整理済み） ---
                # 背景の描画（boss_objのスペル背景 or 通常背景）
                
                # 1. オブジェクト描画
                for e in enemies: e.draw()
                for eb in e_bullets:
                    if getattr(eb, "type", "") == "aoe":
                        eb.draw() # 半透明Surfaceを使用したdrawメソッド
    
                # 3. 中前面：通常弾・自機弾・アイテム
                # AOEの上、かつ自機の下に重なります
                for eb in e_bullets:
                    if getattr(eb, "type", "") != "aoe":
                        eb.draw()
                
                for pb in p_bullets: pb.draw()
                for it in items: it.draw()
                
                # 2. 自機の描画（無敵点滅対応）
                if (player["inv"] // 5) % 2 == 0:
                    screen.blit(IMG_PLAYER, IMG_PLAYER.get_rect(center=player["pos"]))
                    pygame.draw.circle(screen, WHITE, (int(player["pos"][0]), int(player["pos"][1])), 4)
                    pygame.draw.circle(screen, RED, (int(player["pos"][0]), int(player["pos"][1])), 5, 1)
                    
                if player["bomb_timer"] > 0:
                    # 1. 衝撃波エフェクト（青白い円が広がる）
                    # 進行度 (0.0 ～ 1.0)
                    prog = (120 - player["bomb_timer"]) / 120
                    wave_radius = int(prog * 1200) # 画面端まで広がる
                    
                    # 半透明Surfaceを作成
                    bomb_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    # 輪の透明度を徐々に下げる
                    alpha = max(0, 180 - int(prog * 180))
                    
                    # 衝撃波の「輪」を描画
                    pygame.draw.circle(bomb_surf, (150, 220, 255, alpha), player["bomb_origin"], wave_radius, 15)
                    # 少し内側にもう一本細い輪
                    if wave_radius > 50:
                        pygame.draw.circle(bomb_surf, (200, 255, 255, alpha // 2), player["bomb_origin"], wave_radius - 40, 5)
                    
                    screen.blit(bomb_surf, (0, 0))
    
                    # 2. 画面フラッシュ（発動から20フレーム間だけ画面を白く）
                    if player["bomb_timer"] > 100:
                        f_alpha = int((player["bomb_timer"] - 100) / 20 * 200)
                        flash_surf = pygame.Surface((WIDTH, HEIGHT))
                        flash_surf.fill(WHITE)
                        flash_surf.set_alpha(f_alpha)
                        screen.blit(flash_surf, (0, 0))
    
                draw_ui(player, boss_obj, announcement, debug_mode)
                pygame.display.flip()
                frame += 1
                await asyncio.sleep(0)
                clock.tick(FPS)

if __name__ == "__main__":
    asyncio.run(game_main())