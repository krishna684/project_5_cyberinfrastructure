/**
 * Track the target
 */
// Moves forward as long as signal is Good or Getting Better
function driveWhileHot (startSignal: number) {
    // Blue
    cuteBot.colorLight(cuteBot.RGBLights.ALL, 0x0000ff)
    // Drive forward
    cuteBot.motors(25, 25)
    // Drive for up to 1.5 seconds, checking signal every 200ms
    for (let index = 0; index < 8; index++) {
        basic.pause(200)
        // Safety stop
        if (isDistressMode) {
            return
        }
        newSignal = getSmoothedRSSI()
        // Arrived check
        if (newSignal >= RSSI_ARRIVED_THRESH) {
            // Exit, the main loop will catch the success
            return
        }
        // CRITICAL LOGIC: HOT OR COLD?
        // If signal dropped by more than 3 (weaker), we are going wrong way.
        // Example: Started at -70, now at -75. STOP.
        if (newSignal < startSignal - 3) {
            cuteBot.stopcar()
            // Flash Red briefly
            cuteBot.colorLight(cuteBot.RGBLights.ALL, 0xff0000)
            basic.pause(200)
            // Exit function to Trigger a re-scan
            return
        }
        // Update baseline (we are now at the new spot)
        startSignal = newSignal
    }
    cuteBot.stopcar()
}
function becomeVictim () {
    isDistressMode = true
    isRescuing = false
    cuteBot.stopcar()
    cuteBot.colorLight(cuteBot.RGBLights.ALL, 0xff0000)
    basic.showIcon(IconNames.Sad)
    radio.sendValue("ALERT", MY_SERIAL)
    control.runInParallel(function () {
        while (isDistressMode) {
            radio.sendValue("BEACON", MY_SERIAL);
            soundExpression.sad.play();
            if (Math.randomBoolean()) radio.sendValue("ALERT", MY_SERIAL);
            basic.pause(500);
        }
    });
}
// ====== HELPER: RSSI SMOOTHING ======
// Takes 5 readings and averages them to remove noise
function getSmoothedRSSI () {
    // Take 5 samples over 100ms
    for (let index = 0; index < 5; index++) {
        // Only add if we have a valid recent signal
        if (currentRSSI != -100) {
            sum += currentRSSI
            count += 1
        }
        basic.pause(20)
    }
    // If no signal, return a very low number
    if (count == 0) {
        return -100
    }
    return Math.round(sum / count)
}
function missionSuccess () {
    cuteBot.stopcar()
    for (let index = 0; index < 3; index++) {
        // Green
        cuteBot.colorLight(cuteBot.RGBLights.ALL, 0x00ff00)
        basic.showIcon(IconNames.Heart)
        basic.pause(200)
        cuteBot.colorLight(cuteBot.RGBLights.ALL, 0x000000)
        basic.pause(200)
    }
}
function becomeSafe () {
    isDistressMode = false
    radio.sendValue("SAFE", MY_SERIAL)
    resetSystem()
}
function resetSystem () {
    cuteBot.stopcar()
    calmLights()
    // Cooldown for accelerometer
    basic.pause(1000)
    isRescuing = false
    targetId = 0
}
// Scans Left and Right and returns which way is strongest
function smartScan () {
    cuteBot.stopcar()
    // Check Left
    cuteBot.motors(-35, 35)
    basic.pause(300)
    cuteBot.stopcar()
    // Wait for radio to settle
    basic.pause(200)
    leftScore = getSmoothedRSSI()
    // Turn all the way to Right (Left turn + Right turn = 600ms)
    cuteBot.motors(35, -35)
    basic.pause(600)
    cuteBot.stopcar()
    basic.pause(200)
    rightScore = getSmoothedRSSI()
    // Return to Center
    cuteBot.motors(-35, 35)
    basic.pause(300)
    cuteBot.stopcar()
    // Compare
    // Note: Closer to 0 is better. -60 is larger than -80.
    if (leftScore > rightScore + 2) {
        return "LEFT"
    } else if (rightScore > leftScore + 2) {
        return "RIGHT"
    } else {
        // Roughly equal
        return "CENTER"
    }
}
function startRescueRoutine () {
    isRescuing = true
    // Icon: Searching
    basic.showIcon(IconNames.Diamond)
    // Yellow
    cuteBot.colorLight(cuteBot.RGBLights.ALL, 0xffff00)
    searchStartTime = input.runningTime()
    while (isRescuing) {
        // Timeout check
        if (input.runningTime() - searchStartTime > MAX_SEARCH_TIME) {
            // Give up
            break;
        }
        // 1. Get a clean baseline reading
        initialSignal = getSmoothedRSSI()
        // 2. CHECK: Are we there yet?
        if (initialSignal >= RSSI_ARRIVED_THRESH) {
            missionSuccess()
            return
        }
        // 3. DECISION: Scan to find the best direction
        // We look Left, Center, Right
        bestDir = smartScan()
        // 4. Turn toward best direction
        if (bestDir == "LEFT") {
            // Turn Left
            cuteBot.motors(-30, 30)
            basic.pause(300)
        } else if (bestDir == "RIGHT") {
            // Turn Right
            cuteBot.motors(30, -30)
            basic.pause(300)
        }
        // If "CENTER", we don't turn, we just drive.
        // 5. DRIVE & MONITOR (Hot or Cold)
        // We drive forward for a bit, but check if signal drops.
        cuteBot.stopcar()
        basic.pause(100)
        driveWhileHot(initialSignal)
    }
    resetSystem()
}
// ==========================================
// === 1. RADIO HANDLER
// ==========================================
radio.onReceivedValue(function (name, value) {
    if (isDistressMode) {
        return;
    }
    incomingRSSI = radio.receivedPacket(RadioPacketProperty.SignalStrength)
    if (name == "ALERT") {
        if (!(isRescuing)) {
            targetId = value
            // Start the new logic
            startRescueRoutine()
        }
    } else if (name == "BEACON") {
        if (targetId == 0 || value == targetId) {
            // Update the raw global variable
            currentRSSI = incomingRSSI
            lastBeaconTime = input.runningTime()
        }
    } else if (name == "SAFE") {
        if (value == targetId) {
            resetSystem()
        }
    }
})
function calmLights () {
    cuteBot.colorLight(cuteBot.RGBLights.ALL, 0x00ff00)
    basic.showIcon(IconNames.Happy)
}
let z = 0
let lastBeaconTime = 0
let incomingRSSI = 0
let bestDir = ""
let initialSignal = 0
let searchStartTime = 0
let rightScore = 0
let leftScore = 0
let targetId = 0
let count = 0
let sum = 0
let isRescuing = false
let startSignal = 0
let newSignal = 0
let currentRSSI = 0
let MAX_SEARCH_TIME = 0
let RSSI_ARRIVED_THRESH = 0
let MY_SERIAL = 0
// ====== STATE VARIABLES ======
let isDistressMode = false
// ====== CONFIGURATION ======
let RADIO_GROUP = 17
MY_SERIAL = control.deviceSerialNumber()
// ====== TUNING CONSTANTS ======
// Louder threshold for sound
let SOUND_THRESHOLD = 80
// -50 is VERY close
RSSI_ARRIVED_THRESH = -50
// 10 seconds timeout
MAX_SEARCH_TIME = 10000
// Weights: We now trust Radio (RSSI) more than sound for direction
let W_SOUND = 0.3
let W_RSSI = 0.7
// Raw value from radio
currentRSSI = -100
// Setup
radio.setGroup(RADIO_GROUP)
radio.setTransmitPower(7)
calmLights()
// ==========================================
// === 2. VICTIM LOGIC (UNCHANGED)
// ==========================================
control.inBackground(function () {
    while (true) {
        z = input.acceleration(Dimension.Z)
        // Safety Check: Don't flip out if we are driving (Rescuing)
        if (z < -600 && !(isDistressMode) && !(isRescuing)) {
            becomeVictim()
        } else if (z > 200 && isDistressMode) {
            becomeSafe()
        }
        basic.pause(50)
    }
})
