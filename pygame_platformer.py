import pygame as pg
import numpy as np
import cv2
import requests
import json
import datetime
import threading
pg.init()

# 객체를 생성하는 클래스 정의
class Player:
    def __init__(self, image_path, direction, move_speed, jump_power):
        self.normal_img = change_image_size(pg.image.load(image_path), 2) # 이미지 로드
        self.flip_img = pg.transform.flip(self.normal_img, True, False) # 반전된 이미지
        self.flip = False # 반전 여부
        self.image = self.normal_img # 현재 이미지
        self.direction = direction # 보고있는 방향
        self.move_speed = move_speed # 이동속도
        self.init_jump_power = jump_power # 초기 점프력

        self.width = self.image.get_width() # 이미지 너비
        self.height = self.image.get_height() # 이미지 높이
        self.jump_power = self.init_jump_power # 현재 점프력
        self.gravity_acc = 0 # 중력 가속도
        self.jumping = False # 점프중인 상태
        self.on_foothold = False # 발판 위에 닿았는지 여부
        self.move_right = False # 오른쪽 방향키 눌림 여부
        self.move_left = False # 왼쪽 방향키 눌림 여부
        self.x, self.y = 0, 0 # 현재 위치
        self.pull_x, self.pull_y = 0, 0 # 평행이동할 수치(x축, y축의 깃발과 떨어진 거리)
    
    def moving_right(self): # 우측 이동 기능
        player_rect = collision_rect(self.image, self.x + self.move_speed, self.y)
        object_left_tangent = check_collision(CURR_MAP.foothold_layer, player_rect, part="right")
        
        # 플레이어가 우측으로 충돌중이 아니고, 맵 우측 끝부분 보다 안쪽에 있으면
        map_end_x = read_coordinate(CURR_MAP.data_indices, -1, -1)[0]
        map_end_x += CURR_MAP.grid_width
        if self.x < map_end_x:
            if not object_left_tangent:
                self.x += self.move_speed # 이동속도 수치만큼 오른쪽으로 이동
            else:
                self.x += (object_left_tangent - self.x - self.width)
        
        if self.direction == "left": # 왼쪽을 보고 있으면
            self.direction = "right"
            if not self.flip:
                self.image = self.flip_img
                self.flip = True
            else:
                self.image = self.normal_img
                self.flip = False
    
    def moving_left(self): # 좌측 이동 기능
        player_rect = collision_rect(self.image, self.x - self.move_speed, self.y)
        object_right_tangent = check_collision(CURR_MAP.foothold_layer, player_rect, part="left")
        
        # 플레이어가 좌측으로 충돌중이 아니고, 맵 좌측 끝부분 보다 멀리 있으면
        if self.x > 0:
            if not object_right_tangent:
                self.x -= self.move_speed # 이동속도 수치만큼 왼쪽으로 이동
            else:
                self.x -= (self.x - object_right_tangent)

        if self.direction == "right": # 플레이어 이미지가 오른쪽을 보고 있으면
            self.direction = "left" # 방향 상태 변경
            if not self.flip:
                self.image = self.flip_img # 이미지 반전
                self.flip = True # 반전 상태로 변경
            else:
                self.image = self.normal_img # 원래 이미지로
                self.flip = False

    def moving_jump(self): # 점프 기능
        player_rect = collision_rect(self.image, self.x, self.y - self.jump_power)
        object_bottom_tangent = check_collision(CURR_MAP.foothold_layer, player_rect, part="top")
        if not object_bottom_tangent:
            self.y -= self.jump_power # 현재 점프력 수치만큼 플레이어를 위로 이동
            self.jump_power -= CURR_MAP.gravity # 점프력 수치를 중력만큼 감소(매 루프마다 뛰어오르는 속도가 서서히 감소)
        else:
            self.y -= (self.y - object_bottom_tangent)
            self.jump_power = 0
        
        if self.jump_power <= 0: # 현재 점프력 수치가 0이하면
            self.jumping = False # 점프 기능 비활성화
            self.on_foothold = False
            self.jump_power = self.init_jump_power # 점프력 수치 초기화

    def apply_gravity(self): # 중력 적용 기능
        self.gravity_acc += CURR_MAP.gravity # 중력 가속도 변수에 중력을 축적(매 루프마다 아래로 떨어지는 속도가 서서히 증가)
        player_rect = collision_rect(self.image, self.x, self.y + self.gravity_acc)
        collision = check_collision(CURR_MAP.foothold_layer, player_rect, part="bottom")
        if not collision:
            self.y += self.gravity_acc # 현재 중력 가속도 수치만큼 플레이어를 아래로 이동
            self.on_foothold = False
        else:
            object, object_top_tangent = collision[0], collision[1]
            self.y += (object_top_tangent - self.y - self.height)
            self.on_foothold = True
            self.gravity_acc = 0 # 중력 가속도 초기화
            if object.direction == "left" or object.direction == "right":
                self.x += object.move_speed
            elif object.direction == "up":
                self.y -= object.move_speed

    def calc_dist_from_flag(self): # 플레이어 위치와 깃발 위치의 거리차 계산
        # 맵을 x축, y축으로 당길 수치(평행이동할 수치, 플레이어 위치를 기준으로 결정한다.)
        # (0, 0) 위치로부터 x축 방향으로는 화면 가로 중간 너비만큼 떨어진 곳에 가상의 '깃발'이 있고,
        # y축 방향으로는 화면 세로 중간 높이만큼 떨어진 곳에 가상의 '깃발'이 있다고 가정
        
        map_end_x, map_end_y = read_coordinate(CURR_MAP.data_indices, -1, -1)
        map_end_x += CURR_MAP.grid_width # 맵 그리드 배열 마지막 x좌표 + 그리드 한 칸
        map_end_y += CURR_MAP.grid_height # 맵 그리드 배열 마지막 y좌표 + 그리드 한 칸

        if self.x >= map_end_x - WINDOW_WIDTH / 2: # 플레이어 위치가 맵 오른쪽 끝에 다다를시
            self.pull_x = map_end_x - WINDOW_WIDTH # 화면 가로 중간너비 만큼만 덜 당기는 수치
        elif self.x >= WINDOW_WIDTH / 2: # 플레이어 위치가 깃발 위치보다 멀리있거나 같으면
            self.pull_x = self.x - WINDOW_WIDTH / 2 # x축을 당길 수치 = 깃발 위치로부터 플레이어 위치까지의 x좌표 차이
        
        if self.y >= map_end_y - WINDOW_HEIGHT / 2: # 플레이어 위치가 맵 아래쪽 끝에 다다를시
            self.pull_y = map_end_y - WINDOW_HEIGHT # 화면 세로 중간높이 만큼만 덜 당기는 수치
        # elif (self.y >= WINDOW_HEIGHT / 2) or (self.y <= WINDOW_HEIGHT / 2):
        elif (self.y >= WINDOW_HEIGHT / 2):
            self.pull_y = self.y - WINDOW_HEIGHT / 2 # y축을 당길 수치 = 깃발 위치로부터 플레이어 위치까지의 y좌표 차이

    # 캐릭터의 키 이벤트 처리 메서드 추가
    def ninja_frog_key_event(self):
        global RUN
        if self == NINJA_FROG:
            for event in pg.event.get(): # 파이게임의 이벤트들 참조
                if event.type == pg.KEYDOWN: # 키보드 키가 눌린 상태일 때
                    if event.key == pg.K_LEFT: # 왼쪽 방향키인 경우
                        self.move_left = True # 왼쪽 이동 기능 활성화
                    elif event.key == pg.K_RIGHT: # 오른쪽 방향키인 경우
                        self.move_right = True # 오른쪽 이동 기능 활성화
                elif event.type == pg.KEYUP: # 키보드 키를 뗀 상태일 때
                    if event.key == pg.K_LEFT: # 왼쪽 방향키인 경우
                        self.move_left = False # 왼쪽 이동 기능 비활성화
                    elif event.key == pg.K_RIGHT: # 오른쪽 방향키인 경우
                        self.move_right = False # 오른쪽 이동 기능 비활성화
                elif event.type == pg.QUIT: # 창 닫기 버튼을 눌러 창을 닫았을 때
                    RUN = False # 루프문 탈출

            keys = pg.key.get_pressed() # 키보드에서 눌린 키들

            # 왼쪽 ALT키 or 스페이스바가 눌려있고, 플레이어가 점프중이 아니고, 발판 위에 있으면
            if (keys[pg.K_LALT] or keys[pg.K_SPACE]) and not self.jumping and self.on_foothold:
                self.jumping = True # 점프 기능 활성화
            
            # <플레이어 이동>
            if self.move_right:
                self.moving_right() # 오른쪽
            elif self.move_left:
                self.moving_left() # 왼쪽

            if self.jumping:
                self.moving_jump() # 점프
            else:
                self.apply_gravity() # 중력

class Map:
    def __init__(self, map_data, name):
        # 텍스트 기반 맵 파일을 읽어와서 데이터를 리스트로 저장
        with open(map_data, 'r') as file:
            data_list = [list(map(int, list(line.strip()))) for line in file] # 2중 리스트

        # 데이터 리스트를 넘파이 배열로 변환
        self.data_arr = np.array(data_list) # 2차원 배열

        # 모든 맵의 고유 속성
        self.name = name
        self.data_indices = np.indices((len(self.data_arr), len(self.data_arr[0]))) # 데이터 인덱스 배열 생성(행 배열, 열 배열)
        self.grid_height, self.grid_width = 1, 1 # 그리드 한 칸의 사이즈
        self.gravity = 1 # 중력
        self.background_image = None # 배경 이미지
        self.bg_x, self.bg_y = 0, 0 # 배경 이미지 위치
        self.init_player_pos = 0, 0 # 플레이어 스폰 위치

        # 비슷한 유형의 오브젝트들끼리 나눠서 리스트에 저장
        self.foothold_layer = []
        self.monster_layer = []
        self.obstacle_layer = []

        # 맵 이름마다 조건을 달아주고 맵을 정의하는 메서드 호출
        if self.name == "seoul":
            self.seoul()
    
    def draw_background(self): # 배경 그리기 기능
        WINDOW.blit(self.background_image, (self.bg_x - CURR_CHAR.pull_x, self.bg_y - CURR_CHAR.pull_y))

    def draw_player(self): # 플레이어 그리기 기능
        # 플레이어의 실제 위치를 (pull_x, pull_y)만큼 평행이동 시키고 플레이어 이미지 그리기
        WINDOW.blit(CURR_CHAR.image, (CURR_CHAR.x - CURR_CHAR.pull_x, CURR_CHAR.y - CURR_CHAR.pull_y))

    # 맵을 정의하는 메서드 추가
    def seoul(self): # 서울맵 정의
        # 발판 이미지 로드
        foothold_image = pg.image.load("img/foothold_2.png")
        foothold_image = change_image_size(foothold_image, 2)

        # 그리드 한 칸의 크기를 발판의 사이즈로 결정
        self.grid_height, self.grid_width = foothold_image.get_height(), foothold_image.get_width()

        # 데이터 인덱스 배열(행 배열, 열 배열)에 그리드 사이즈 적용
        self.data_indices[0] *= self.grid_height
        self.data_indices[1] *= self.grid_width
        
        # 배경 이미지 로드
        background_image = pg.image.load("img/Brown.png")
        end_x, end_y = read_coordinate(self.data_indices, -1, -1) # 데이터 인덱스 배열에서 마지막 행, 마지막 열의 좌표

        # 가로 세로 각각 그리드 한 칸 만큼 더 늘려서 적용(1픽셀 확장)
        self.background_image = pg.transform.scale(background_image, (end_x + self.grid_width, end_y + self.grid_height))

        # 이 맵의 플레이어 초기 위치
        pos_index = np.argwhere(self.data_arr == 9)[0]
        CURR_CHAR.x, CURR_CHAR.y = read_coordinate(self.data_indices, pos_index[0], pos_index[1])

        for i in np.argwhere(self.data_arr):
            row, col = i[0], i[1] # i: 요소의 행렬 인덱스를 담고 있다.(i[0]: 행 인덱스, i[1]: 열 인덱스)
            x, y = read_coordinate(self.data_indices, row, col) # 오브젝트를 배치할 좌표
            
            image = foothold_image
            object_type = None
            direction = None
            move_speed = None
            name = None

            if self.data_arr[row, col] == 1:
                object_type = "static_foothold"
            elif self.data_arr[row, col] == 2:
                object_type = "dynamic_foothold"
                direction = "right"
                move_speed = 3
            elif self.data_arr[row, col] == 3:
                object_type = "dynamic_foothold"
                direction = "up"
                move_speed = 3
            elif self.data_arr[row, col] == 4:
                object_type = "dynamic_foothold"
                direction = "left"
                move_speed = 3
            elif self.data_arr[row, col] == 5:
                image = pg.image.load("img/Goblin.png")
                object_type = "monster"
                direction = "left"
                move_speed = 2
                name = "요괴"
            elif self.data_arr[row, col] == 6:
                image = pg.image.load("img/Rabbit.png")
                object_type = "monster"
                direction = "left"
                move_speed = 3
                name = "토끼"
            
            if object_type == "dynamic_foothold" or object_type == "static_foothold":
                self.foothold_layer.append(Object(image, x, y, object_type, direction, move_speed, name))
            elif object_type == "monster":
                y -= ((y + image.get_height()) - (y + self.grid_height)) # 발판 위에 닿도록 위치변경
                self.monster_layer.append(Object(image, x, y, object_type, direction, move_speed, name))

    # 정의한 맵을 그리는 메서드 추가
    def draw_seoul_map(self): # 서울맵 그리기 기능
        # 발판 그리기
        for foothold in CURR_MAP.foothold_layer:
            if foothold.type == "dynamic_foothold" and (
                foothold.direction == "right" or foothold.direction == "left"):
                if foothold.direction == "right": # 발판의 방향 속성명이 오른쪽일 경우(오른쪽으로 갔다가 되돌아옴)
                    if foothold.x - foothold.init_x >= 3000: # 3000이상을 오른쪽으로 이동했으면
                        foothold.move_speed *= -1 # 방향 전환
                    elif foothold.x < foothold.init_x: # 초기 발판 위치보다 왼쪽에 있을 경우
                        foothold.move_speed *= -1 # 방향 재전환
                elif foothold.direction == "left": # 방향 속성명이 왼쪽일 경우(왼쪽으로 갔다가 되돌아옴)
                    if foothold.init_x - foothold.x >= 3000: # 3000이상을 왼쪽으로 이동했으면
                        foothold.move_speed *= -1 # 방향 전환
                    elif foothold.init_x < foothold.x: # 초기 발판 위치보다 오른쪽에 있을 경우
                        foothold.move_speed *= -1 # 방향 재전환

                foothold.x += foothold.move_speed # 발판의 이동속도 속성값 만큼 수평이동
                player_rect = collision_rect(CURR_CHAR.image, CURR_CHAR.x, CURR_CHAR.y) # 플레이어 충돌영역
                foothold_rect = collision_rect(foothold.image, foothold.x, foothold.y) # 발판 충돌영역
                if player_rect.colliderect(foothold_rect): # 플레이어와 발판이 충돌 했는지
                    if foothold.move_speed > 0: # 플레이어를 왼쪽에서 쳤으면
                        CURR_CHAR.x = foothold_rect.right # 발판의 오른쪽 접선에 배치
                    else: # 오른쪽에서 쳤으면
                        CURR_CHAR.x = foothold_rect.left - CURR_CHAR.width # 왼쪽 접선에 배치
            
            # 발판의 방향 속성명이 위쪽일 경우(위쪽으로 올라갔다가 다시 내려옴)
            elif foothold.type == "dynamic_foothold" and foothold.direction == "up":
                if foothold.init_y - foothold.y >= 1000: # 1000이상을 위쪽으로 이동했으면
                    foothold.move_speed *= -1 # 방향 전환
                elif foothold.init_y < foothold.y: # 초기 발판 위치보다 아래쪽에 있을 경우
                    foothold.move_speed *= -1 # 방향 재전환

                foothold.y -= foothold.move_speed # 발판의 이동속도 속성값 만큼 수직이동
            
            # 발판의 실제 위치를 (pull_x, pull_y)만큼 평행이동 시키고 발판 이미지 그리기
            WINDOW.blit(foothold.image, (foothold.x - CURR_CHAR.pull_x, foothold.y - CURR_CHAR.pull_y))
        
        # 몬스터 그리기
        for monster in CURR_MAP.monster_layer:
            if monster.name == "요괴" or monster.name == "토끼":
                if monster.direction == "left":
                    if monster.init_x - monster.x >= 1000:
                        monster.move_speed *= -1
                        
                        if not monster.flip:
                            monster.image = monster.flip_img
                            monster.flip = True
                        else:
                            monster.image = monster.normal_img
                            monster.flip = False
                        
                    elif monster.init_x < monster.x:
                        monster.move_speed *= -1

                        monster.direction = "left" # 방향 상태 변경
                        if not monster.flip:
                            monster.image = monster.flip_img # 이미지 반전
                            monster.flip = True # 반전 상태로 변경
                        else:
                            monster.image = monster.normal_img # 원래 이미지로
                            monster.flip = False
                
                monster.x += monster.move_speed
                player_rect = collision_rect(CURR_CHAR.image, CURR_CHAR.x, CURR_CHAR.y) # 플레이어 충돌영역
                monster_rect = collision_rect(monster.image, monster.x, monster.y) # 발판 충돌영역
                if player_rect.colliderect(monster_rect):
                    if monster.move_speed > 0:
                        CURR_CHAR.x += 100
                    else:
                        CURR_CHAR.x -= 100
            
            # monster 그리기
            WINDOW.blit(monster.image, (monster.x - CURR_CHAR.pull_x, monster.y - CURR_CHAR.pull_y))

class Object:
    def __init__(self, image, x, y, type=None, direction=None, move_speed=None, name=None):
        self.normal_img = image
        self.flip_img = pg.transform.flip(image, True, False) # 반전된 이미지
        self.image = self.normal_img # 현재 이미지
        self.flip = False # 이미지 반전 여부
        self.init_x, self.init_y = x, y # 초기 좌표
        self.x, self.y = self.init_x, self.init_y # 실시간 좌표
        self.type = type # 타입명
        self.direction = direction # 이동방향
        self.move_speed = move_speed # 이동속도
        self.name = name # 이름

# 함수
def change_image_size(image, size): # 이미지 사이즈 조절
    return pg.transform.scale(image, (image.get_width() * size, image.get_height() * size))

def read_coordinate(data_indices, row, col): # 그리드 배열에 전달받은 값을 인덱싱하여 해당 위치의 좌표를 반환
    return data_indices[1, row, col], data_indices[0, row, col]

def collision_rect(img, x, y): # 전달받은 이미지와 좌표로 충돌 영역 정의(히트박스)
    return pg.Rect(x, y, img.get_width(), img.get_height())

def check_collision(object_layer, standard_rect, part): # 충돌 검사, 접선 반환
    for object in object_layer:
        # 레이어에 담긴 모든 오브젝트의 충돌 영역 리스트 생성
        object_rect = collision_rect(object.image, object.x, object.y)
        if standard_rect.colliderect(object_rect): # 플레이어가 오브젝트와 충돌했는지 확인
            if part == "bottom":
                return object, object_rect.top # 오브젝트의 윗변의 y좌표와 오브젝트 반환
            elif part == "left":
                return object_rect.right # 오브젝트의 높이(오른쪽)의 x좌표
            elif part == "right":
                return object_rect.left # 오브젝트의 높이(왼쪽)의 x좌표
            elif part == "top":
                return object_rect.bottom # 오브젝트의 밑변의 y좌표

def request_draw_curr_map(map_name): # 현재 플레이중인 맵 그리기 요청
    if map_name == "seoul":
        CURR_MAP.draw_seoul_map()

def request_event_process(char): # 현재 플레이중인 캐릭터의 키 이벤트 처리 요청
    if char == NINJA_FROG:
        char.ninja_frog_key_event()

# 글로벌 변수
WINDOW_WIDTH, WINDOW_HEIGHT = 1200, 800 # 출력화면 창의 너비, 높이
WINDOW = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT)) # 출력화면 창 정의
pg.display.set_caption("Platformer Game") # 창 상단바 제목

CLOCK = pg.time.Clock() # 게임 시간
FPS = 60 # 초당 프레임
RUN = True # 루프문 실행 여부

# 캐릭터 객체 추가
NINJA_FROG = Player(image_path="img/player_2.png", direction="right", move_speed=5, jump_power=20) # 플레이어 객체 생성

# 현재 플레이중인 캐릭터
CURR_CHAR = NINJA_FROG

# 맵 객체 추가
SEOUL = Map(map_data="seoul.txt", name="seoul") # 맵 객체 생성

# 현재 플레이중인 맵
CURR_MAP = SEOUL

# 메인 루프
while RUN:
    CLOCK.tick(FPS) # 초당 루프문을 수행하는 횟수(게임 진행속도)
    
    # <현재 캐릭터의 키 이벤트 처리 요청>
    request_event_process(CURR_CHAR)

    # <현재 맵 상태 그리기>
    CURR_CHAR.calc_dist_from_flag() # 추적 거리 계산
    CURR_MAP.draw_background() # 배경
    request_draw_curr_map(CURR_MAP.name) # 현재 맵의 모든 오브젝트 상태 그리기 요청
    CURR_MAP.draw_player() # 플레이어
    
    # 업데이트 사항 출력
    pg.display.update()

pg.quit() # 파이게임 종료