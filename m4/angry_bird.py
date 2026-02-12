import pygame
import math
import random

# 增加注释

# 初始化pygame
pygame.init()

# 游戏常量
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRAVITY = 0.5
GROUND_HEIGHT = 100

# 颜色定义
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)

class Bird:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.radius = 15
        self.color = RED
        self.launched = False
        
    def update(self):
        if self.launched:
            self.x += self.vx
            self.y += self.vy
            self.vy += GRAVITY
            
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

class Pig:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 20
        self.color = GREEN
        self.alive = True
        
    def draw(self, screen):
        if self.alive:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

class Block:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = BROWN
        self.destroyed = False
        
    def draw(self, screen):
        if not self.destroyed:
            pygame.draw.rect(screen, self.color, 
                           (self.x, self.y, self.width, self.height))

class Slingshot:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.height = 100
        self.width = 10
        
    def draw(self, screen):
        pygame.draw.rect(screen, BROWN, (self.x, self.y, self.width, self.height))

# Bug 1: 类名拼写错误
class AngryBirdsGme:  # 应该是 AngryBirdsGame
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("愤怒的小鸟")
        self.clock = pygame.time.Clock()
        
        # 初始化游戏对象
        self.slingshot = Slingshot(100, SCREEN_HEIGHT - GROUND_HEIGHT - 100)
        self.birds = [Bird(120, SCREEN_HEIGHT - GROUND_HEIGHT - 50)]
        self.pigs = [
            Pig(600, SCREEN_HEIGHT - GROUND_HEIGHT - 20),
            Pig(650, SCREEN_HEIGHT - GROUND_HEIGHT - 20),
        ]
        self.blocks = [
            Block(580, SCREEN_HEIGHT - GROUND_HEIGHT - 60, 20, 60),
            Block(620, SCREEN_HEIGHT - GROUND_HEIGHT - 60, 20, 60),
            Block(660, SCREEN_HEIGHT - GROUND_HEIGHT - 60, 20, 60),
        ]
        
        self.dragging = False
        self.launch_power = 0
        self.launch_angle = 0
        self.game_over = False
        
    def handle_mouse_events(self, mouse_pos, mouse_pressed):
        if len(self.birds) > 0 and not self.birds[0].launched:
            bird = self.birds[0]
            
            if mouse_pressed:
                # Bug 2: 数学计算错误 - 角度计算有误
                dx = mouse_pos[0] - bird.x
                dy = mouse_pos[1] - bird.y
                self.launch_angle = math.atan2(dy, dx)  # 错误：应该考虑方向
                self.launch_power = min(math.sqrt(dx*dx + dy*dy) / 5, 20)
                self.dragging = True
            else:
                if self.dragging:
                    # 发射小鸟
                    bird.vx = self.launch_power * math.cos(self.launch_angle)
                    bird.vy = self.launch_power * math.sin(self.launch_angle)
                    bird.launched = True
                    self.dragging = False
    
    def check_collisions(self):
        if len(self.birds) == 0:
            return
            
        bird = self.birds[0]
        
        # Bug 3: 碰撞检测逻辑错误
        for pig in self.pigs:
            if pig.alive:
                distance = math.sqrt((bird.x - pig.x)**2 + (bird.y - pig.y)**2)
                if distance < bird.radius + pig.radius:
                    pig.alive = False
                    self.birds.remove(bird)  # 错误：直接删除可能导致索引问题
        
        # 检查与方块的碰撞
        for block in self.blocks:
            if not block.destroyed:
                # Bug 4: 简化的碰撞检测错误
                if (bird.x > block.x and bird.x < block.x + block.width and
                    bird.y > block.y and bird.y < block.y + block.height):
                    block.destroyed = True
                    bird.vx *= -0.5  # 反弹
                    bird.vy *= -0.5
        
        # Bug 5: 地面碰撞检测错误
        if bird.y > SCREEN_HEIGHT - GROUND_HEIGHT:
            bird.y = SCREEN_HEIGHT - GROUND_HEIGHT  # 错误：没有考虑小鸟半径
            bird.vy = 0
            bird.vx *= 0.8  # 摩擦力
    
    def update_game(self):
        # Bug 6: 列表修改时的迭代错误
        for bird in self.birds:
            bird.update()
            
            # 移除飞出屏幕的小鸟
            if bird.x > SCREEN_WIDTH or bird.y > SCREEN_HEIGHT:
                self.birds.remove(bird)  # 错误：在迭代中修改列表
        
        self.check_collisions()
        
        # Bug 7: 胜利条件判断错误
        all_pigs_dead = True
        for pig in self.pigs:
            if pig.alive == True:  # 应该用 is 或直接 if pig.alive
                all_pigs_dead = False
                break
        
        if all_pigs_dead:
            print("胜利！")
            self.game_over = True
        
        # Bug 8: 类型错误
        if len(self.birds) == "0":  # 错误：字符串比较而非数字
            print("游戏结束！")
            self.game_over = True
    
    def draw_trajectory(self):
        if self.dragging and len(self.birds) > 0:
            bird = self.birds[0]
            # Bug 9: 轨迹预测计算错误
            for i in range(10):
                t = i * 0.5
                # 错误的物理公式
                x = bird.x + self.launch_power * math.cos(self.launch_angle) * t
                y = bird.y + self.launch_power * math.sin(self.launch_angle) * t + 0.5 * GRAVITY * t * t
                
                if x < SCREEN_WIDTH and y < SCREEN_HEIGHT:
                    pygame.draw.circle(self.screen, WHITE, (int(x), int(y)), 3)
    
    def draw(self):
        self.screen.fill(BLUE)  # 天空
        
        # 绘制地面
        pygame.draw.rect(self.screen, GREEN, 
                        (0, SCREEN_HEIGHT - GROUND_HEIGHT, SCREEN_WIDTH, GROUND_HEIGHT))
        
        # 绘制弹弓
        self.slingshot.draw(self.screen)
        
        # 绘制小鸟
        for bird in self.birds:
            bird.draw(self.screen)
        
        # 绘制猪
        for pig in self.pigs:
            pig.draw(self.screen)
        
        # 绘制方块
        for block in self.blocks:
            block.draw(self.screen)
        
        # 绘制轨迹
        self.draw_trajectory()
        
        pygame.display.flip()
    
    def run(self):
        running = True
        while running and not self.game_over:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_events(pygame.mouse.get_pos(), True)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_events(pygame.mouse.get_pos(), False)
            
            self.update_game()
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()

# Bug 10: 缩进和实例化错误
if __name__ == "__main__":
try:
    game = AngryBirdsGme()  # 错误：类名拼写错误
    game.run()
except Exception as e:
        print(f"游戏出错: {e}")
