# 🚑 Micro:bit Search & Rescue Swarm

This project turns a group of **Elecfreaks Smart Cutebots** (powered by BBC Micro:bits) into an autonomous swarm. If one robot "crashes" (flips over), it broadcasts a distress signal. The other robots immediately stop what they are doing, lock onto the signal, and autonomously drive to the victim to "rescue" them.

## 🛠 Hardware Overview

This system relies on two distinct pieces of hardware working together:

### 1\. The Brain: BBC Micro:bit

The Micro:bit is the microcontroller inserted into the robot. It handles:

  * **Radio (2.4GHz):** Sends and receives data packets between robots without needing WiFi or Bluetooth pairing.
  * **Accelerometer (Gyro):** Detects if the robot has flipped over (Z-axis gravity detection).
  * **Logic:** Runs the TypeScript/JavaScript code to make decisions.

### 2\. The Body: Elecfreaks Smart Cutebot

The Cutebot is the chassis that the Micro:bit plugs into. It handles:

  * **Motors:** Differential drive (left and right wheels) for turning and moving.
  * **NeoPixels:** RGB lights used to communicate status (Red = Help, Green = Safe, Blue = Driving).
  * **Sonar/Sensors:** (Optional) Used for obstacle avoidance, though this specific code relies on Radio.

-----

## 🧩 The Logic: How the Code Works

The code is built on a **State Machine**. At any given moment, a robot is in one of three states:

1.  **Idle:** Waiting for a command.
2.  **Victim (Distress Mode):** Has flipped over and is broadcasting for help.
3.  **Rescuer (Search Mode):** Is actively tracking a victim.

### 1\. The Radio Protocol

The robots speak a custom language using `radio.sendValue(name, value)`.

  * `"ALERT"`: Sent once when a robot crashes. Contains the Victim's Serial Number.
  * `"BEACON"`: Sent continuously by the victim. Rescuers measure the **Signal Strength (RSSI)** of this packet to estimate distance.
  * `"SAFE"`: Sent when the victim is flipped back upright, telling rescuers to stand down.

### 2\. The Victim Logic (The "Flip" Trigger)

The code runs a background loop checking the **Z-axis acceleration**.

  * **Normal Driving:** Gravity pulls down (\~ +1000).
  * **Upside Down:** Gravity pulls "up" relative to the chip (\< -600).
  * **The Trigger:**
    ```typescript
    if (z < -600 && !isRescuing) { becomeVictim(); }
    ```
    *Note: The `!isRescuing` check is crucial. It prevents a Rescuer from accidentally triggering its own alarm while driving over bumps.*

### 3\. The Rescuer Logic (The "Hot or Cold" Algorithm)

This is the most complex part of the code. Radio signals are messy; they bounce off walls (multipath interference). To handle this, we use **Smoothing** and **Active Feedback**.

#### A. RSSI Smoothing

Raw radio signals jump around (e.g., -60, -82, -55). If the robot reacted to every jump, it would jitter.
**The Solution:** The `getSmoothedRSSI()` function takes 5 rapid readings (over 100ms) and calculates the **average**. This provides a reliable "true" signal strength.

#### B. The Search Loop

The robot does not use GPS. It uses relative signal strength.

1.  **Scan:** The robot turns Left, checks signal. Turns Right, checks signal.
2.  **Compare:** It calculates which direction had the stronger (higher) signal (e.g., -50 is stronger than -90).
3.  **Orient:** It turns toward the strongest signal.

#### C. "Drive While Hot" (Feedback Loop)

Once the robot picks a direction, it drives forward. However, it doesn't just drive blindly. It checks the signal constantly:

  * **Hotter (Signal Increasing):** Keep driving\!
  * **Colder (Signal Dropping):** Stop immediately\! We are driving away from the target. The robot stops and restarts the "Scan" phase.

-----

## 📜 Code Structure Breakdown

| Function | Purpose |
| :--- | :--- |
| `radio.onReceivedValue` | The "Ears." Listens for ALERTS. If an ALERT is heard, it saves the Victim's ID and triggers `startRescueRoutine()`. |
| `control.inBackground` | The "Inner Ear." Constantly checks orientation (gravity). If upside down, triggers `becomeVictim()`. |
| `startRescueRoutine()` | The main loop for Rescuers. Controls the flow of Scanning -\> Driving -\> Checking Success. |
| `smartScan()` | Turns the robot mechanically to physically point the antenna in different directions to find the strongest signal source. |
| `driveWhileHot()` | Drives forward but includes an "Emergency Brake." If the signal gets worse (weaker) by a margin of 3, it aborts the drive. |
| `missionSuccess()` | Triggers when Signal Strength \> -50 (approx 15cm distance). Performs a "Victory Dance." |

-----

## 🚦 LED Status Codes

The Cutebot uses its headlights to tell you what it is thinking:

  * 🟢 **Green + Smile:** Idle / Safe. System is normal.
  * 🔴 **Red + Sad Face:** VICTIM. I have crashed and need help.
  * 🟡 **Yellow + Diamond:** ACKNOWLEDGED. I heard a cry for help and I am scanning.
  * 🔵 **Blue:** DRIVING. I am locked onto the signal and moving towards it.
  * 🚨 **Flash Red:** MISTAKE. I drove the wrong way (signal got weaker), correcting course.

-----

Based on your repository URL, here is the updated **How to Run** section for your `README.md`.

Since this project is hosted on GitHub, the easiest way for others to run it is by importing the repository URL directly into the MakeCode editor.

### 🚀 How to Run

There are two ways to run this project: using the online MakeCode editor (easiest) or compiling locally.

#### Method 1: Open Directly in MakeCode (Recommended)

You don't need to manually download files. You can pull the code directly from GitHub into the editor.

1.  Open [makecode.microbit.org](https://makecode.microbit.org/).
2.  Click the **Import** button on the home screen.
3.  Select **Import URL**.
4.  Paste the repository URL:
    ```text
    https://github.com/krishna684/project_5_cyberinfrastructure
    ```
5.  Click **Go**. The project will load into the editor automatically.
6.  Click the **Download** button in the bottom left.
7.  Connect your Micro:bit to your computer via USB.
8.  Drag and drop the downloaded `.hex` file onto the `MICROBIT` drive.

#### Method 2: Manual Installation (Git)

If you prefer to work with the source files locally:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/krishna684/project_5_cyberinfrastructure.git
    ```
2.  **Import to MakeCode:**
      * Go to [makecode.microbit.org](https://makecode.microbit.org/).
      * Click **Import** -\> **Import File**.
      * Select the `pxt.json` or `main.ts` file from the cloned folder.
3.  **Flash:**
      * Follow the standard download procedure to flash the code to your Micro:bit.

#### Method 3: Command Line (PXT CLI)

For advanced users who want to build the project using the PXT command line tools:

1.  Install [Node.js](https://nodejs.org/en/).
2.  Install the PXT command line tool:
    ```bash
    npm install -g pxt
    ```
3.  Clone and install dependencies:
    ```bash
    git clone https://github.com/krishna684/project_5_cyberinfrastructure.git
    cd project_5_cyberinfrastructure
    pxt install
    ```
4.  Build and Deploy:
    Ensure your Micro:bit is connected via USB, then run:
    ```bash
    pxt deploy
    ```
