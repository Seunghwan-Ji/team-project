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
    def __init__(self, image_path, direction, move_speed, jump_power, weight, name):
        self.normal_img = change_image_size(pg.image.load(image_path), 2) # 이미지 로드
        self.flip_img = pg.transform.flip(self.normal_img, True, False) # 반전된 이미지
        self.flip = False # 반전 여부
        self.image = self.normal_img # 현재 이미지
        self.direction = direction # 보고있는 방향
        self.init_move_speed = move_speed
        self.move_speed = self.init_move_speed # 이동속도
        self.init_jump_power = jump_power # 초기 점프력
        self.weight = weight # 중량
        self.life_count = 5

        self.name = name
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
        self.deal_coolTime = int(time.time()) # 시간 기록(기능의 쿨타임)
        self.game_over = False
        self.bulk_up_time = False # 아이템 효과 쿨타임
        self.save_jump_power = self.init_jump_power
        self.skill_effect = None # 스킬 오브젝트 저장

        self.effect_layer = [] # 캐릭터의 이펙트 레이어

        if self.name == "ninja_frog":
            self.ninja_frog_skill_effect()
    
    # 플레이어 기능 메서드 추가
    def move_right(self): # 우측 이동 기능
        map_end_x = read_coordinate(CURR_MAP.data_indices, -1, -1)[0]
        map_end_x += (CURR_MAP.grid_width - self.width)
        if self.x < map_end_x: # 맵 우측 끝 위치보다 안쪽에 있으면 이동 허용
            self.x += self.move_speed # 이동속도 수치만큼 오른쪽으로 이동
        
        flip_image_direction(object=self, direction="right")

        for object in CURR_MAP.foothold_layer:
            if not object.is_dynamic:
                if object.static_blocks_dynamic(dynamic_obj=self):
                    break
            else:
                if object.dynamic_blocks_dynamic(dynamic_obj=self):
                    break
    
    def move_left(self): # 좌측 이동 기능
        if self.x > 0: # 맵 좌측 시작 위치보다 멀리있으면 이동 허용
            self.x -= self.move_speed # 이동속도 수치만큼 왼쪽으로 이동
        
        flip_image_direction(object=self, direction="left")
        
        for object in CURR_MAP.foothold_layer:
            if not object.is_dynamic:
                if object.static_blocks_dynamic(dynamic_obj=self):
                    break
            else:
                if object.dynamic_blocks_dynamic(dynamic_obj=self):
                    break

    def jump(self): # 점프 기능
        self.y -= self.jump_power # 현재 점프력 수치만큼 플레이어를 위로 이동
        # 점프력 수치를 (중력+중량)만큼 감소(매 루프마다 뛰어오르는 속도가 서서히 감소)
        self.jump_power -= (CURR_MAP.gravity + self.weight)
        self.direction = "up"
        
        for object in CURR_MAP.foothold_layer:
            if not object.is_dynamic:
                if object.static_blocks_dynamic(dynamic_obj=self):
                    self.jump_power = 0
                    break
            else:
                if object.dynamic_blocks_dynamic(dynamic_obj=self):
                    self.jump_power = 0
                    break
        
        if self.jump_power <= 0: # 현재 점프력 수치가 0이하면
            self.jumping = False # 점프 기능 비활성화
            self.on_foothold = False
            self.jump_power = self.init_jump_power # 점프력 수치 초기화

    def apply_gravity(self): # 중력 적용 기능
        # 중력 가속도 변수에 (중력+중량)을 축적(매 루프마다 아래로 떨어지는 속도가 서서히 증가)
        self.gravity_acc += (CURR_MAP.gravity + self.weight)
        self.y += self.gravity_acc # 현재 중력 가속도 수치만큼 플레이어를 아래로 이동
        self.direction = "down"

        for object in CURR_MAP.foothold_layer:
            if not object.is_dynamic:
                if object.static_blocks_dynamic(dynamic_obj=self):
                    self.gravity_acc = 0
                    self.on_foothold = True
                    break
                else:
                    self_rect = pg.Rect(self.x, self.y, self.width, self.height)
                    if self_rect.bottom == object.rect.top:
                        self.on_foothold = True # 접하기만 해도 true로 설정
                    else:
                        self.on_foothold = False
            else:
                if object.dynamic_blocks_dynamic(dynamic_obj=self):
                    self.gravity_acc = 0
                    self.on_foothold = True
                    if self.init_jump_power == self.save_jump_power:
                        if object.direction == "right":
                            self.x += object.move_speed
                        elif object.direction == "left":
                            self.x -= object.move_speed
                        elif object.direction == "up":
                            self.y -= object.move_speed
                    break
                else:
                    self_rect = pg.Rect(self.x, self.y, self.width, self.height)
                    if self_rect.bottom == object.rect.top:
                        self.on_foothold = True # 접하기만 해도 true로 설정
                    else:
                        self.on_foothold = False

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

    def attack(self):
        if self.skill_effect not in self.effect_layer:
            self.effect_layer.append(self.skill_effect)

        if not self.skill_effect.move_count:
            self.skill_effect.y = self.y + self.height/4
            if self.image == self.normal_img:
                self.skill_effect.x = self.x + self.width
                self.skill_effect.direction = "right"
            else:
                self.skill_effect.x = self.x
                self.skill_effect.direction = "left"
        
        if self.skill_effect.direction == "right":
            self.skill_effect.x += self.skill_effect.move_speed
            self.skill_effect.move_count += 1
        elif self.skill_effect.direction == "left":
            self.skill_effect.x -= self.skill_effect.move_speed
            self.skill_effect.move_count += 1
        
        if self.skill_effect.move_count == 25:
            self.skill_effect.move_count = 0
            self.skill_effect.flying = False
            self.effect_layer.remove(self.skill_effect)
            return

        for monster in CURR_MAP.monster_layer:
            if self.skill_effect.deal_damage(object=monster, damage=2):
                self.skill_effect.move_count = 0
                self.skill_effect.flying = False
                self.effect_layer.remove(self.skill_effect)
                break

    def ninja_frog_skill_effect(self):
        image = change_image_size(pg.image.load("img/skill.png"), 4)
        self.skill_effect = Object(is_dynamic=True, image=image, x=0, y=0, type="skill", move_speed=20, name="눈덩이")
        self.skill_effect.flying = False

        self.effect_layer.append(self.skill_effect)

    # 캐릭터의 키 이벤트 처리 메서드 추가
    def ninja_frog_key_event(self): # ninja_frog 캐릭터의 이벤트 처리방식
        global RUN
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
        elif keys[pg.K_LCTRL] and not self.skill_effect.flying:
            self.skill_effect.flying = True
        
        # <플레이어 이동>
        if self.jumping:
            self.jump() # 점프
        else:
            self.apply_gravity() # 중력
        
        if self.key_right:
            self.move_right() # 오른쪽
        elif self.key_left:
            self.move_left() # 왼쪽
        
        # 공격
        if self.skill_effect.flying:
            self.attack()

class Map:
    def __init__(self, map_data, name):
        # 텍스트 기반 맵 파일을 읽어와서 데이터를 리스트로 저장
        with open(map_data, 'r') as file:
            data_list = [list(map(int, line.strip().split())) for line in file] # 2중 리스트

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
        self.end_point = False # 맵 엔드지점 도착 여부
        self.life_ui = change_image_size(pg.image.load("img/life.png"), 1/3)

        # 비슷한 유형의 오브젝트들끼리 나눠서 리스트에 저장
        self.static_objects = [] # 정적인 객체 모음
        self.dynamic_objects = [] # 동적인 객체 모음
        self.foothold_layer = [] # 발판 레이어
        self.obstacle_layer = [] # 장애물 레이어
        self.monster_layer = [] # 몬스터 레이어
        self.item_layer = [] # 아이템 레이어

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

    def draw_object(self): # 오브젝트 그리기 기능
        for object in (self.foothold_layer + self.obstacle_layer +
            self.monster_layer + self.item_layer + CURR_CHAR.effect_layer):
            WINDOW.blit(object.image, (object.x - CURR_CHAR.pull_x, object.y - CURR_CHAR.pull_y))

    def draw_player(self): # 플레이어 그리기 기능
        # 플레이어의 실제 위치를 (pull_x, pull_y)만큼 평행이동 시키고 플레이어 이미지 그리기
        WINDOW.blit(CURR_CHAR.image, (CURR_CHAR.x - CURR_CHAR.pull_x, CURR_CHAR.y - CURR_CHAR.pull_y))

    def draw_ui(self):
        if CURR_CHAR.life_count:
            for i in range(CURR_CHAR.life_count):
                WINDOW.blit(self.life_ui, (i * self.life_ui.get_width(), 0))

    def draw_lobby(self):
        pass

    def draw_ending(self):
        pass

    def draw_game_over(self):
        pass

    # 맵을 정의하는 메서드 추가
    def seoul(self): # 서울맵 정의
        # 발판 이미지 로드
        foothold_image = pg.image.load("img/tile.png")
        # foothold_image = change_image_size(foothold_image, 2)

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

        for i in np.argwhere(self.data_arr):
            row, col = i[0], i[1] # i: 요소의 행렬 인덱스를 담고 있다.(i[0]: 행 인덱스, i[1]: 열 인덱스)
            var = self.data_arr[row, col]
            x, y = read_coordinate(self.data_indices, row, col) # 오브젝트를 배치할 좌표
            
            image = foothold_image
            is_dynamic = False
            type = None
            direction = None
            move_speed = None
            name = None

            if var == 1:
                type = "turning_point"

            elif var == 2:
                type = "static_foothold"

            elif var == 3:
                CURR_CHAR.x, CURR_CHAR.y = x, y # 이 맵의 플레이어 초기 위치
                continue
            
            elif var == 4:
                is_dynamic = True
                type = "horizontal_foothold"
                direction = "right"
                move_speed = 8
            
            elif var == 5:
                is_dynamic = True
                type = "vertical_foothold"
                direction = "up"
                move_speed = 3
            
            elif var == 6:
                image = change_image_size(pg.image.load("img/Trampoline.png"), 4)
                type = "obstacle"
                name = "트램펄린"

            elif var == 7:
                image = change_image_size(pg.image.load("img/spike.png"), 2)
                type = "obstacle"
                name = "스파이크"
            
            elif var == 8:
                is_dynamic = True
                image = change_image_size(pg.image.load("img/honeybee.png"), 1.3)
                type = "monster"
                direction = "right"
                move_speed = 3
                name = "꿀벌"
            
            elif var == 9:
                is_dynamic = True
                image = change_image_size(pg.image.load("img/spike_mole.png"), 1.3)
                type = "monster"
                direction = "right"
                move_speed = 2
                name = "가시두더지"
            
            elif var == 10:
                image = change_image_size(pg.image.load("img/Melon.png"), 4)
                type = "item"
                name = "수박"
            
            elif var == 11:
                pass # 다른 캐릭터 객체로 변신하는 아이템 추가

            elif var == 12:
                image = change_image_size(pg.image.load("img/end_point.png"), 2)
                type = "obstacle"
                name = "엔드"

            # 장애물, 몬스터, 아이템 등을 발판위에 배치하도록 하는 y값 저장
            if image != foothold_image: # 발판 제외 y값 조정
                y -= (y + image.get_height()) - (y + self.grid_height)

            object = Object(is_dynamic, image, x, y, type, direction, move_speed, name)

            if is_dynamic:
                self.dynamic_objects.append(object)
            else:
                self.static_objects.append(object)

            if (type == "static_foothold" or type == "horizontal_foothold" or
                type == "vertical_foothold"):
                self.foothold_layer.append(object)
            elif type == "monster":
                self.monster_layer.append(object)
            elif type == "item":
                self.item_layer.append(object)
            elif type == "obstacle":
                self.obstacle_layer.append(object)

    # 정의한 맵의 기능 메서드 추가
    def update_seoul(self): # 서울맵 기능
        # 발판 기능
        for foothold in self.foothold_layer:
            if foothold.type == "horizontal_foothold": # 수평적 발판
                foothold.horizontal_motion(flip_img=False)
            elif foothold.type == "vertical_foothold": # 수직적 발판
                foothold.vertical_motion()
        
        # 장애물 기능
        for obstacle in self.obstacle_layer:
            if obstacle.name == "트램펄린":
                obstacle.bounce_up(object=CURR_CHAR, power=30, count=20)
            elif obstacle.name == "스파이크":
                obstacle.deal_damage(object=CURR_CHAR, coolTime=2)
                obstacle.slow_down(object=CURR_CHAR, move_speed=3, jump_power=5, coolTime=5)
            elif obstacle.name == "엔드":
                obstacle.check_end_point(player=CURR_CHAR)

        # 몬스터 기능
        for monster in self.monster_layer:
            monster.horizontal_motion()
            if CURR_CHAR.bulk_up_time:
                monster.step_on(object=CURR_CHAR)
            else:
                monster.deal_damage(object=CURR_CHAR, coolTime=2)
                monster.slow_down(object=CURR_CHAR, move_speed=3, jump_power=5, coolTime=2)
        
        # 아이템 기능
        for item in self.item_layer:
            if item.name == "수박":
                item.bulk_up(layer=self.item_layer, object=CURR_CHAR, size=3)
        
        # 아이템 효과 쿨타임 관리
        if CURR_CHAR.bulk_up_time:
            curr_time = int(time.time())
            if curr_time - CURR_CHAR.bulk_up_time >= 5:
                CURR_CHAR.weight *= (1/CURR_CHAR.init_size)
                change_image_size(CURR_CHAR.normal_img, 1/CURR_CHAR.init_size, CURR_CHAR)
                CURR_CHAR.bulk_up_time = False
        
        # 정적, 동적 객체간 충돌 막기
        for static in self.static_objects:
            for dynamic in self.dynamic_objects:
                if dynamic.type == "monster":
                    static.static_blocks_dynamic(dynamic_obj=dynamic, reverse_direction=True, flip_img=True)
                else:
                    static.static_blocks_dynamic(dynamic_obj=dynamic, reverse_direction=True)

class Object:
    def __init__(self, is_dynamic, image, x, y, type=None, direction=None, move_speed=None, name=None):
        self.is_dynamic = is_dynamic # 동적인가? true or false
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
        self.life_count = 3
        self.deal_coolTime = int(time.time()) # 시간 기록(기능의 쿨타임)
        self.slow_down_coolTime = False
        self.move_count = 0

        # 정적 객체만 충돌영역 설정
        if not self.is_dynamic:
            if not self.image: # 이미지가 없는 객체는 그리드 한 칸 사이즈로 설정
                self.width, self.height = CURR_MAP.grid_width, CURR_MAP.grid_height
            # 충돌영역 설정
            self.rect = pg.Rect(self.x, self.y, self.width, self.height)
    
    # 오브젝트 기능 메서드 추가
    def horizontal_motion(self, distance=0, flip_img=True): # 수평이동 기능
        if self.direction == "right":
            if distance:
                if self.x < self.init_x + distance:
                    self.x += self.move_speed
                else:
                    self.init_x += distance
                    self.x = self.init_x
                    if flip_img:
                        flip_image_direction(object=self, direction="left")
                    else:
                        self.direction = "left"
            else:
                self.x += self.move_speed
        elif self.direction == "left":
            if distance:
                if self.x > self.init_x - distance:
                    self.x -= self.move_speed
                else:
                    self.init_x -= distance
                    self.x = self.init_x
                    if flip_img:
                        flip_image_direction(object=self, direction="right")
                    else:
                        self.direction = "right"
            else:
                self.x -= self.move_speed

    def vertical_motion(self, distance=0): # 수직이동 기능
        if self.direction == "up":
            if distance:
                if self.y > self.init_y - distance:
                    self.y -= self.move_speed
                else:
                    self.init_y -= distance
                    self.y = self.init_y
                    self.direction = "down"
            else:
                self.y -= self.move_speed
        elif self.direction == "down":
            if distance:
                if self.y < self.init_y + distance:
                    self.y += self.move_speed
                else:
                    self.init_y += distance
                    self.y = self.init_y
                    self.direction = "up"
            else:
                self.y += self.move_speed

    def static_blocks_dynamic(self, dynamic_obj, reverse_direction=False, flip_img=False): # 정적인 객체가 동적인 객체를 막는 기능
        dynamic_obj_rect = pg.Rect(dynamic_obj.x, dynamic_obj.y, dynamic_obj.width, dynamic_obj.height)
        if self.rect.colliderect(dynamic_obj_rect):
            if dynamic_obj.direction == "right":
                dynamic_obj.x = self.rect.left - dynamic_obj.width
                
                if flip_img:
                    flip_image_direction(dynamic_obj, "left")
                elif reverse_direction:
                    dynamic_obj.direction = "left"
            
            elif dynamic_obj.direction == "left":
                dynamic_obj.x = self.rect.right
                
                if flip_img:
                    flip_image_direction(dynamic_obj, "right")
                elif reverse_direction:
                    dynamic_obj.direction = "right"
            
            elif dynamic_obj.direction == "up":
                dynamic_obj.y = self.rect.bottom
                
                if reverse_direction:
                    dynamic_obj.direction = "down"
            
            elif dynamic_obj.direction == "down":
                dynamic_obj.y = self.rect.top - dynamic_obj.height
                
                if reverse_direction:
                    dynamic_obj.direction = "up"

            return True

    def dynamic_blocks_dynamic(self, dynamic_obj): # 동적인 객체가 동적인 객체를 막는 기능
        self.rect = pg.Rect(self.x, self.y, self.width, self.height)
        dynamic_obj_rect = pg.Rect(dynamic_obj.x, dynamic_obj.y, dynamic_obj.width, dynamic_obj.height)
        if self.rect.colliderect(dynamic_obj_rect):
            if dynamic_obj.direction == "right":
                dynamic_obj.x = self.rect.left - dynamic_obj.width
            
            elif dynamic_obj.direction == "left":
                dynamic_obj.x = self.rect.right
            
            elif dynamic_obj.direction == "up":
                dynamic_obj.y = self.rect.bottom
            
            elif dynamic_obj.direction == "down":
                dynamic_obj.y = self.rect.top - dynamic_obj.height
        
            return True

    def deal_damage(self, object, damage=1, coolTime=False): # 충돌한 객체에게 데미지를 입히는 기능
        self.rect = pg.Rect(self.x, self.y, self.width, self.height)
        object_rect = pg.Rect(object.x, object.y, object.width, object.height)
        if object_rect.colliderect(self.rect):
            if coolTime:
                curr_time = int(time.time())
                if curr_time - self.deal_coolTime >= coolTime:
                    object.life_count -= damage
                    self.deal_coolTime = curr_time
                    # print(object.life_count)

                    if object.life_count <= 0:
                        if object != CURR_CHAR:
                            CURR_MAP.monster_layer.remove(object)
                            if object.slow_down_coolTime: # 캐릭터 둔화 풀어주기
                                CURR_CHAR.move_speed = CURR_CHAR.init_move_speed
                                CURR_CHAR.init_jump_power = CURR_CHAR.save_jump_power
                                object.slow_down_coolTime = False
                        else:
                            CURR_CHAR.game_over = True
            else:
                object.life_count -= damage
                if object.life_count <= 0:
                    CURR_MAP.monster_layer.remove(object)
                    if object.slow_down_coolTime:
                        CURR_CHAR.move_speed = CURR_CHAR.init_move_speed
                        CURR_CHAR.init_jump_power = CURR_CHAR.save_jump_power
                        object.slow_down_coolTime = False
            
            return True
    
    def slow_down(self, object, move_speed, jump_power, coolTime):
        if self.slow_down_coolTime:
            curr_time = int(time.time())
            if curr_time - self.slow_down_coolTime >= coolTime:
                object.move_speed = object.init_move_speed
                object.init_jump_power = object.save_jump_power
                self.slow_down_coolTime = False
        else:
            self.rect = pg.Rect(self.x, self.y, self.width, self.height)
            object_rect = pg.Rect(object.x, object.y, object.width, object.height)
            if object_rect.colliderect(self.rect):
                object.move_speed -= move_speed
                object.init_jump_power -= jump_power
                object.jump_power = object.init_jump_power
                object.gravity_acc = 0
                self.slow_down_coolTime = int(time.time())

    def bulk_up(self, layer, object, size): # 충돌한 객체의 크기와 중량을 커지게 하는 기능
        object_rect = pg.Rect(object.x, object.y, object.width, object.height)
        if object_rect.colliderect(self.rect):
            object.init_size = size
            init_height = object.height
            change_image_size(object.normal_img, size, object)
            object.weight *= size
            object.y -= (object.height - init_height) # 발판위에 재배치
            object.bulk_up_time = int(time.time())
            layer.remove(self)

    def bounce_up(self, object, power, count): # 충돌한 객체를 위로 튕겨내는 기능
        if self.bouncing:
            if object.jumping:
                object.jump_power = 0 # 점프상태이면 점프력을 0으로 초기화하고 더 뛰어오르지 못하게함
            object.y -= (self.bounce_power + object.gravity_acc) # 중력 가속도만큼 내려간걸 다시 올려서 계산
            self.bounce_power -= (CURR_MAP.gravity + object.weight)
            self.bounce_count += 1
            if self.bounce_count == count:
                self.bounce_count = 0
                object.gravity_acc = 0
                self.bouncing = False
        else:
            object_rect = pg.Rect(object.x, object.y, object.width, object.height)
            if self.rect.colliderect(object_rect):
                if object_rect.bottom <= self.rect.bottom:
                    object.y = self.rect.top - object.height
                    self.bouncing = True
                    self.bounce_count = 0
                    self.bounce_power = power
                else:
                    self.static_blocks_dynamic(dynamic_obj=object)

    def step_on(self, object): # 위에서 충돌한 객체가 있다면 자신을 레이어에서 제거하는 기능
        self.rect = pg.Rect(self.x, self.y, self.width, self.height)
        object_rect = pg.Rect(object.x, object.y, object.width, object.height)
        if object_rect.colliderect(self.rect):
            if object_rect.bottom < self.rect.bottom:
                CURR_MAP.monster_layer.remove(self)

    def check_end_point(self, player):
        player_rect = pg.Rect(player.x, player.y, player.width, player.height)
        if player_rect.colliderect(self.rect):
            CURR_MAP.end_point = True

# 함수
def change_image_size(image, size, object=None): # 이미지 사이즈 조절
    resized_img = pg.transform.scale(image, (image.get_width() * size, image.get_height() * size))
    if object: # 객체를 전달하면 이미지 관련 속성을 모두 수정해줌
        object.normal_img = resized_img
        object.flip_img = pg.transform.flip(resized_img, True, False)
        object.width = resized_img.get_width()
        object.height = resized_img.get_height()
        # 현재 이미지 결정
        if not object.flip:
            object.image = object.normal_img
        else:
            object.image = object.flip_img
    else:
        return resized_img

def flip_image_direction(object, direction): # 전달받은 방향대로 객체의 이미지를 반전시켜주는 함수
    if object.direction != direction:
        object.direction = direction # 방향 변경
        if direction == "right":
            object.image = object.normal_img
            object.flip = False
        elif direction == "left":
            object.image = object.flip_img
            object.flip = True

def read_coordinate(data_indices, row, col): # 그리드 배열에 전달받은 값을 인덱싱하여 해당 위치의 좌표를 반환
    return data_indices[1, row, col], data_indices[0, row, col]

def request_update_map(map_name): # 현재 플레이중인 맵 그리기 요청
    if map_name == "seoul":
        CURR_MAP.update_seoul()

def request_event_process(char): # 현재 플레이중인 캐릭터의 키 이벤트 처리 요청
    if char == NINJA_FROG:
        char.ninja_frog_key_event()

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
BG_PATH = ["spring", "daytime", "Rain"] # 고정할 배경 영상 폴더 경로(각 폴더 이름만)

# 캐릭터 객체 추가
PINK_MAN = Player(image_path="img/player_1.png", direction="right",
    move_speed=5, jump_power=20, weight=0.4, name="pink_man") # 플레이어 객체 생성

NINJA_FROG = Player(image_path="img/player_2.png", direction="right",
    move_speed=7, jump_power=25, weight=0.2, name="ninja_frog")

# 현재 플레이중인 캐릭터
CURR_CHAR = NINJA_FROG

# 맵 객체 추가
SEOUL = Map(map_data="seoul.txt", name="seoul") # 맵 객체 생성, name=지역이름

# 현재 플레이중인 맵
CURR_MAP = SEOUL

# 스레드 생성
THREAD = threading.Thread(target=update_time_and_weather) # 스레드가 입장할 함수
THREAD.daemon = True # 메인스레드가 종료될 때 이 스레드도 같이 종료
THREAD.start() # 스레드 시작

# 메인 루프
while RUN:
    CLOCK.tick(FPS) # 초당 루프문을 수행하는 횟수(게임 진행속도)
    
    # <현재 플레이어의 키 이벤트 처리 요청>
    request_event_process(CURR_CHAR)

    # 현재 맵 업데이트 요청
    request_update_map(CURR_MAP.name)

    # 플레이어 위치 추적
    CURR_CHAR.calc_dist_from_flag()

    # 그리기
    CURR_MAP.draw_background() # 배경
    CURR_MAP.draw_object() # 오브젝트
    CURR_MAP.draw_player() # 플레이어
    CURR_MAP.draw_ui() # UI
    
    # 게임 오버 처리
    if CURR_CHAR.game_over:
        print("Game Over")
        # CURR_MAP.draw_game_over() # 추가예정
        break

    # 엔딩 처리
    if CURR_MAP.end_point:
        print("Thank you for playing the game")
        # CURR_MAP.draw_ending() # 추가예정
        break

    # 출력
    pg.display.update()

pg.quit() # 파이게임 종료
