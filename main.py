# ============== Radio setup ==============
RADIO_GROUP = 17
# Must be same on all bots
radio.set_group(RADIO_GROUP)
radio.set_transmit_power(7)
# Max power
myId = control.device_serial_number()
# ============== Message types ==============
MSG_ALERT = "ALERT"
MSG_BEACON = "BEACON"
MSG_DONE = "DONE"
# ============== Motion / Scan Constants ==============
TURN_SPEED = 40
# Speed for initial scan
SCAN_MS = 600
# Duration to listen per side (ms)
SEEK_MS = 400
# Duration to turn towards target (ms)
SETTLE_MS = 100
# Pause to stabilize (ms)
# ============== Approach Constants ==============
SLOW_FORWARD_SPEED = 25
SOUND_APPROACH_THRESH = 60
# Stop if quieter than this
APPROACH_MAX_MS = 5000
# Give up after 5 seconds
QUIET_STOP_MS = 500
# Stop if quiet for 0.5s
# ============== Re-scan Constants ==============
RESCAN_PERIOD_MS = 800
# Re-check heading every 0.8s
SCAN_MS_SHORT = 300
SEEK_MS_SHORT = 250
APPROACH_TURN_SPEED = 35
# ============== Sensor Weights (0–100 scaled) ==============
SOUND_WEIGHT = 0.7
# Trust ears more
RSSI_WEIGHT = 0.3
# Trust radio less
# ============== Global State Variables ==============
isDistressMode = False
scanning = False
scanningAnimOn = False
# Target tracking
targetId = 0
currentRSSI = -128
lastBeaconTime = 0
BEACON_TIMEOUT_MS = 2000
# =============================================
# =========== PART 1: DISTRESS MODE ===========
# =============================================
# Orientation monitor – runs forever

def on_forever():
    global isDistressMode
    accelZ = input.acceleration(Dimension.Z)
    # Flip down → distress
    # Flip back up → exit distress
    if accelZ < -600 and not isDistressMode:
        enterDistressMode()
    elif accelZ > 200 and isDistressMode:
        exitDistressMode()
    basic.pause(50)
basic.forever(on_forever)

def enterDistressMode():
    global isDistressMode, scanning
    if isDistressMode:
        return
    isDistressMode = True
    scanning = False
    # Stop rescuing others if I am hurt
    cuteBot.stopcar()
    sadLights()
    radio.send_value(MSG_ALERT, myId)
    # Continuous distress loop in background
    
    def on_in_background():
        while isDistressMode:
            # Broadcast beacon for RSSI tracking
            radio.send_value(MSG_BEACON, myId)
            # Play sad sound (non-blocking is nicer, but play is okay)
            soundExpression.sad.play()
            # Randomly re-send ALERT packet
            if Math.random_boolean():
                radio.send_value(MSG_ALERT, myId)
            basic.pause(600)
    control.in_background(on_in_background)
    
def exitDistressMode():
    global isDistressMode
    isDistressMode = False
    radio.send_value(MSG_DONE, myId)
    calmLights()
# Manual shake trigger

def on_gesture_shake():
    global isDistressMode
    if not isDistressMode:
        enterDistressMode()
        # Force sadness for at least 3 seconds on shake
        
        def on_in_background2():
            basic.pause(3000)
            if isDistressMode and input.acceleration(Dimension.Z) > -200:
                exitDistressMode()
        control.in_background(on_in_background2)
        
input.on_gesture(Gesture.SHAKE, on_gesture_shake)

# =============================================
# =========== PART 2: RESCUER LOGIC ===========
# =============================================

def on_received_value(name, value):
    global isDistressMode, scanning, currentRSSI, lastBeaconTime, targetId
    rssi = radio.received_packet(RadioPacketProperty.SIGNAL_STRENGTH)
    if name == MSG_ALERT:
        senderId = value
        if senderId != myId and not isDistressMode and not scanning:
            # Start rescue!
            respondToAlert(senderId)
    elif name == MSG_BEACON:
        # Only track the robot we are looking for
        if targetId == 0 or value == targetId:
            currentRSSI = rssi
            lastBeaconTime = input.running_time()
    elif name == MSG_DONE:
        if value == targetId:
            # Victim is happy, stop rescue
            scanning = False
            targetId = 0
            cuteBot.stopcar()
            calmLights()
radio.on_received_value(on_received_value)

def respondToAlert(senderId2: number):
    global scanning, targetId, TURN_SPEED
    scanning = True
    targetId = senderId2
    scanningLights()
    basic.pause(200)
    # 1. Scan left/right to find direction
    leftScore = scanSide(-TURN_SPEED, TURN_SPEED, SCAN_MS)
    basic.pause(SETTLE_MS)
    rightScore = scanSide(TURN_SPEED, -TURN_SPEED, SCAN_MS)
    basic.pause(SETTLE_MS)
    # 2. Pivot towards winner
    if leftScore > rightScore:
        cuteBot.motors(-TURN_SPEED, TURN_SPEED)
        basic.pause(SEEK_MS)
    else:
        cuteBot.motors(TURN_SPEED, -TURN_SPEED)
        basic.pause(SEEK_MS)
    cuteBot.stopcar()
    # 3. Empathize and approach
    sadLights()
    soundExpression.sad.play()
    approachWhileLoudWithRescan()
    # 4. Reset
    scanningAnimationStop()
    scanning = False
    targetId = 0
    calmLights()
# Scan one direction and return a score combining sound & RSSI
def scanSide(leftSpeed: number, rightSpeed: number, duration: number):
    cuteBot.motors(leftSpeed, rightSpeed)
    soundMax = 0
    rssiMax = -128
    t0 = input.running_time()
    while input.running_time() - t0 < duration:
        s = input.sound_level()
        if s > soundMax:
            soundMax = s
        if input.running_time() - lastBeaconTime < BEACON_TIMEOUT_MS:
            if currentRSSI > rssiMax:
                rssiMax = currentRSSI
        basic.pause(10)
    cuteBot.stopcar()
    soundScore = normSound(soundMax)
    rssiScore = normRssi(rssiMax)
    return SOUND_WEIGHT * soundScore + RSSI_WEIGHT * rssiScore
# Approach loop with periodic re-scan ("wiggle")
def approachWhileLoudWithRescan():
    tStart = input.running_time()
    quietStart = 0
    lastRescan = input.running_time()
    cuteBot.motors(SLOW_FORWARD_SPEED, SLOW_FORWARD_SPEED)
    while input.running_time() - tStart < APPROACH_MAX_MS:
        # Safety: if we get flipped during rescue, enter distress
        if isDistressMode:
            cuteBot.stopcar()
            return
        # Volume check
        t = input.sound_level()
        if t >= SOUND_APPROACH_THRESH:
            quietStart = 0
        else:
            if quietStart == 0:
                quietStart = input.running_time()
            if input.running_time() - quietStart >= QUIET_STOP_MS:
                break
        # Periodic re-scan to adjust heading
        if input.running_time() - lastRescan >= RESCAN_PERIOD_MS:
            cuteBot.stopcar()
            briefRescanAndAdjust()
            cuteBot.motors(SLOW_FORWARD_SPEED, SLOW_FORWARD_SPEED)
            lastRescan = input.running_time()
        basic.pause(20)
    cuteBot.stopcar()
def briefRescanAndAdjust():
    global APPROACH_TURN_SPEED
    scanningLights()
    # Quick left/right check
    left = scanSide(-APPROACH_TURN_SPEED, APPROACH_TURN_SPEED, SCAN_MS_SHORT)
    basic.pause(50)
    right = scanSide(APPROACH_TURN_SPEED, -APPROACH_TURN_SPEED, SCAN_MS_SHORT)
    if left > right:
        cuteBot.motors(-APPROACH_TURN_SPEED, APPROACH_TURN_SPEED)
        basic.pause(SEEK_MS_SHORT)
    else:
        cuteBot.motors(APPROACH_TURN_SPEED, -APPROACH_TURN_SPEED)
        basic.pause(SEEK_MS_SHORT)
    cuteBot.stopcar()
    sadLights()
# ============== Normalization Helpers ==============
def normSound(v: number):
    if v < 0:
        v = 0
    if v > 255:
        v = 255
    return Math.round(v * 100 / 255)
def normRssi(rssi2: number):
    MIN = -95
    MAX = -45
    if rssi2 < MIN:
        rssi2 = MIN
    if rssi2 > MAX:
        rssi2 = MAX
    return Math.round((rssi2 - MIN) * 100 / (MAX - MIN))
# ============== LED / Display Control ==============
def calmLights():
    scanningAnimationStop()
    cuteBot.color_light(cuteBot.RGBLights.ALL, 0x00ff00)
    basic.show_icon(IconNames.HAPPY)
def sadLights():
    scanningAnimationStop()
    cuteBot.color_light(cuteBot.RGBLights.ALL, 0xff0000)
    basic.show_icon(IconNames.SAD)
def scanningLights():
    cuteBot.color_light(cuteBot.RGBLights.ALL, 0xffff00)
    scanningAnimationStart()
def scanningAnimationStart():
    global scanningAnimOn
    if scanningAnimOn:
        return
    scanningAnimOn = True
    
    def on_in_background3():
        frames = [images.create_image("""
                . . . . .
                . . # . .
                . # . # .
                . . . . .
                . . . . .
                """),
            images.create_image("""
                . . . . .
                . . . . .
                . . # . .
                . . . . .
                . . . . .
                """),
            images.create_image("""
                . . . . .
                . . . . .
                . # . # .
                . . # . .
                . . . . .
                """)]
        i = 0
        while scanningAnimOn:
            frames[i].show_image(0)
            i = (i + 1) % len(frames)
            basic.pause(120)
        basic.clear_screen()
    control.in_background(on_in_background3)
    
def scanningAnimationStop():
    global scanningAnimOn
    scanningAnimOn = False
# ============== Main startup ==============
calmLights()