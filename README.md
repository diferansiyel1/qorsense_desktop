# QorSense Desktop - Mission-Control v3.0

**QorSense Desktop** is a high-performance, hardware-locked predictive maintenance and sensor analytics platform designed for industrial environments. Built with **Python (PyQt6)**, it offers real-time monitoring via **Modbus TCP/RTU**, advanced signal analysis, and a secure licensing system.

## 🚀 Key Features

### 1. Robust Data Acquisition
- **Modbus TCP & RTU**: Native support for industrial sensors (e.g., Hamilton VisiWater/Arc) over Ethernet or RS485/Serial.
- **Legacy Support**: Import and analyze historical data from CSV/Excel files.
- **Smart Connection Dialog**: Auto-scans COM ports and provides pre-configured settings for standard sensors.

### 2. Advanced Signal Analytics
- **Real-Time Health Engine**: 
  - **DFA (Detrended Fluctuation Analysis)**: Detects long-range correlations and fractal patterns.
  - **SNR (Signal-to-Noise Ratio)**: Monitors signal quality.
  - **Bias & Slope**: Quantifies drift and trend direction.
- **Automated Diagnosis**: Rule-based AI provides instant health scores (0-100), status updates, and actionable recommendations.

### 3. Hardware-Locked Security
- **Fingerprinting**: Generates unique Machine IDs based on hardware MAC address and hostname.
- **Secure Activation**: Requires a valid license key generated specifically for the target machine.
- **Offline Capable**: License verification works completely offline; no internet connection required.

### 4. Professional UI/UX
- **Fusion Dark Theme**: Modern, eye-friendly interface optimized for control room environments.
- **Oscilloscope View**: Smooth, real-time scrolling charts for live signal visualization.
- **Interactive Tools**: Field Explorer, Alarm Panel, and persistent application settings.

---

## 🏗 System Architecture

The application follows a modular architecture separating the UI, business logic, and core analysis engine:

```mermaid
graph TD
    User[User / Operator] -->|Interacts| UI[Desktop UI (PyQt6)]
    
    subgraph "Frontend Layer"
        UI -->|Config| ConnDialog[Connection Dialog]
        UI -->|View| Oscilloscope[PyQtGraph Charts]
        UI -->|Control| LicenseDlg[License Dialog]
    end
    
    subgraph "Worker Layer (QThread)"
        LiveWorker[Modbus Worker]
        FileWorker[File Loader]
        AnalysisWorker[Analysis Worker]
    end
    
    subgraph "Core Backend"
        LM[License Manager]
        Bridge[Analyzer Bridge]
        Engine[Analysis Engine (NumPy/SciPy)]
    end
    
    ConnDialog --> LiveWorker
    LiveWorker -->|Signals| Oscilloscope
    LicenseDlg -->|Verify| LM
    AnalysisWorker -->|Compute| Engine
    
    UI --> AnalysisWorker
```

### Component Details
- **`desktop_app/ui/`**: Contains strict UI components (`main_window.py`, `license_dialog.py`).
- **`desktop_app/workers/`**: Background threads for non-blocking operations (`live_worker.py` for Modbus, `analysis_worker.py` for heavy math).
- **`backend/analysis.py`**: The synchronized math engine shared with the web version.
- **`backend/license_manager.py`**: Handles SHA-256 fingerprinting and key verification.

---

## 🛠 Installation & Setup

### Prerequisites
- Python 3.10+
- pip (Python Package Manager)

### Step 1: Clone & Setup Environment
```bash
git clone https://github.com/diferansiyel1/qorsense_desktop.git
cd qorsense_desktop

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
pip install -r desktop_app/requirements.txt
```

### Step 3: Run the Application
```bash
python desktop_app/main.py
```

---

## 🔑 Licensing & Activation

### For Users
1. Upon first launch, the **License Activation** dialog will appear.
2. Copy your **Machine ID** (e.g., `A35C7B79-BFE9-BE24-2EBB-9160AAB960CC`).
3. Send this ID to Pikolab Support.
4. Enter the received **License Key** to activate your copy.

### For Administrators (Key Generation)
A standalone tool is included for generating keys:

```bash
# Launch the generator tool
python tools/license_generator.py
```
1. Paste the customer's Machine ID.
2. Click **Generate License Key**.
3. Send the generated generic key to the customer.

---

## 📡 Modbus Configuration

The `ConnectionDialog` supports standard Modbus parameters:

| Parameter | Default (Hamilton) | Options |
|-----------|--------------------|---------|
| **Baud Rate** | 19200 | 9600, 19200, 38400... |
| **Parity** | Even (E) | None, Even, Odd |
| **Stop Bits** | 1 | 1, 2 |
| **Byte Size** | 8 | 8 |
| **Format** | Float32 Big-Endian | Float32 BE, Int16... |

---

## 📄 License

**Copyright © 2025 Pikolab R&D Ltd. Co.**
All Rights Reserved. Unauthorized copying, distribution, or reverse engineering of this software is strictly prohibited.
