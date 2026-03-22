Python Desktop Calendar & Event Manager


​A robust Desktop Application for scheduling and managing events, built with Python, Tkinter, and SQLite. This project follows the Model-View-Controller (MVC) architectural pattern to ensure clean code separation and scalability.


​Key Features
-​ Full CRUD Operations: Create, Read, Update, and Delete events stored in a persistent SQLite database.
- ​Dynamic UI: Built with Tkinter and ttk.Treeview for a clean, table-based data display.
- ​Date Management: Integrated tkcalendar for intuitive date picking and automated duration calculations.
- ​Business Logic: Custom algorithms to calculate event durations and prevent logical errors (e.g., end time before start time).
-​ Data Persistence: Uses a local .db file, ensuring your schedule is saved across sessions.


​Tech Stack
-​ Language: Python 3.x
-​ GUI Library: GUI Library: CustomTkinter & Tkinter
- ​Database: SQLite3
- ​Date Utilities: datetime, tkcalendar


​Installation & Setup
- ​Clone the repository:  
git clone https://github.com/AggelosKrs/CalendarApp.git
- ​Install dependencies:  
This app requires the CustomTkinter and tkcalendar libraries.
pip install customtkinter tkcalendar
- ​Run the application:  
python test.py (or the name of your script) 