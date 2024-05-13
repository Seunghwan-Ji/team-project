import pygame as pg
import numpy as np
pg.init()

WINDOW_WIDTH, WINDOW_HEIGHT = 1200, 800 # 출력화면 창의 너비, 높이
WINDOW = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT)) # 출력화면 창 정의
pg.display.set_caption("Platformer Game") # 창 상단바 제목

# 텍스트 맵 파일을 읽어와서 리스트로 저장
with open('map_data_2.txt', 'r') as file:
    data = [list(map(int, list(line.strip()))) for line in file]

# 데이터 리스트를 넘파이 2차원 배열로 변환
MAP_DATA_ARR = np.array(data)

# 전달 받은 이미지의 사이즈 조절
def change_image_size(img, size):
    return pg.transform.scale(img, (img.get_width() * size, img.get_height() * size))

# 배경 타일 이미지
BG_TILE = pg.image.load("img/Brown.png")
BG_TILE = change_image_size(BG_TILE, 2)

# 발판 타일 이미지
FOOTHOLD_TILE = pg.image.load("img/foothold_2.png")
FOOTHOLD_TILE = change_image_size(FOOTHOLD_TILE, 2)

# 맵 데이터의 크기만큼 행 배열, 열 배열을 생성하고 각각 발판의 높이, 너비를 곱셈(x축 배열, y축 배열 생성)
MAP_DATA_INDICES = np.indices((len(MAP_DATA_ARR), len(MAP_DATA_ARR[0])))
MAP_DATA_INDICES[0] *= FOOTHOLD_TILE.get_height()
MAP_DATA_INDICES[1] *= FOOTHOLD_TILE.get_width()

def read_coordinate(row, col): # x축 배열, y축 배열에 전달받은 값을 인덱싱하여 해당 위치의 좌표를 반환
    return MAP_DATA_INDICES[1, row, col], MAP_DATA_INDICES[0, row, col]

class Object_Info: # 모든 오브젝트의 정보를 담는 클래스 정의
    FOOTHOLD_LAYER = [] # 모든 발판의 그릴 좌표, 정보(속성)
    MONSTER_LAYER = [] # 모든 몬스터의 그릴 좌표, 정보(속성)
    OBSTACLE_LAYER = [] # 모든 장애물의 그릴 좌표, 정보(속성)
    EFFECT_LAYER = [] # 모든 이펙트의 그릴 좌표, 정보(속성)

    def __init__(self, row, col, type, direction=None): # 클래스 호출하면 기본적으로 실행되는 함수
        self.init_x, self.init_y = read_coordinate(row, col) # 초기 (x, y)좌표
        self.x, self.y = self.init_x, self.init_y # 변하는 (x, y)좌표(동적인 오브젝트만)
        self.type = type # 정적인 타입 or 동적인 타입
        self.direction = direction # 동적인 타입의 이동 방향(상하좌우)
        self.move_speed = 3

for i in np.argwhere(MAP_DATA_ARR == 1): # 정적인 발판 객체에 속성을 부여하고 발판 레이어 리스트에 추가
    type = "static" # 타입 속성명 설정
    Object_Info.FOOTHOLD_LAYER.append(Object_Info(i[0], i[1], type))

# 동적인 발판 객체에 속성을 부여하고 발판 레이어 리스트에 추가
for i in np.argwhere(MAP_DATA_ARR == 4): # 맵 배열에서 요소가 4인것
    type = "horizontal" # 타입 속성명 설정
    direction = "left" # 방향 속성명 설정
    Object_Info.FOOTHOLD_LAYER.append(Object_Info(i[0], i[1], type, direction)) # 좌표 속성을 부여하기 위해 행렬, 인덱스도 전달

for i in np.argwhere(MAP_DATA_ARR == 2):
    type = "horizontal"
    direction = "right"
    Object_Info.FOOTHOLD_LAYER.append(Object_Info(i[0], i[1], type, direction))

for i in np.argwhere(MAP_DATA_ARR == 3):
    type = "vertical"
    direction = "up"
    Object_Info.FOOTHOLD_LAYER.append(Object_Info(i[0], i[1], type, direction))

# 플레이어 이미지
PLAYER_IMG = pg.image.load("img/player_2.png")
PLAYER_IMG = change_image_size(PLAYER_IMG, 2)

# 배열에서 값이 9인 요소의 행, 열 인덱스 찾기, [0]은 값이 여러개일 경우 하나만 선택한다는 의미
PLAYER_INDEX = np.argwhere(MAP_DATA_ARR == 9)[0]

# 플레이어 초기 위치를 행, 열 인덱스에 각각 너비와 높이를 곱해서 좌표로 지정(스폰 좌표)
PLAYER_X, PLAYER_Y = PLAYER_INDEX[1] * FOOTHOLD_TILE.get_width(), (
    PLAYER_INDEX[0] + 1) * FOOTHOLD_TILE.get_height() - PLAYER_IMG.get_height()

# 초기 평행이동 수치 설정(맵의 x, y축을 출력 화면쪽으로 당길 수치)
PULL_X, PULL_Y = 0, 0

FPS = pg.time.Clock() # 초당 프레임 변수 선언
MOVE_LEFT = False # 오른쪽 이동키 눌림 여부
MOVE_RIGHT = False # 왼쪽 이동키 눌림 여부
PLAYER_FLIP = False # 플레이어 이미지 반전(플레이어가 보고있는 방향)
GRAVITY = 1 # 중력
GRAVITY_ACC = 0 # 축적된 중력의 총 크기(중력 가속도)
MOVE_SPEED = 5 # 이동속도
INIT_JUMP_POWER = 20 # 점프력(초기값)
JUMP_POWER = INIT_JUMP_POWER # 현재 점프력
JUMPING = False # 점프중인 상태
ON_FOOTHOLD = False # 플레이어가 발판 위에 닿았는지 여부
RUN = True # 메인 루프 실행 여부

# 전달받은 이미지의 충돌 영역 정의(히트박스)
def collision_rect(img, x, y):
    return pg.Rect(x, y, img.get_width(), img.get_height())

# 전달받은 두 이미지의 충돌 감지 여부
def detect_collision(rect1, rect2):
    return rect1.colliderect(rect2)

# 충돌 검사할 부위, 오브젝트와 맞닿은 접선 반환
def check_collision_part(player_rect, part):
    # 모든 발판의 충돌 영역 리스트 생성
    for foothold in Object_Info.FOOTHOLD_LAYER:
        foothold_rect = collision_rect(FOOTHOLD_TILE, foothold.x, foothold.y)
        if player_rect.colliderect(foothold_rect): # 플레이어가 발판과 충돌했는지 확인
            if part == "bottom":
                return foothold_rect.top, foothold # 발판의 윗변의 y좌표와 발판 객체 반환
            elif part == "left":
                return foothold_rect.right # 발판의 높이(오른쪽)의 x좌표와 발판 객체 반환
            elif part == "right":
                return foothold_rect.left # 발판의 높이(왼쪽)의 x좌표와 발판 객체 반환
            elif part == "top":
                return foothold_rect.bottom # 발판의 밑변의 y좌표와 발판 객체 반환

while RUN:
    FPS.tick(144) # 초당 화면에 그려낼 프레임 수(출력 횟수)
    
    # <이벤트 처리 로직>

    for event in pg.event.get(): # 파이게임의 이벤트들 참조
        if event.type == pg.QUIT: # 닫기 버튼을 눌러 창을 닫았을 때
            RUN = False # 루프 탈출
        elif event.type == pg.KEYDOWN: # 키보드 키가 눌린 상태일 때
            if event.key == pg.K_LEFT: # 왼쪽 방향키인 경우
                MOVE_LEFT = True # 왼쪽 이동 기능 활성화
            elif event.key == pg.K_RIGHT: # 오른쪽 방향키인 경우
                MOVE_RIGHT = True # 오른쪽 이동 기능 활성화
        elif event.type == pg.KEYUP: # 키보드 키를 뗀 상태일 때
            if event.key == pg.K_LEFT: # 왼쪽 방향키인 경우
                MOVE_LEFT = False # 왼쪽 이동 기능 비활성화
            elif event.key == pg.K_RIGHT: # 오른쪽 방향키인 경우
                MOVE_RIGHT = False # 오른쪽 이동 기능 비활성화

    keys = pg.key.get_pressed() # 키보드에서 눌린 키들
    # 왼쪽 ALT키가 눌려있고, 플레이어가 점프중이 아니고, 발판 위에 있으면
    if (keys[pg.K_LALT] or keys[pg.K_SPACE]) and not JUMPING and ON_FOOTHOLD:
        JUMPING = True # 점프 기능 활성화

    # <플레이어 이동 로직>
    
    # 좌우 이동 기능
    if MOVE_LEFT:
        player_rect = collision_rect(PLAYER_IMG, PLAYER_X - MOVE_SPEED, PLAYER_Y)
        object_right_tangent = check_collision_part(player_rect, part="left")
        # 플레이어가 좌측으로 충돌중이 아니고, 맵 좌측 끝부분 보다 멀리 있으면
        if PLAYER_X > 0 and not object_right_tangent:
            PLAYER_X -= MOVE_SPEED # 이동속도 수치만큼 왼쪽으로 이동
        else:
            if object_right_tangent:
                PLAYER_X -= (PLAYER_X - object_right_tangent)
        if not PLAYER_FLIP: # 플레이어 이미지가 반전되지 않은 상태이면
            PLAYER_IMG = pg.transform.flip(PLAYER_IMG, True, False) # 플레이어 이미지 반전
            PLAYER_FLIP = True # 반전 상태로 변경
    elif MOVE_RIGHT:
        player_rect = collision_rect(PLAYER_IMG, PLAYER_X + MOVE_SPEED, PLAYER_Y)
        object_left_tangent = check_collision_part(player_rect, part="right")
        # 플레이어가 우측으로 충돌중이 아니고, 맵 우측 끝부분 보다 안쪽에 있으면
        if PLAYER_X < (len(MAP_DATA_ARR[0]) * FOOTHOLD_TILE.get_width() - PLAYER_IMG.get_width()) and (
            not object_left_tangent):
            PLAYER_X += MOVE_SPEED # 이동속도 수치만큼 오른쪽으로 이동
        else:
            if object_left_tangent:
                PLAYER_X += (object_left_tangent - PLAYER_X - PLAYER_IMG.get_width())
        if PLAYER_FLIP: # 이미지 반전 상태이면
            PLAYER_IMG = pg.transform.flip(PLAYER_IMG, True, False) # 이미지 재반전
            PLAYER_FLIP = False # 반전 상태 초기화

    # 점프 기능
    if JUMPING: # 점프 기능이 활성화 되어있으면
        player_rect = collision_rect(PLAYER_IMG, PLAYER_X, PLAYER_Y - JUMP_POWER)
        object_bottom_tangent = check_collision_part(player_rect, part="top")
        if not object_bottom_tangent:
            PLAYER_Y -= JUMP_POWER # 현재 점프력 수치만큼 플레이어를 위로 이동
            JUMP_POWER -= GRAVITY # 점프력 수치를 중력만큼 감소(매 루프마다 뛰어오르는 속도가 서서히 감소)
        else:
            PLAYER_Y -= (PLAYER_Y - object_bottom_tangent)
            JUMP_POWER = 0
        
        if JUMP_POWER <= 0: # 현재 점프력 수치가 0이하면
            JUMPING = False # 점프 기능 비활성화
            ON_FOOTHOLD = False
            JUMP_POWER = INIT_JUMP_POWER # 점프력 수치 초기화
    # 중력 기능
    else:
        GRAVITY_ACC += GRAVITY # 중력 가속도 변수에 중력을 축적(매 루프마다 아래로 떨어지는 속도가 서서히 증가)
        player_rect = collision_rect(PLAYER_IMG, PLAYER_X, PLAYER_Y + GRAVITY_ACC)
        object = check_collision_part(player_rect, part="bottom")
        if not object:
            PLAYER_Y += GRAVITY_ACC # 현재 중력 가속도 수치만큼 플레이어를 아래로 이동
            ON_FOOTHOLD = False
        else:
            object_top_tangent, object_info = object[0], object[1]
            PLAYER_Y += (object_top_tangent - PLAYER_Y - PLAYER_IMG.get_height())
            ON_FOOTHOLD = True
            GRAVITY_ACC = 0 # 중력 가속도 초기화
            if object_info.direction == "left" or object_info.direction == "right":
                PLAYER_X += object_info.move_speed
            elif object_info.direction == "up":
                PLAYER_Y -= object_info.move_speed

    # <출력 로직>
    
    # 먼저 출력 화면에 배경 타일 이미지를 채워서 그리기
    arrX = np.arange(0, WINDOW_WIDTH, BG_TILE.get_width())
    arrY = np.arange(0, WINDOW_HEIGHT, BG_TILE.get_height())
    grid_arrX, grid_arrY = np.meshgrid(arrX, arrY, indexing='xy') # indexing='xy': 행렬을 좌표 형식으로 바꿔줌 (y, x) -> (x, y)
    for x, y in zip(grid_arrX.ravel(), grid_arrY.ravel()): # ravel(): 다차원 배열을 1차원 배열로 평탄화
        WINDOW.blit(BG_TILE, (x, y))

    # 맵을 x축, y축으로 당길 수치(평행이동할 수치)
    # (0, 0) 위치로부터 x축 방향으로는 화면 가로 중간 너비만큼 떨어진 곳에 가상의 '깃발'이 있고,
    # y축 방향으로는 화면 세로 중간 높이만큼 떨어진 곳에 가상의 '깃발'이 있다고 가정
    map_end_posX = len(MAP_DATA_ARR[0]) * FOOTHOLD_TILE.get_width() # 맵 끝 위치 x좌표(맵의 행에서 마지막 열 번호 * 타일 높이)
    if PLAYER_X >= map_end_posX - WINDOW_WIDTH / 2: # 플레이어 위치가 맵 오른쪽 끝에 다다를시
        PULL_X = map_end_posX - WINDOW_WIDTH # 화면 가로 중간너비 만큼만 덜 당기는 수치
    elif PLAYER_X >= WINDOW_WIDTH / 2: # 플레이어 위치가 깃발 위치보다 멀리있거나 같으면
        PULL_X = PLAYER_X - WINDOW_WIDTH / 2 # x축을 당길 수치 = 깃발 위치로부터 플레이어 위치까지의 x좌표 차이
    
    map_end_posY = len(MAP_DATA_ARR) * FOOTHOLD_TILE.get_height() # 맵 가장 아래쪽 y좌표(맵의 마지막 행 번호 * 타일 높이)
    if PLAYER_Y >= map_end_posY - WINDOW_HEIGHT / 2: # 플레이어 위치가 맵 아래쪽 끝에 다다를시
        PULL_Y = map_end_posY - WINDOW_HEIGHT # 화면 세로 중간높이 만큼만 덜 당기는 수치
    elif (PLAYER_Y >= WINDOW_HEIGHT / 2) or (PLAYER_Y <= WINDOW_HEIGHT / 2):
        PULL_Y = PLAYER_Y - WINDOW_HEIGHT / 2 # y축을 당길 수치 = 깃발 위치로부터 플레이어 위치까지의 y좌표 차이

    # **플레이어를 포함한 맵에 존재하는 모든 오브젝트는 좌표를 항상 (PULL_X, PULL_Y)만큼 평행이동 시킨 후 그린다.**
    # 맵을 출력 화면쪽으로 당겨서 그리기(평행이동)
    for foothold in Object_Info.FOOTHOLD_LAYER:
        if foothold.type == "horizontal": # 발판의 타입 속성명이 수평일 경우
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
            player_rect = collision_rect(PLAYER_IMG, PLAYER_X, PLAYER_Y) # 플레이어 충돌영역
            foothold_rect = collision_rect(FOOTHOLD_TILE, foothold.x, foothold.y) # 발판 충돌영역
            if player_rect.colliderect(foothold_rect): # 플레이어와 발판이 충돌 했는지
                if foothold.move_speed > 0: # 플레이어를 왼쪽에서 쳤으면
                    PLAYER_X = foothold_rect.right # 발판의 오른쪽 접선에 배치
                else: # 오른쪽에서 쳤으면
                    PLAYER_X = foothold_rect.left - PLAYER_IMG.get_width() # 왼쪽 접선에 배치
        
        elif foothold.type == "vertical": # 발판의 타입 속성명이 수직일 경우
            if foothold.direction == "up": # 발판의 방향 속성명이 위쪽일 경우(위쪽으로 올라갔다가 다시 내려옴)
                if foothold.init_y - foothold.y >= 1000: # 1000이상을 위쪽으로 이동했으면
                    foothold.move_speed *= -1 # 방향 전환
                elif foothold.init_y < foothold.y: # 초기 발판 위치보다 아래쪽에 있을 경우
                    foothold.move_speed *= -1 # 방향 재전환

            foothold.y -= foothold.move_speed # 발판의 이동속도 속성값 만큼 수직이동
        
        # 발판의 실제 위치를 (PULL_X, PULL_Y)만큼 평행이동 시키고 발판 이미지 그리기
        WINDOW.blit(FOOTHOLD_TILE, (foothold.x - PULL_X, foothold.y - PULL_Y))
    
    # 플레이어의 실제 위치를 (PULL_X, PULL_Y)만큼 평행이동 시키고 플레이어 이미지 그리기
    WINDOW.blit(PLAYER_IMG, (PLAYER_X - PULL_X, PLAYER_Y - PULL_Y))
    
    pg.display.update() # 화면 상태 업데이트

pg.quit()