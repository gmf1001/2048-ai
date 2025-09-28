import pygame
import random
import sys

# 初始化pygame
pygame.init()

# 游戏常量
GRID_WIDTH = 10
GRID_HEIGHT = 20
CELL_SIZE = 30
WINDOW_WIDTH = GRID_WIDTH * CELL_SIZE
WINDOW_HEIGHT = GRID_HEIGHT * CELL_SIZE

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# Bug 1: 变量名拼写错误
class TetrisGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("俄罗斯方块")
        self.clock = pygame.time.Clock()
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_piece = self.create_piece()
        self.game_over = False
        
    def create_piece(self):
        # Bug 2: 数组越界 - 试图访问超出范围的索引
        shapes = [
            [[1, 1, 1, 1]],  # I型
            [[1, 1], [1, 1]],  # O型
            [[1, 1, 0], [0, 1, 1]],  # S型
        ]
        shape = shapes[random.randint(0, 5)]  # 错误：索引超出范围
        return {
            'shape': shape,
            'x': GRID_WIDTH // 2,
            'y': 0,
            'color': random.choice([RED, GREEN, BLUE, YELLOW])
        }
    
    def draw_grid(self):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if self.grid[y][x]:
                    pygame.draw.rect(self.screen, WHITE, rect)
                pygame.draw.rect(self.screen, BLACK, rect, 1)
    
    def draw_piece(self):
        piece = self.current_piece
        shape = piece['shape']
        # Bug 3: 缩进错误导致逻辑错误
    for y, row in enumerate(shape):
        for x, cell in enumerate(row):
            if cell:
                rect = pygame.Rect(
                    (piece['x'] + x) * CELL_SIZE,
                    (piece['y'] + y) * CELL_SIZE,
                    CELL_SIZE, CELL_SIZE
                )
                pygame.draw.rect(self.screen, piece['color'], rect)
    
    def move_piece(self, dx, dy):
        # Bug 4: 变量名错误
        self.current_piece['x'] += dx
        self.current_peice['y'] += dy  # 拼写错误：peice应该是piece
        
    def check_collision(self):
        piece = self.current_piece
        shape = piece['shape']
        
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    new_x = piece['x'] + x
                    new_y = piece['y'] + y
                    
                    # Bug 5: 边界检查逻辑错误
                    if (new_x < 0 or new_x > GRID_WIDTH or  # 应该是 >= GRID_WIDTH
                        new_y < 0 or new_y >= GRID_HEIGHT or
                        self.grid[new_y][new_x]):
                        return True
        return False
    
    def place_piece(self):
        piece = self.current_piece
        shape = piece['shape']
        
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    grid_x = piece['x'] + x
                    grid_y = piece['y'] + y
                    # Bug 6: 类型错误 - 将颜色对象存储到网格中
                    self.grid[grid_y][grid_x] = piece['color']  # 应该存储1或True
    
    def clear_lines(self):
        lines_to_clear = []
        for y in range(GRID_HEIGHT):
            if all(self.grid[y]):
                lines_to_clear.append(y)
        
        # Bug 7: 逻辑错误 - 删除行的方式错误
        for line in lines_to_clear:
            del self.grid[line]  # 这会导致索引错乱
            self.grid.insert(0, [0] * GRID_WIDTH)
    
    def run(self):
        while not self.game_over:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.move_piece(-1, 0)
                    elif event.key == pygame.K_RIGHT:
                        self.move_piece(1, 0)
                    elif event.key == pygame.K_DOWN:
                        self.move_piece(0, 1)
            
            # 自动下落
            self.move_piece(0, 1)
            
            if self.check_collision():
                self.move_piece(0, -1)  # 撤销移动
                self.place_piece()
                self.clear_lines()
                self.current_piece = self.create_piece()
                
                if self.check_collision():
                    self.game_over = True
            
            self.screen.fill(BLACK)
            self.draw_grid()
            self.draw_piece()
            pygame.display.flip()
            self.clock.tick(60)

# Bug 8: 缩进错误
if __name__ == "__main__":
game = TetrisGame()  # 缺少缩进
game.run()
