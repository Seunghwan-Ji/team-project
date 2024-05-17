import pygame as pg
import numpy as np
import cv2
import requests
import json
import datetime
import threading
import time
pg.init()

# 객체를 생성하는 클래스 정의
class Player:
    def __init__(self, image_path, direction, move_speed, jump_power, weight):
        self.normal_img = change_image_size(pg.image.load(image_path), 2) # 이미지 로드
        self.flip_img = pg.transform.flip(self.normal_img, True, False) # 반전된 이미지
        self.flip = False # 반전 여부
        self.image = self.normal_img # 현재 이미지
        self.direction = direction # 보고있는 방향
        self.move_speed = move_speed # 이동속도
        self.init_jump_power = jump_power # 초기 점프력
        self.weight = weight # 중량

        self.width = self.image.get_width() # 이미지 너비
        self.height = self.image.get_height() # 이미지 높이
        self.jump_power = self.init_jump_power # 현재 점프력
        self.gravity_acc = 0 # 중력 가속도
        self.jumping = False # 점프중인 상태
        self.on_foothold = False # 발판 위에 닿았는지 여부
        self.key_right = False # 오른쪽 방향키 눌림 여부
        self.key_left = False # 왼쪽 방향키 눌림 여부
        self.x, self.y = 0, 0 # 현재 위치
        self.pull_x, self.pull_y = 0, 0 # 평행이동할 수치(x축, y축의 깃발과 떨어진 거리)
        self.bouncing = False # 바운스 상태
        self.bounce_count = 0 # 바운스 횟수
    
    def move_right(self): # 우측 이동 기능
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
        
        flip_image_direction(self, "right")
    
    def move_left(self): # 좌측 이동 기능
        player_rect = collision_rect(self.image, self.x - self.move_speed, self.y)
        object_right_tangent = check_collision(CURR_MAP.foothold_layer, player_rect, part="left")
        
        # 플레이어가 좌측으로 충돌중이 아니고, 맵 좌측 끝부분 보다 멀리 있으면
        if self.x > 0:
            if not object_right_tangent:
                self.x -= self.move_speed # 이동속도 수치만큼 왼쪽으로 이동
            else:
                self.x -= (self.x - object_right_tangent)

        flip_image_direction(self, "left")

    def jump(self): # 점프 기능
        player_rect = collision_rect(self.image, self.x, self.y - self.jump_power)
        object_bottom_tangent = check_collision(CURR_MAP.foothold_layer, player_rect, part="top")
        if not object_bottom_tangent:
            self.y -= self.jump_power # 현재 점프력 수치만큼 플레이어를 위로 이동
            # 점프력 수치를 (중력+중량)만큼 감소(매 루프마다 뛰어오르는 속도가 서서히 감소)
            self.jump_power -= (CURR_MAP.gravity + self.weight)
        else:
            self.y -= (self.y - object_bottom_tangent)
            self.jump_power = 0
        
        if self.jump_power <= 0: # 현재 점프력 수치가 0이하면
            self.jumping = False # 점프 기능 비활성화
            self.on_foothold = False
            self.jump_power = self.init_jump_power # 점프력 수치 초기화

    def apply_gravity(self): # 중력 적용 기능
        # 중력 가속도 변수에 (중력+중량)을 축적(매 루프마다 아래로 떨어지는 속도가 서서히 증가)
        self.gravity_acc += (CURR_MAP.gravity + self.weight)
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
            
            # 동적인 오브젝트 위에 탑승 시 따라가기
            if object.direction == "right":
                self.x += object.move_speed
            elif object.direction == "left":
                self.x -= object.move_speed
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
                        self.key_left = True # 왼쪽 이동 기능 활성화
                    elif event.key == pg.K_RIGHT: # 오른쪽 방향키인 경우
                        self.key_right = True # 오른쪽 이동 기능 활성화
                elif event.type == pg.KEYUP: # 키보드 키를 뗀 상태일 때
                    if event.key == pg.K_LEFT: # 왼쪽 방향키인 경우
                        self.key_left = False # 왼쪽 이동 기능 비활성화
                    elif event.key == pg.K_RIGHT: # 오른쪽 방향키인 경우
                        self.key_right = False # 오른쪽 이동 기능 비활성화
                elif event.type == pg.QUIT: # 창 닫기 버튼을 눌러 창을 닫았을 때
                    RUN = False # 루프문 탈출

            keys = pg.key.get_pressed() # 키보드에서 눌린 키들

            # 왼쪽 ALT키 or 스페이스바가 눌려있고, 플레이어가 점프중이 아니고, 발판 위에 있으면
            if (keys[pg.K_LALT] or keys[pg.K_SPACE]) and not self.jumping and self.on_foothold:
                self.jumping = True # 점프 기능 활성화
            
            # <플레이어 이동>
            if self.key_right:
                self.move_right() # 오른쪽
            elif self.key_left:
                self.move_left() # 왼쪽

            if self.jumping:
                self.jump() # 점프
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
        self.grid_width, self.grid_height = 1, 1 # 그리드 한 칸의 사이즈
        self.width, self.height = None, None # 맵의 전체 너비, 높이
        self.gravity = 1 # 중력
        self.background_image = None # 배경 이미지
        self.bg_x, self.bg_y = 0, 0 # 배경 이미지 위치
        self.init_player_pos = 0, 0 # 플레이어 스폰 위치
        self.month = datetime.datetime.now().month # 현재 월 저장
        self.season = BG_PATH[0] if FIX_BG else decide_season(self.month) # 현재 월의 계절 저장
        self.hour = datetime.datetime.now().hour # 현재 시각 저장
        self.timeslot = BG_PATH[1] if FIX_BG else decide_timeslot(self.hour) # 현재 시각의 시간대 저장
        self.weather = BG_PATH[2] if FIX_BG else request_weather(self.name) # 지역의 날씨 저장
        self.cap = cv2.VideoCapture(f"video/{self.season}/{self.timeslot}/{self.weather}.mp4") # 영상 로드
        self.ret, self.frame = self.cap.read() # 프레임 읽기 시작

        # 비슷한 유형의 오브젝트들끼리 나눠서 리스트에 저장
        self.foothold_layer = []
        self.monster_layer = []
        self.obstacle_layer = []
        self.item_layer = []

        # 맵 이름마다 조건을 달아주고 맵을 정의하는 메서드 호출
        if self.name == "seoul":
            self.seoul()
    
    def draw_background(self): # 배경 그리기 기능
        frame_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB) # 현재 프레임을 rgb형식으로 변환
        background_image = pg.image.frombuffer(frame_rgb.tobytes(), frame_rgb.shape[1::-1], "RGB") # rgb를 이미지로 변환
        
        # 이미지를 맵의 전체 너비, 높이 속성만큼 사이즈 업
        self.background_image = pg.transform.scale(background_image, (self.width, self.height))

        # 이미지 그리기
        WINDOW.blit(self.background_image, (self.bg_x - CURR_CHAR.pull_x, self.bg_y - CURR_CHAR.pull_y))

        self.ret, self.frame = self.cap.read() # 다음 프레임 읽기
        if not self.ret: # 모든 프레임이 끝나서 읽어지지 않는다면
            if not FIX_BG: # 배경 고정 모드가 아니면
                # 프레임 끝날때마다 속성값 참조하여 영상 업데이트
                self.cap = cv2.VideoCapture(f"video/{self.season}/{self.timeslot}/{self.weather}.mp4")
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # 0번째 인덱스 프레임으로 이동
            self.ret, self.frame = self.cap.read() # 다시 읽기 시작

    def draw_player(self): # 플레이어 이미지 그리기 기능
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

        # 맵의 전체 너비, 높이 계산
        end_x, end_y = read_coordinate(self.data_indices, -1, -1) # 데이터 인덱스 배열에서 마지막 행, 마지막 열의 좌표
        self.width, self.height = end_x + self.grid_width, end_y + self.grid_height # 가로 세로 각각 그리드 한 칸 만큼 더 늘려서 적용(1픽셀 확장)
        
        # 배경 이미지 로드
        # background_image = pg.image.load("img/Brown.png")
        # self.background_image = pg.transform.scale(background_image, (self.width, self.height))

        # 이 맵의 플레이어 초기 위치
        pos_index = np.argwhere(self.data_arr == 9)[0]
        CURR_CHAR.x, CURR_CHAR.y = read_coordinate(self.data_indices, pos_index[0], pos_index[1])

        for i in np.argwhere(self.data_arr):
            row, col = i[0], i[1] # i: 요소의 행렬 인덱스를 담고 있다.(i[0]: 행 인덱스, i[1]: 열 인덱스)
            x, y = read_coordinate(self.data_indices, row, col) # 오브젝트를 배치할 좌표
            
            image = foothold_image
            type = None
            direction = None
            move_speed = None
            name = None

            if self.data_arr[row, col] == 1:
                type = "static_foothold"
            elif self.data_arr[row, col] == 2:
                type = "horizontal_foothold"
                direction = "right"
                move_speed = 3
            elif self.data_arr[row, col] == 3:
                type = "vertical_foothold"
                direction = "up"
                move_speed = 3
            elif self.data_arr[row, col] == 4:
                type = "horizontal_foothold"
                direction = "left"
                move_speed = 3
            elif self.data_arr[row, col] == 5:
                image = pg.image.load("img/Goblin.png")
                type = "monster"
                direction = "left"
                move_speed = 2
                name = "요괴"
            elif self.data_arr[row, col] == 6:
                image = pg.image.load("img/Rabbit.png")
                type = "monster"
                direction = "left"
                move_speed = 3
                name = "토끼"
            elif self.data_arr[row, col] == 7:
                image = change_image_size(pg.image.load("img/Apple.png"), 2)
                type = "item"
                name = "사과"
            elif self.data_arr[row, col] == 8:
                image = change_image_size(pg.image.load("img/Trampoline.png"), 2)
                type = "obstacle"
                name = "트램펄린"
            
            if type == "static_foothold" or type == "horizontal_foothold" or type == "vertical_foothold":
                self.foothold_layer.append(Object(image, x, y, type, direction, move_speed, name))
            elif type == "monster":
                y -= ((y + image.get_height()) - (y + self.grid_height)) # 발판 위에 닿도록 위치변경
                self.monster_layer.append(Object(image, x, y, type, direction, move_speed, name))
            elif type == "item":
                y -= ((y + image.get_height()) - (y + self.grid_height))
                self.item_layer.append(Object(image, x, y, type, direction, move_speed, name))
            elif type == "obstacle":
                y -= ((y + image.get_height()) - (y + self.grid_height))
                self.obstacle_layer.append(Object(image, x, y, type, direction, move_speed, name))

    # 정의한 맵을 그리는 메서드 추가
    def draw_seoul_map(self): # 서울맵 그리기 기능
        # 발판 레이어 그리기
        for foothold in self.foothold_layer:
            if foothold.type == "horizontal_foothold": # 수평적 발판
                foothold.horizontal_motion(distance=2000)
            elif foothold.type == "vertical_foothold": # 수직적 발판
                foothold.vertical_motion(distance=2000)
            
            if foothold.type != "static_foothold":
                foothold.push_object(CURR_CHAR)
            
            WINDOW.blit(foothold.image, (foothold.x - CURR_CHAR.pull_x, foothold.y - CURR_CHAR.pull_y))
        
        # 몬스터 레이어 그리기
        for monster in self.monster_layer:
            if monster.name == "요괴" or monster.name == "토끼":
                monster.horizontal_motion(distance=1000)
            
            WINDOW.blit(monster.image, (monster.x - CURR_CHAR.pull_x, monster.y - CURR_CHAR.pull_y))
        
        # 아이템 레이어 그리기
        for item in self.item_layer:
            if item.name == "사과":
                item.bulk_up(layer=self.item_layer, object=CURR_CHAR, size=2)
                WINDOW.blit(item.image, (item.x - CURR_CHAR.pull_x, item.y - CURR_CHAR.pull_y))
        
        # 장애물 레이어 그리기
        for obstacle in self.obstacle_layer:
            if obstacle.name == "트램펄린":
                obstacle.bounce(object=CURR_CHAR, direction="up", power=50, count=10)
                WINDOW.blit(obstacle.image, (obstacle.x - CURR_CHAR.pull_x, obstacle.y - CURR_CHAR.pull_y))

class Object:
    def __init__(self, image, x, y, type=None, direction=None, move_speed=None, name=None):
        self.normal_img = image
        self.flip_img = pg.transform.flip(image, True, False) # 반전된 이미지
        self.flip = False # 이미지 반전 여부
        self.image = self.normal_img # 현재 이미지
        self.width = self.image.get_width() # 이미지 너비
        self.height = self.image.get_height() # 이미지 높이
        self.init_x, self.init_y = x, y # 초기 좌표
        self.x, self.y = self.init_x, self.init_y # 실시간 좌표
        self.type = type # 타입명
        self.direction = direction # 이동방향
        self.move_speed = move_speed # 이동속도
        self.name = name # 이름
        self.bouncing = False # 바운스 상태
        self.bounce_count = 0 # 바운스 횟수
    
    # 오브젝트 기능 추가
    def horizontal_motion(self, distance): # 수평이동 기능
        if self.direction == "right":
            if self.x < self.init_x + distance:
                self.x += self.move_speed
            else:
                self.init_x += distance
                self.x = self.init_x
                flip_image_direction(self, "left")
        elif self.direction == "left":
            if self.x > self.init_x - distance:
                self.x -= self.move_speed
            else:
                self.init_x -= distance
                self.x = self.init_x
                flip_image_direction(self, "right")

    def vertical_motion(self, distance): # 수직이동 기능
        if self.direction == "up":
            if self.y > self.init_y - distance:
                self.y -= self.move_speed
            else:
                self.init_y -= distance
                self.y = self.init_y
                self.direction = "down"
        elif self.direction == "down":
            if self.y < self.init_y + distance:
                self.y += self.move_speed
            else:
                self.init_y += distance
                self.y = self.init_y
                self.direction = "up"

    def prevent_overlap(self, object, move_speed): # 객체가 충돌되지 않게 막는 기능
        self_rect = self.collision_rect(self.image, self.x, self.y)
        object_rect = None
        distance = 0
        if object.direction == "right":
            object_rect = object.collision_rect(object.image, object.x + move_speed, object.y)
            distance = self_rect.left - object.x - object.width
        elif object.direction == "left":
            object_rect = object.collision_rect(object.image, object.x - move_speed, object.y)
            distance = self_rect.right - object.x
        elif object.direction == "up":
            object_rect = object.collision_rect(object.image, object.x, object.y - move_speed)
            distance = self_rect.bottom - object.y
        elif object.direction == "down":
            object_rect = object.collision_rect(object.image, object.x, object.y + move_speed)
            distance = self_rect.top - object.y + object.height

        if self_rect.colliderect(object_rect):
            if object.direction == "right" or object.direction == "left":
                object.x += distance
            else:
                object.y += distance

    def push_object(self, object): # 충돌한 객체를 밀어내는 기능
        self_rect = collision_rect(self.image, self.x, self.y)
        object_rect = collision_rect(object.image, object.x, object.y)
        if self_rect.colliderect(object_rect):
            if self.direction == "right":
                object.x = self_rect.right # 오른쪽 접선에 배치
            elif self.direction == "left":
                object.x = self_rect.left - object.width # 왼쪽 접선에 배치

    def deal_damage(self): # 충돌한 객체에 데미지를 입히는 기능
        pass

    def bulk_up(self, layer, object, size): # 충돌한 객체의 크기와 중량을 커지게 하는 기능
        object_rect = collision_rect(object.image, object.x, object.y)
        self_rect = collision_rect(self.image, self.x, self.y)
        if object_rect.colliderect(self_rect):
            init_height = object.height
            change_image_size(object.image, size, object)
            object.weight *= size
            object.y -= (object.height - init_height)
            layer.remove(self)

    def bounce(self, object, direction, power, count): # 충돌한 객체를 튕겨내는 기능
        if not object.bouncing:
            self_rect = collision_rect(self.image, self.x, self.y)
            object_rect = collision_rect(object.image, object.x, object.y)
            if self_rect.colliderect(object_rect):
                object.bouncing = True
        
        if object.bouncing:
            if direction == "up":
                object.y -= power
            elif direction == "right":
                object.x += power
            elif direction == "left":
                object.x -= power
            
            object.bounce_count += 1

            if object.bounce_count == count:
                object.bounce_count = 0
                object.bouncing = False

# 함수
def change_image_size(image, size, object=None): # 이미지 사이즈 조절
    resized_img = pg.transform.scale(image, (image.get_width() * size, image.get_height() * size))
    if object: # 객체를 전달하면 이미지 관련 속성을 모두 수정해줌
        object.normal_img = resized_img
        object.flip_img = pg.transform.flip(resized_img, True, False)
        object.image = resized_img
        object.width = resized_img.get_width()
        object.height = resized_img.get_height()
    else:
        return resized_img

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

def flip_image_direction(object, direction): # 전달받은 방향대로 이미지를 반전시켜주는 함수
    if object.direction != direction:
        object.direction = direction # 방향 변경
        if not object.flip:
            object.image = object.flip_img # 반전된 이미지로 변경
            object.flip = True # 반전 상태로 변경
        else:
            object.image = object.normal_img # 원래 이미지로
            object.flip = False

def decide_season(month): # 현재 월에 대한 계절 반환
    if month >= 3 and month < 6:
        return "spring"
    elif month >= 6 and month < 9:
        return "summer"
    elif month >= 9 and month < 12:
        return "fall"
    elif month == 12 or month == 1 or month == 2:
        return "winter"

def decide_timeslot(hour): # 현재 시각에 대한 시간대 반환
    if hour >= 0 and hour < 6:
        return "midnight"
    if hour >= 6 and hour < 12:
        return "morning"
    if hour >= 12 and hour < 18:
        return "daytime"
    if hour >= 18 and hour < 24:
        return "evening"

def request_weather(city): # 현재 지역의 날씨 반환
    apiKey = "34160e089147db88b9f126c63909254a" # api key
    lang = 'kr' # 언어
    units = 'metric' # 화씨 온도를 섭씨 온도로 변경
    api = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={apiKey}&lang={lang}&units={units}" # 주소

    result = requests.get(api) # 요청
    data = json.loads(result.text) # 데이터 반환

    return data['weather'][0]['main'] # 날씨

def update_time_and_weather(): # 주기적으로 계절, 시간, 날씨를 분석해주는 함수(스레드가 입장하는 함수)
    while not FIX_BG: # 배경 고정 모드가 아니면 반복
        curr_month = datetime.datetime.now().month # 현재 월
        if CURR_MAP.month != curr_month:
            CURR_MAP.month = curr_month # 현재 맵의 월 속성 업데이트
        
        curr_season = decide_season(CURR_MAP.month) # 계절 반환 함수 호출
        if CURR_MAP.season != curr_season:
            CURR_MAP.season = curr_season # 계절 속성 업데이트
        
        curr_hour = datetime.datetime.now().hour # 현재 시각
        if CURR_MAP.hour != curr_hour:
            CURR_MAP.hour = curr_hour # 시각 속성 업데이트

        curr_timeslot = decide_timeslot(CURR_MAP.hour) # 시간대 반환 함수 호출
        if CURR_MAP.timeslot != curr_timeslot:
            CURR_MAP.timeslot = curr_timeslot # 시간대 속성 업데이트

        weather = request_weather(CURR_MAP.name) # 날씨 반환 함수 호출
        if weather != CURR_MAP.weather:
            CURR_MAP.weather = weather # 날씨 속성 업데이트

        print(f"{CURR_MAP.month}월({CURR_MAP.season}), {CURR_MAP.hour}시({CURR_MAP.timeslot}), 날씨: {CURR_MAP.weather}")
        time.sleep(60) # 60초마다 한번씩 분석

# 글로벌 변수
WINDOW_WIDTH, WINDOW_HEIGHT = 1200, 800 # 출력화면 창의 너비, 높이
WINDOW = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT)) # 출력화면 창 정의
pg.display.set_caption("Platformer Game") # 창 상단바 제목

CLOCK = pg.time.Clock() # 게임 시간
FPS = 60 # 초당 프레임
RUN = True # 루프문 실행 여부
FIX_BG = False # 배경 고정 모드
BG_PATH = ["winter", "daytime", "Snow"] # 고정할 배경 영상 폴더 경로(각 폴더 이름만)

# 캐릭터 객체 추가
NINJA_FROG = Player(image_path="img/player_2.png", direction="right",
    move_speed=5, jump_power=50, weight=0.4) # 플레이어 객체 생성

# 현재 플레이중인 캐릭터
CURR_CHAR = NINJA_FROG

# 맵 객체 추가
SEOUL = Map(map_data="seoul.txt", name="seoul") # 맵 객체 생성

# 현재 플레이중인 맵
CURR_MAP = SEOUL

# 스레드 생성
THREAD = threading.Thread(target=update_time_and_weather) # 스레드가 입장할 함수
THREAD.daemon = True # 메인스레드가 종료될 때 이 스레드도 같이 종료
THREAD.start() # 스레드 시작

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