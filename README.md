# Python Desktop Calendar & Event Manager

A robust Desktop Application for scheduling and managing events, built with Python, CustomTkinter, and SQLite. This project follows a structured modular approach to ensure clean code separation, visual consistency, and reliability.

## Key Features

- **Full CRUD Operations:** Create, Read, Update, and Delete events stored in a persistent local SQLite database.
- **Modern UI/UX:** Completely ported to `CustomTkinter` featuring responsive grid layouts, custom hover effects, and an elegant Sand-styled design.
- **Real-Time Countdown Engine:** An asynchronous background loop updating every 1000ms that tracks events and displays live statuses (*Time Remaining*, *In Progress*, *Expired*).
- **Interactive Data Visualization:** Embedded `Matplotlib` bar charts displaying yearly event statistics directly inside the interface with auto-refresh functionality.
- **Smart Conflict Resolution:** Built-in validation algorithms to prevent time overlaps (`is_slot_busy`) and logical date-entry errors.
- **Fluid Navigation:** Intuitive calendar layout with a quick-switch 4x3 month matrix overview.

## Tech Stack

- **Language:** Python 3.x
- **GUI Libraries:** CustomTkinter & Tkinter (Treeview Architecture)
- **Data Visualization:** Matplotlib (FigureCanvasTkAgg)
- **Database:** SQLite3
- **Date Utilities:** datetime, tkcalendar

## Installation & Setup

You can run the application either as a standalone executable or directly from the source code.

### 📦 Option A: Executable (Clean)
This build initializes a fresh, empty workspace.
1. Download **`CalendarApp.exe`** from the **Releases** section on the right side of this repository.
2. Run the executable to generate a clean database file automatically.

### 🛠️ Option B: Run from Source
1. Clone the repository:
    ```bash
    git clone https://github.com/gchorafas/Calendar-App-Python.git
    cd Calendar-App-Python
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Run the application:
    ```bash
    python main.py
    ```

### 🚀 Option C: Demo Showcase
This build comes pre-populated with event entries across 2026 and 2027 to demonstrate the real-time countdowns and monthly Matplotlib chart statistics.
1. Download **`CalendarApp-Demo-Showcase.zip`** from the **Releases** section on the right side of this repository.
2. Extract the ZIP archive.
3. Run `CalendarApp.exe` from the extracted folder.