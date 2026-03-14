import math
import random
import cvzone
import cv2
from cvzone.HandTrackingModule import HandDetector
import time

def detectGesture(hand):
    fingers = detector.fingersUp(hand)
    lm = hand["lmList"]

    # 获取关键点坐标
    thumb_tip = lm[4]
    index_tip = lm[8]
    middle_tip = lm[12]
    pinky_tip = lm[20]
    wrist = lm[0]

    # 计算手指高度
    index_height = wrist[1] - index_tip[1]
    middle_height = wrist[1] - middle_tip[1]

    # 手势1: 比耶 → 暂停
    if fingers == [0, 1, 1, 0, 0] and index_height > 30 and middle_height > 30:
        return "STOP"

    # 手势2: 蜘蛛侠 → 开始/继续
    if fingers == [1, 1, 0, 0, 1] and index_height > 50:
        return "START"

    # 手势3: 摇滚手势 → 跳过食物
    if fingers == [1, 0, 0, 0, 1]:
        thumb_pinky_dist = math.dist(thumb_tip[:2], pinky_tip[:2])
        base_dist = math.dist(wrist[:2], lm[9][:2])
        
        if thumb_pinky_dist > base_dist * 0.7:
            return "ROCK"

    return "NONE"

class SnakeGame:
    def __init__(self, food_path):
        self.left_points = []
        self.right_points = []
        self.left_lengths = []
        self.right_lengths = []
        self.currentLeftLength = 0
        self.currentRightLength = 0
        self.allowedLength = 200
        self.previousLeftHead = (0, 0)
        self.previousRightHead = (0, 0)

        self.imgFood = cv2.imread(food_path, cv2.IMREAD_UNCHANGED)
        self.hFood, self.wFood, _ = self.imgFood.shape
        self.foodPoint = (0, 0)
        self.randomFoodLocation()

        self.score = 0
        self.startTime = time.time()

        self.lastSkipTime = 0
        self.skipCooldown = 1
        self.trailDuration = 1.0

    def randomFoodLocation(self):
        self.foodPoint = (
            random.randint(100, 1180),
            random.randint(100, 620)
        )

    def update(self, imgMain, leftHeadPoint, rightHeadPoint):
        current_time = time.time()

        # 更新左手轨迹
        if leftHeadPoint:
            self._updateHandTrail(leftHeadPoint, current_time, is_left=True)
            
            # 检测左手是否吃到食物
            if self._checkFoodCollision(leftHeadPoint):
                self._handleFoodEaten()

        # 更新右手轨迹
        if rightHeadPoint:
            self._updateHandTrail(rightHeadPoint, current_time, is_left=False)
            
            # 检测右手是否吃到食物
            if self._checkFoodCollision(rightHeadPoint):
                self._handleFoodEaten()

        # 清理过期轨迹点
        self._cleanOldPoints(current_time)
        
        # 控制蛇身长度
        self._controlSnakeLength()

        # 绘制蛇身和蛇头
        self._drawSnake(imgMain, current_time)

        return imgMain

    def _updateHandTrail(self, headPoint, current_time, is_left):
        cx, cy = headPoint
        points = self.left_points if is_left else self.right_points
        lengths = self.left_lengths if is_left else self.right_lengths
        prevHead = self.previousLeftHead if is_left else self.previousRightHead
        
        px, py = prevHead
        points.append([cx, cy, current_time])
        dist = math.dist((cx, cy), (px, py))
        lengths.append(dist)
        
        if is_left:
            self.currentLeftLength += dist
            self.previousLeftHead = (cx, cy)
        else:
            self.currentRightLength += dist
            self.previousRightHead = (cx, cy)

    def _checkFoodCollision(self, headPoint):
        cx, cy = headPoint
        fx, fy = self.foodPoint
        return (fx - self.wFood // 2 < cx < fx + self.wFood // 2 and 
                fy - self.hFood // 2 < cy < fy + self.hFood // 2)

    def _handleFoodEaten(self):
        self.randomFoodLocation()
        self.allowedLength += 40
        self.score += 1

    def _cleanOldPoints(self, current_time):
        # 清理左手过期点
        while (self.left_points and 
               current_time - self.left_points[0][2] > self.trailDuration):
            if self.left_lengths:
                self.currentLeftLength -= self.left_lengths.pop(0)
            self.left_points.pop(0)

        # 清理右手过期点
        while (self.right_points and 
               current_time - self.right_points[0][2] > self.trailDuration):
            if self.right_lengths:
                self.currentRightLength -= self.right_lengths.pop(0)
            self.right_points.pop(0)

    def _controlSnakeLength(self):
        # 控制左手蛇长
        while self.currentLeftLength > self.allowedLength and self.left_lengths:
            self.currentLeftLength -= self.left_lengths.pop(0)
            if self.left_points:
                self.left_points.pop(0)

        # 控制右手蛇长
        while self.currentRightLength > self.allowedLength and self.right_lengths:
            self.currentRightLength -= self.right_lengths.pop(0)
            if self.right_points:
                self.right_points.pop(0)

    def _drawSnake(self, imgMain, current_time):
        # 绘制左手蛇身（蓝色系）
        for i in range(1, len(self.left_points)):
            time_factor = 1.0 - (current_time - self.left_points[i][2]) / self.trailDuration
            color_intensity = int(255 * time_factor)
            color = (color_intensity, color_intensity // 2, 0)  # 蓝到青
            thickness = max(5, int(20 * time_factor))
            
            cv2.line(imgMain, tuple(self.left_points[i-1][:2]), 
                     tuple(self.left_points[i][:2]), color, thickness)

        # 绘制右手蛇身（红色系）
        for i in range(1, len(self.right_points)):
            time_factor = 1.0 - (current_time - self.right_points[i][2]) / self.trailDuration
            color_intensity = int(255 * time_factor)
            color = (0, color_intensity // 2, color_intensity)  # 红到橙
            thickness = max(5, int(20 * time_factor))
            
            cv2.line(imgMain, tuple(self.right_points[i-1][:2]), 
                     tuple(self.right_points[i][:2]), color, thickness)

        # 绘制蛇头
        if self.left_points:
            cv2.circle(imgMain, tuple(self.left_points[-1][:2]), 20, (255, 100, 100), cv2.FILLED)
            cv2.circle(imgMain, tuple(self.left_points[-1][:2]), 20, (255, 255, 255), 2)

        if self.right_points:
            cv2.circle(imgMain, tuple(self.right_points[-1][:2]), 20, (100, 100, 255), cv2.FILLED)
            cv2.circle(imgMain, tuple(self.right_points[-1][:2]), 20, (255, 255, 255), 2)

    def skipFood(self):
        currentTime = time.time()
        if currentTime - self.lastSkipTime > self.skipCooldown:
            self.randomFoodLocation()
            self.lastSkipTime = currentTime
            return True
        return False

    def drawFood(self, imgMain):
        fx, fy = self.foodPoint
        return cvzone.overlayPNG(imgMain, self.imgFood, 
                                 (fx - self.wFood // 2, fy - self.hFood // 2))

    def drawUI(self, imgMain, gameRunning, skipMessageTime):
        currentTime = time.time()
        
        # 分数
        cvzone.putTextRect(imgMain, f"Score: {self.score}", [50, 60], scale=2, thickness=3)
        
        # 时间
        elapsed = int(currentTime - self.startTime)
        mm, ss = elapsed // 60, elapsed % 60
        cvzone.putTextRect(imgMain, f"Time: {mm:02d}:{ss:02d}", [50, 120], scale=2, thickness=3)
        
        # 状态提示
        if not gameRunning:
            cvzone.putTextRect(imgMain, "STOP", [50, 180], scale=2, thickness=2)
        elif currentTime - skipMessageTime < 1.0:
            cvzone.putTextRect(imgMain, "SKIP", [50, 180], scale=2, thickness=2)
            
        return imgMain

# 初始化
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

detector = HandDetector(detectionCon=0.8, maxHands=2)
game = SnakeGame("donut.png")

gameRunning = True
skipMessageTime = 0
lastGesture = "NONE"

# 主循环
while True:
    success, img = cap.read()
    img = cv2.flip(img, 1)

    hands, img = detector.findHands(img, flipType=False)

    currentGesture = "NONE"
    currentTime = time.time()

    leftHandPoint = None
    rightHandPoint = None

    if hands:
        for hand in hands:
            handType = hand["type"]
            index_tip = tuple(hand["lmList"][8][:2])

            if handType == "Left":
                leftHandPoint = index_tip
            else:
                rightHandPoint = index_tip

            # 检测手势
            gesture = detectGesture(hand)
            if gesture != "NONE":
                currentGesture = gesture

        # 处理手势变化
        if currentGesture != lastGesture:
            if currentGesture == "START":
                gameRunning = True
            elif currentGesture == "STOP":
                gameRunning = False

            if gameRunning and currentGesture == "ROCK":
                if game.skipFood():
                    skipMessageTime = currentTime

        lastGesture = currentGesture

        if gameRunning:
            img = game.update(img, leftHandPoint, rightHandPoint)
    else:
        lastGesture = "NONE"

    # 绘制食物和UI
    img = game.drawFood(img)
    img = game.drawUI(img, gameRunning, skipMessageTime)

    # 显示当前手势
    cvzone.putTextRect(img, f"Gesture: {currentGesture}", [50, 650], scale=1, thickness=2)

    cv2.imshow("Snake Game", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()