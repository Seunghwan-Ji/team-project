import pygame as pg
import numpy as np
pg.init()

WINDOW_WIDTH, WINDOW_HEIGHT = 1200, 800
WINDOW = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pg.display.set_caption("Platformer Game")

FPS = pg.time.Clock()
MOVE_LEFT = False # 오른쪽 이동키 눌림 여부
MOVE_RIGHT = False # 왼쪽 이동키 눌림 여부
PLAYER_FLIP = False # 플레이어 이미지 반전(플레이어가 보고있는 방향)
GRAVITY = 0.5 # 중력
GRAVITY_ACC = 0 # 축적된 중력의 총 크기(중력 가속도)
MOVE_SPEED = 5 # 이동속도
INIT_JUMP_POWER = 15 # 점프력(초기값)
JUMP_POWER = INIT_JUMP_POWER # 현재 점프력
JUMPING = False # 점프중인 상태
ON_FOOTHOLD = False # 플레이어가 발판 위에 닿았는지 여부
COLLISION_TOP = False # 플레이어 머리 부분이 충돌했는지 여부
COLLISION_LEFT = False # 플레이어 왼쪽 부분이 충돌했는지 여부
COLLISION_RIGHT = False # 플레이어 오른쪽 부분이 충돌했는지 여부
RUN = True

# 전달 받은 이미지의 사이즈 조절
def change_image_size(img, size):
    return pg.transform.scale(img, (img.get_width() * size, img.get_height() * size))

# 배경 타일 이미지
BG_TILE = pg.image.load("img/bg.png")
BG_TILE = change_image_size(BG_TILE, 2)

# 발판 타일 이미지
FOOTHOLD_TILE = pg.image.load("img/floor.png")
FOOTHOLD_TILE = change_image_size(FOOTHOLD_TILE, 2)

# 플레이어 이미지
PLAYER_IMG = pg.image.load("img/player.png")
PLAYER_IMG = change_image_size(PLAYER_IMG, 2)

# 플레이어 초기 위치 설정
PLAYER_X, PLAYER_Y = 0, 0

# 초기 평행이동 수치 설정(맵의 x, y축을 출력 화면쪽으로 당길 수치)
PULL_X, PULL_Y = 0, 0

# 텍스트 맵 파일을 읽어와서 데이터를 리스트로 저장
with open('map_data_1.txt', 'r') as file:
    data = [list(map(int, line.split())) for line in file]

# 데이터 리스트를 넘파이 2차원 배열로 변환
MAP_DATA = np.array(data)

# 전달받은 이미지의 충돌 영역 정의(히트박스)
def collision_rect(img, x, y):
    return pg.Rect(x, y, img.get_width(), img.get_height())

# 전달받은 두 이미지의 충돌 감지 여부
def detect_collision(rect1, rect2):
    return rect1.colliderect(rect2)

# 충돌부위 검사
def check_collision_part(player_rect):
    collision_part = "" # 충돌부위
    contact_pos = () # 접점
    foothold_indices = np.argwhere(MAP_DATA == 1) # 발판이 있는 모든 위치의 행, 열 인덱스가 저장된 배열
    # 발판 위치를 실제 좌표로 변환(행 번호 * 발판 높이, 열 번호 * 발판 너비)
    foothold_positions = foothold_indices * (FOOTHOLD_TILE.get_height(), FOOTHOLD_TILE.get_width())
    # 모든 발판의 충돌 영역 리스트 생성
    foothold_rects = [collision_rect(FOOTHOLD_TILE, pos[1], pos[0]) for pos in foothold_positions]
    for foothold_rect in foothold_rects:
        if player_rect.colliderect(foothold_rect): # 플레이어가 발판과 충돌했는지 확인
            distance_x = player_rect.centerx - foothold_rect.centerx # x좌표 차이
            distance_y = player_rect.centery - foothold_rect.centery # y좌표 차이
            if abs(distance_x) > abs(distance_y): # x좌표 차이가 y좌표 차이보다 클 경우
                if distance_x > 0: # x좌표 차이가 양수이면
                    tangent = foothold_rect.right # 접선
                    contact_pos = (tangent, PLAYER_Y) # 접점
                    collision_part = "left"
                else:
                    tangent = foothold_rect.left - PLAYER_IMG.get_width()
                    contact_pos = (tangent, PLAYER_Y)
                    collision_part = "right"
            else:
                if distance_y > 0: # y좌표 차이가 양수이면
                    tangent = foothold_rect.bottom
                    contact_pos = (PLAYER_X, tangent)
                    collision_part = "top"
                else:
                    tangent = foothold_rect.top - PLAYER_IMG.get_height()
                    contact_pos = (PLAYER_X, tangent + 1.5)
                    collision_part = "bottom"
            break
    
    return collision_part, contact_pos

while RUN:
    FPS.tick(60) # 초당 화면에 그려낼 프레임 수(출력 횟수)

    # <충돌 처리 로직>

    player_rect = collision_rect(PLAYER_IMG, PLAYER_X, PLAYER_Y) # 플레이어 이미지의 충돌 영역 정의
    collision_part, contact_pos = check_collision_part(player_rect)
    
    if collision_part == "left":
        COLLISION_LEFT = True
        if (PLAYER_X, PLAYER_Y) != contact_pos:
            print("left")
            PLAYER_X, PLAYER_Y = contact_pos[0], contact_pos[1]
    else:
        COLLISION_LEFT = False
    
    if collision_part == "right":
        COLLISION_RIGHT = True
        if (PLAYER_X, PLAYER_Y) != contact_pos:
            print("right")
            PLAYER_X, PLAYER_Y = contact_pos[0], contact_pos[1]
    else:
        COLLISION_RIGHT = False
    
    if collision_part == "top":
        COLLISION_TOP = True
        JUMP_POWER = 0 # 점프력을 0으로 변경하고 점프 기능에서 더이상 뛰어오르지 못하게 한다.
        if (PLAYER_X, PLAYER_Y) != contact_pos:
            print("top")
            PLAYER_X, PLAYER_Y = contact_pos[0], contact_pos[1]
    else:
        COLLISION_TOP = False
    
    if collision_part == "bottom":
        ON_FOOTHOLD = True
        GRAVITY_ACC = 0 # 중력 가속도 초기화
        if (PLAYER_X, PLAYER_Y) != contact_pos:
            print("bottom")
            PLAYER_X, PLAYER_Y = contact_pos[0], contact_pos[1]
    else:
        ON_FOOTHOLD = False
    
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
    if keys[pg.K_LALT] and not JUMPING and ON_FOOTHOLD: # 왼쪽 ALT키가 눌려있고, 플레이어가 점프중이 아니고, 발판 위에 있으면
        JUMPING = True # 점프 기능 활성화

    # <플레이어 이동 로직>
    
    # 좌우 이동 기능
    if MOVE_LEFT:
        # 플레이어가 좌측으로 충돌중이 아니고, 맵 좌측 끝부분 보다 멀리 있으면
        if not COLLISION_LEFT and PLAYER_X > 0:
            PLAYER_X -= MOVE_SPEED # 이동속도 수치만큼 왼쪽으로 이동
        if not PLAYER_FLIP: # 플레이어 이미지가 반전되지 않은 상태이면
            PLAYER_IMG = pg.transform.flip(PLAYER_IMG, True, False) # 플레이어 이미지 반전
            PLAYER_FLIP = True # 반전 상태로 변경
    elif MOVE_RIGHT:
        # 플레이어가 우측으로 충돌중이 아니고, 맵 우측 끝부분 보다 안쪽에 있으면
        if not COLLISION_RIGHT and PLAYER_X < (
            len(MAP_DATA[0]) * FOOTHOLD_TILE.get_width() - PLAYER_IMG.get_width()):
            PLAYER_X += MOVE_SPEED # 이동속도 수치만큼 오른쪽으로 이동
        if PLAYER_FLIP: # 이미지 반전 상태이면
            PLAYER_IMG = pg.transform.flip(PLAYER_IMG, True, False) # 이미지 재반전
            PLAYER_FLIP = False # 반전 상태 초기화

    # 점프 기능
    if JUMPING: # 점프 기능이 활성화 되어있으면
        if not COLLISION_TOP:
            # print(JUMP_POWER)
            PLAYER_Y -= JUMP_POWER # 현재 점프력 수치만큼 플레이어를 위로 이동
            JUMP_POWER -= GRAVITY # 점프력 수치를 중력만큼 감소(매 루프마다 뛰어오르는 속도가 서서히 감소)
        if JUMP_POWER <= 0: # 현재 점프력 수치가 0이하면
            JUMPING = False # 점프 기능 비활성화
            JUMP_POWER = INIT_JUMP_POWER # 점프력 수치 초기화
    else:
        if not ON_FOOTHOLD: # 플레이어가 발판 위에 있지 않으면
            GRAVITY_ACC += GRAVITY # 중력 가속도 변수에 중력을 축적(매 루프마다 아래로 떨어지는 속도가 서서히 증가)
            PLAYER_Y += GRAVITY_ACC # 현재 중력 가속도 수치만큼 플레이어를 아래로 이동

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
    map_end_posX = len(MAP_DATA[0]) * FOOTHOLD_TILE.get_width() # 맵 끝 위치 x좌표
    if PLAYER_X >= map_end_posX - WINDOW_WIDTH / 2: # 플레이어 위치가 맵 오른쪽 끝에 다다를시
        PULL_X = map_end_posX - WINDOW_WIDTH # 화면 가로 중간너비 만큼만 덜 당기는 수치
    elif PLAYER_X >= WINDOW_WIDTH / 2: # 플레이어 위치가 깃발 위치보다 멀리있거나 같으면
        PULL_X = PLAYER_X - WINDOW_WIDTH / 2 # x축을 당길 수치 = 깃발 위치로부터 플레이어 위치까지의 x좌표 차이
    
    map_end_posY = len(MAP_DATA) * FOOTHOLD_TILE.get_height() # 맵 끝 위치 y좌표
    if PLAYER_Y >= map_end_posY - WINDOW_HEIGHT / 2: # 플레이어 위치가 맵 아래쪽 끝에 다다를시
        PULL_Y = map_end_posY - WINDOW_HEIGHT # 화면 세로 중간높이 만큼만 덜 당기는 수치
    elif PLAYER_Y >= WINDOW_HEIGHT / 2:
        PULL_Y = PLAYER_Y - WINDOW_HEIGHT / 2 # y축을 당길 수치 = 깃발 위치로부터 플레이어 위치까지의 y좌표 차이

    # **플레이어를 포함한 맵에 존재하는 모든 오브젝트는 좌표를 항상 (PULL_X, PULL_Y)만큼 평행이동 시킨 후 그린다.**
    # 맵을 출력 화면쪽으로 당겨서 그리기(평행이동)
    foothold_indices = np.argwhere(MAP_DATA == 1)
    foothold_positions = foothold_indices * (FOOTHOLD_TILE.get_height(), FOOTHOLD_TILE.get_width())
    for pos in foothold_positions:
        x, y = pos[1], pos[0]
        # 발판의 실제 위치를 (PULL_X, PULL_Y)만큼 평행이동 시키고 발판 이미지 그리기
        WINDOW.blit(FOOTHOLD_TILE, (x - PULL_X, y - PULL_Y))
    
    # 플레이어의 실제 위치를 (PULL_X, PULL_Y)만큼 평행이동 시키고 플레이어 이미지 그리기
    WINDOW.blit(PLAYER_IMG, (PLAYER_X - PULL_X, PLAYER_Y - PULL_Y))
    
    pg.display.update() # 화면 상태 업데이트

pg.quit()