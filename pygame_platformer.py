import pygame as pg
import numpy as np
pg.init()

WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600
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

# 맵 형태
MAP_DATA = np.array(
    [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
     [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
     [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
     [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0],
     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0],
     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
     [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
     [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]
    )

# 전달받은 이미지의 충돌 영역 정의(히트박스)
def collision_rect(img, x, y):
    return pg.Rect(x, y, img.get_width(), img.get_height())

# 전달받은 두 이미지의 충돌 감지 여부
def detect_collision(rect1, rect2):
    return rect1.colliderect(rect2)

# 플레이어가 발판 위에 닿았는지 여부를 검사
def check_on_foothold(player_rect):
    foothold_indices = np.argwhere(MAP_DATA == 1) # 발판이 있는 모든 위치의 행, 열 인덱스가 저장된 배열
    # 발판 위치를 실제 좌표로 변환(행 번호 * 발판 높이, 열 번호 * 발판 너비)
    foothold_positions = foothold_indices * (FOOTHOLD_TILE.get_height(), FOOTHOLD_TILE.get_width())
    # 모든 발판의 충돌 영역 리스트 생성
    foothold_rects = [collision_rect(FOOTHOLD_TILE, pos[1], pos[0]) for pos in foothold_positions]
    for foothold_rect in foothold_rects:
        if player_rect.colliderect(foothold_rect): # 플레이어가 발판과 충돌했는지 확인
            # 충돌 부분이 플레이어의 아랫부분과 발판의 윗부분인지 확인
            if foothold_rect.top - 50 <= player_rect.bottom <= foothold_rect.top + 50: # 오차 범위 적용
                return True

while RUN:
    FPS.tick(60) # 초당 화면에 그려낼 프레임 수(출력 횟수)

    # <충돌 처리 로직>
    
    player_rect = collision_rect(PLAYER_IMG, PLAYER_X, PLAYER_Y) # 플레이어 이미지의 충돌 영역 정의
    is_on_foothold = check_on_foothold(player_rect) # 플레이어가 발판 위에 닿았는지 여부

    if is_on_foothold: # 반환값이 True이면
        ON_FOOTHOLD = True # 발판에 닿은 상태로 변경
        GRAVITY_ACC = 0 # 중력 가속도 초기화
    else:
        ON_FOOTHOLD = False # 발판에 닿지 않은 상태로 변경
    
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
    if MOVE_LEFT and PLAYER_X > 0: # 왼쪽 이동 기능이 활성화 되어있고, 플레이어가 맵 좌측 끝부분 보다 멀리 있으면
        PLAYER_X -= MOVE_SPEED # 이동속도 수치만큼 왼쪽으로 이동
        if not PLAYER_FLIP: # 플레이어 이미지가 반전되지 않은 상태이면
            PLAYER_IMG = pg.transform.flip(PLAYER_IMG, True, False) # 플레이어 이미지 반전
            PLAYER_FLIP = True # 반전 상태로 변경
    elif MOVE_RIGHT and PLAYER_X < (len(MAP_DATA[0]) * FOOTHOLD_TILE.get_width() - PLAYER_IMG.get_width()): # 플레이어가 맵 우측 끝부분 보다 안쪽에 있으면
        PLAYER_X += MOVE_SPEED # 이동속도 수치만큼 오른쪽으로 이동
        if PLAYER_FLIP: # 이미지 반전 상태이면
            PLAYER_IMG = pg.transform.flip(PLAYER_IMG, True, False) # 이미지 재반전
            PLAYER_FLIP = False # 반전 상태 초기화

    # 점프 기능
    if JUMPING: # 점프 기능이 활성화 되어있으면
        PLAYER_Y -= JUMP_POWER # 현재 점프력 수치만큼 플레이어를 위로 이동
        JUMP_POWER -= GRAVITY # 점프력 수치를 중력만큼 감소(매 루프마다 뛰어오르는 속도가 서서히 감소)
        if JUMP_POWER == 0: # 현재 점프력 수치가 0이 되었으면
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