import pygame
import math
import random
import sys

pygame.init()

# --- Screen setup ---
WIDTH, HEIGHT = 800, 600
ENV_WIDTH = 600
PANEL_WIDTH = WIDTH - ENV_WIDTH

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("RL Car Obstacle Avoidance Demo")

BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
GREEN  = (0, 180, 0)
BLUE   = (0, 0, 255)
RED    = (220, 0, 0)
GRAY   = (180, 180, 180)
YELLOW = (255, 255, 0)

font = pygame.font.SysFont(None, 24)
big_font = pygame.font.SysFont(None, 32)

car_radius = 6
speed = 3

def create_obstacles():
    obs_list = []
    for _ in range(30):
        x = random.randint(20, ENV_WIDTH - 40)
        y = random.randint(20, HEIGHT - 40)
        obs_list.append(pygame.Rect(x, y, 25, 25))
    return obs_list

def get_free_start(obstacles):
    """Find a starting position not inside any obstacle."""
    while True:
        x = random.randint(60, ENV_WIDTH - 60)
        y = random.randint(60, HEIGHT - 60)
        car_rect = pygame.Rect(x - car_radius, y - car_radius,
                               car_radius * 2, car_radius * 2)
        if not any(o.colliderect(car_rect) for o in obstacles):
            return [x, y]

def reset_episode():
    global car_pos, car_angle, obstacles, reward, current_action
    obstacles = create_obstacles()
    car_pos   = get_free_start(obstacles)
    car_angle = 0
    reward = 0.0
    current_action = "Go Straight"

def cast_sensor(angle_deg, max_dist=250, step=3):
    ang = math.radians(angle_deg)
    for d in range(0, max_dist, step):
        x = car_pos[0] + d * math.cos(ang)
        y = car_pos[1] - d * math.sin(ang)

        if x < 0 or x >= ENV_WIDTH or y < 0 or y >= HEIGHT:
            return d, (int(x), int(y))

        pt = (x, y)
        for obs in obstacles:
            if obs.collidepoint(pt):
                return d, (int(x), int(y))
    return max_dist, (int(x), int(y))

# ---- Simple rule-based controller (fake "policy") ----
def decide_action(dists):
    """
    dists = [dist_left, dist_front, dist_right]
    returns: "Turn Left" / "Turn Right" / "Go Straight"
    """
    left, front, right = dists
    danger_front = 80
    danger_side  = 50

    # If something very close on the sides, avoid it strongly
    if left < danger_side and right >= left:
        return "Turn Right"
    if right < danger_side and left >= right:
        return "Turn Left"

    # If obstacle in front, choose the more open side
    if front < danger_front:
        if left > right:
            return "Turn Left"
        else:
            return "Turn Right"

    # Otherwise just go straight
    return "Go Straight"

reset_episode()

clock = pygame.time.Clock()
running = True

while running:
    # --- Events (only close button) ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # ---- Sense environment BEFORE moving ----
    sensor_angles = [car_angle + 45, car_angle, car_angle - 45]
    sensor_names  = ["Distance left", "Distance front", "Distance right"]
    dists = [cast_sensor(a)[0] for a in sensor_angles]

    # ---- Decide action automatically ----
    turned = False
    action = decide_action(dists)

    if action == "Turn Left":
        car_angle += 4
        turned = True
    elif action == "Turn Right":
        car_angle -= 4
        turned = True

    current_action = action

    if turned:
        reward -= 0.1     # turning penalty

    # Move car forward
    car_pos[0] += speed * math.cos(math.radians(car_angle))
    car_pos[1] -= speed * math.sin(math.radians(car_angle))

    # --- Collision / boundary check ---
    crashed = False
    if (car_pos[0] - car_radius < 0 or
        car_pos[0] + car_radius > ENV_WIDTH or
        car_pos[1] - car_radius < 0 or
        car_pos[1] + car_radius > HEIGHT):
        crashed = True
    else:
        car_rect = pygame.Rect(car_pos[0]-car_radius,
                               car_pos[1]-car_radius,
                               car_radius*2, car_radius*2)
        for obs in obstacles:
            if obs.colliderect(car_rect):
                crashed = True
                break

    if crashed:
        reward -= 100
        pygame.time.delay(500)
        reset_episode()

    reward += 1  # survival reward

    # --- DRAW ---
    screen.fill(BLACK)
    pygame.draw.rect(screen, GREEN, (ENV_WIDTH, 0, PANEL_WIDTH, HEIGHT))

    # Obstacles
    for obs in obstacles:
        pygame.draw.rect(screen, WHITE, obs)

    # Recompute sensors for drawing (after movement)
    dists_draw = []
    for ang in sensor_angles:
        dist, hit_pt = cast_sensor(ang)
        dists_draw.append(dist)
        pygame.draw.line(screen, GRAY, car_pos, hit_pt, 1)
        pygame.draw.circle(screen, YELLOW, hit_pt, 2)

    # Car
    pygame.draw.circle(screen, WHITE,
                       (int(car_pos[0]), int(car_pos[1])), car_radius)

    # --- UI panel ---
    panel_x = ENV_WIDTH + 10
    y = 20
    text = big_font.render("Sensors", True, WHITE)
    screen.blit(text, (panel_x, y))
    y += 30

    max_sensor = 250
    bar_width = PANEL_WIDTH - 40
    bar_height = 18

    for name, dist in zip(sensor_names, dists_draw):
        label = font.render(name, True, WHITE)
        screen.blit(label, (panel_x, y))
        pygame.draw.rect(screen, WHITE,
                         (panel_x, y+20, bar_width, bar_height), 1)
        norm = 1.0 - min(dist, max_sensor) / max_sensor
        bar_len = int((bar_width-2) * norm)
        bar_color = RED if norm > 0.7 else BLUE
        pygame.draw.rect(screen, bar_color,
                         (panel_x+1, y+21, bar_len, bar_height-2))
        y += 50

    y += 10
    text = big_font.render("Actions", True, WHITE)
    screen.blit(text, (panel_x, y))
    y += 30

    actions = ["Turn Left", "Go Straight", "Turn Right"]
    for act in actions:
        rect = pygame.Rect(panel_x, y, bar_width, bar_height)
        pygame.draw.rect(screen, WHITE, rect, 1)
        if act == current_action:
            pygame.draw.rect(screen, BLUE, rect)
        label = font.render(act, True, WHITE)
        screen.blit(label, (panel_x+5, y+2))
        y += 30

    y += 10
    rew_text = big_font.render(f"Reward: {int(reward)}", True, WHITE)
    screen.blit(rew_text, (panel_x, y))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
