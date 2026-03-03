import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
#pip3 install tkcalendar --user
from tkcalendar import *
import calendar

# --- 1. ΜΟΝΤΕΛΟ ΔΕΔΟΜΕΝΩΝ (MODEL) ---
class Event:
    def __init__(self, event_id, title, description, event_str, event_fsh):
        self.id = event_id 
        self.title = title 
        self.description = description 
        self.event_str = event_str # Αντικείμενο datetime
        self.event_fsh = event_fsh # Αντικείμενο datetime

    def get_duration(self):
        """Υπολογίζει τη διάρκεια μεταξύ έναρξης και λήξης."""
        duration = self.event_fsh - self.event_str
        tr_sec = int(duration.total_seconds())
        if tr_sec < 0: return "Λανθασμένη ώρα"
        tr_hours = tr_sec // 3600
        tr_min = (tr_sec % 3600) // 60
        return f"{tr_hours}ώ {tr_min}λ"
    

# --- 2. ΔΙΑΧΕΙΡΙΣΗ ΒΑΣΗΣ ΔΕΔΟΜΕΝΩΝ (DATABASE) ---
class CalendarDB:
    def __init__(self):
        # Σύνδεση στη βάση - Αν δεν υπάρχει, το IF NOT EXISTS την δημιουργεί
        self.conn = sqlite3.connect("CalendarApp.db")
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        #Δημιουργεί τον πίνακα αν δεν υπάρχει ήδη.
        #Τα ονόματα πρέπει να αντιστοιχούν με την βάση μας
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS CalendarApp (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Title TEXT,
                Description TEXT,
                Event_str TEXT,
                Event_fsh TEXT
            )
        """)
        self.conn.commit()

    def is_slot_busy(self, new_start, new_end):
        #Ελέγχει για επικαλύψεις ωρών στη βάση.
        self.cursor.execute("SELECT Event_str, Event_fsh FROM CalendarApp")
        rows = self.cursor.fetchall()
        for start_s, end_s in rows:
            exist_start = datetime.strptime(start_s, '%Y-%m-%d %H:%M')
            exist_end = datetime.strptime(end_s, '%Y-%m-%d %H:%M')
            # Λογική σύγκρουσης: (StartA < EndB) και (EndA > StartB)
            if new_start < exist_end and new_end > exist_start:
                return True
        return False

    def new_event(self, event):
        """Εισαγωγή νέου γεγονότος."""
        #Ένα query το οποίο κάνει εισαγωγή στοιχείων στη βάση 
        qr = "INSERT INTO CalendarApp (Title, Description, Event_str, Event_fsh) VALUES (?,?,?,?)"
        data = (
            #Το event είναι το αντικείμένο που κληρονομεί από την κλάση Event 
            event.title,
            event.description,
            event.event_str.strftime('%Y-%m-%d %H:%M'),
            event.event_fsh.strftime('%Y-%m-%d %H:%M')
        )
        self.cursor.execute(qr, data)
        self.conn.commit()

    def load_table(self, day_filter=None):
        if day_filter:
            # Αν υπάρχει φίλτρο, φέρε μόνο όσα ξεκινούν με αυτή την ημερομηνία
            self.cursor.execute("SELECT * FROM CalendarApp WHERE Event_str LIKE ? ORDER BY Event_str", (day_filter + "%",))
        else:
            #Φορτώνει όλα τα γεγονότα ταξινομημένα χρονικά.
            self.cursor.execute("SELECT * FROM CalendarApp ORDER BY Event_str")
        return self.cursor.fetchall()

    def delete_event(self, event_id):
        #Διαγράφει ένα γεγονός βάσει ID.
        self.cursor.execute("DELETE FROM CalendarApp WHERE ID = ?", (event_id,))
        self.conn.commit()

# --- 3. ΓΡΑΦΙΚΟ ΠΕΡΙΒΑΛΛΟΝ (UI) ---
class CalendarUI:
    def __init__(self, root):
        now = datetime.now() # Παίρνουμε την ώρα συστήματος (τώρα)
        self.current_month = now.month # π.χ. 3
        self.current_year = now.year   # π.χ. 2026
        self.root = root
        self.root.title("Project 22 - Ηλεκτρονικό Ημερολόγιο")
        self.root.geometry("800x700")
        self.db = CalendarDB()
        self.setup_ui()
        self.refresh_view()

    def setup_ui(self):
        # --- FRAME ΕΙΣΑΓΩΓΗΣ ---
        frame = tk.LabelFrame(self.root, text="Διαχείριση Γεγονότος", padx=10, pady=10)
        frame.pack(pady=10, fill="x", padx=10)

        tk.Label(frame, text="Τίτλος:").grid(row=0, column=0, sticky="w")
        self.ent_title = tk.Entry(frame)
        self.ent_title.grid(row=0, column=1, sticky="we")

        tk.Label(frame, text="Ημερομηνία (ΗΗ/ΜΜ/ΕΕΕΕ):").grid(row=1, column=0, sticky="w")
        date_subframe = tk.Frame(frame)
        date_subframe.grid(row=1, column=1, sticky="w")
        self.ent_day = tk.Entry(date_subframe, width=3)
        self.ent_day.pack(side="left")
        tk.Label(date_subframe, text="/").pack(side="left")
        self.ent_month = tk.Entry(date_subframe, width=3)
        self.ent_month.pack(side="left")
        tk.Label(date_subframe, text="/").pack(side="left")
        self.ent_year = tk.Entry(date_subframe, width=5)
        self.ent_year.pack(side="left")

        tk.Label(frame, text="Ώρα Έναρξης (ΩΩ:ΛΛ):").grid(row=2, column=0, sticky="w")
        self.ent_time = tk.Entry(frame)
        self.ent_time.grid(row=2, column=1, sticky="w")
        
        # Κουμπιά Ενεργειών
        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=3, columnspan=2, pady=10)
        
        tk.Button(btn_frame, text="Αποθήκευση", command=self.save_event, bg="green", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Διαγραφή Επιλεγμένου", command=self.delete_selected, bg="red", fg="white").pack(side="left", padx=5)

        self.calendar_inframe()

        # --- TREEVIEW (ΠΙΝΑΚΑΣ) ---
        self.tree = ttk.Treeview(self.root, columns=("ID", "Τίτλος", "Έναρξη", "Διάρκεια"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Τίτλος", text="Τίτλος")
        self.tree.heading("Έναρξη", text="Έναρξη")
        self.tree.heading("Διάρκεια", text="Διάρκεια")
        self.tree.column("ID", width=50)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def calendar_inframe(self):
        # ΕΛΕΓΧΟΣ: Αν υπάρχει ήδη το frame, το διαγράφουμε πριν το ξαναφτιάξουμε
        if hasattr(self, 'calendar_frame'):
            self.calendar_frame.destroy()

        self.calendar_frame = tk.LabelFrame(self.root, text=f"Ημερολόγιο - Μήνας: {self.current_month}/{self.current_year}", padx=10, pady=10)
        self.calendar_frame.pack(pady=10, fill="x", padx=10)

        # Δημιουργία κουμπιών πλοήγησης
        tk.Button(self.calendar_frame, text="<", command=lambda: self.change_month(-1)).grid(row=0, column=0)#Μήνα πίσω
        tk.Button(self.calendar_frame, text=">", command=lambda: self.change_month(1)).grid(row=0, column=6)#Μήνα επόμενο

        # Επικεφαλίδες ημερών (Δευ, Τρι κλπ)
        days_of_week = ["Δευ", "Τρι", "Τετ", "Πεμ", "Παρ", "Σαβ", "Κυρ"]
        for i, day in enumerate(days_of_week):
            tk.Label(self.calendar_frame, text=day, font=('Arial', 9, 'bold')).grid(row=1, column=i)

        # Δημιουργία των ημερών του μήνα
        month_table = calendar.monthcalendar(self.current_year, self.current_month)
        for r, week in enumerate(month_table):
            for c, day in enumerate(week):
                if day != 0:
                    # Σύνδεση με τη συμπλήρωση των πεδίων (προαιρετικό αλλά χρήσιμο)
                    btn = tk.Button(self.calendar_frame, text=str(day), width=4,
                                    command=lambda d=day: self.fill_entries_from_cal(d))
                    btn.grid(row=r+2, column=c, padx=2, pady=2)
    
    def change_month(self, delta):
        self.current_month += delta
        #Σε περίπτωση που ο μήνας πάει 13 τότε πάι πάει 1 και προσθέτουμε +1 στα χρόνια
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        #Εδώ ακριβός το ανάποδο από το if
        elif self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.calendar_inframe() # Κλήση της σωστής μεθόδου

    def fill_entries_from_cal(self, day):
        """Βοηθητική μέθοδος για να γεμίζουν τα Entries όταν πατάς μια μέρα"""
        # 1. Φτιάχνουμε την ημερομηνία σε μορφή YYYY-MM-DD
        date_str = f"{self.current_year}-{self.current_month:02d}-{day:02d}"
    
        # 2. Ενημερώνουμε τα κουτάκια (Entries)
        self.ent_day.delete(0, tk.END); self.ent_day.insert(0, str(day))
        self.ent_month.delete(0, tk.END); self.ent_month.insert(0, str(self.current_month))
        self.ent_year.delete(0, tk.END); self.ent_year.insert(0, str(self.current_year))

        # 3. Καλούμε την refresh_view με την ημερομηνία-φίλτρο!
        self.refresh_view(date_str)

    
    def save_event(self):
        try:
            # 1. Λήψη δεδομένων
            d, m, y = self.ent_day.get(), self.ent_month.get(), self.ent_year.get()
            t = self.ent_time.get()
            start_dt = datetime.strptime(f"{y}-{m}-{d} {t}", "%Y-%m-%d %H:%M")
            
            # 2. Ορισμός λήξης (π.χ. +1 ώρα αυτόματα για το παράδειγμα)
            end_dt = start_dt + timedelta(hours=1)

            # 3. Έλεγχος Επικάλυψης
            if self.db.is_slot_busy(start_dt, end_dt):
                messagebox.showwarning("Σύγκρουση", "Η συγκεκριμένη ώρα είναι ήδη δεσμευμένη!")
                return

            # 4. Αποθήκευση
            new_ev = Event(None, self.ent_title.get(), "Περιγραφή", start_dt, end_dt)
            self.db.new_event(new_ev)
            messagebox.showinfo("Επιτυχία", "Το γεγονός προστέθηκε!")
            self.refresh_view()
        except ValueError:
            messagebox.showerror("Λάθος", "Παρακαλώ εισάγετε σωστή ημερομηνία και ώρα (π.χ. 12:00)")

    def delete_selected(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Επιλογή", "Παρακαλώ επιλέξτε ένα γεγονός από τον πίνακα.")
            return
        
        item_data = self.tree.item(selected_item)['values']
        event_id = item_data[0]
        
        if messagebox.askyesno("Επιβεβαίωση", "Θέλετε σίγουρα να διαγράψετε αυτό το γεγονός;"):
            self.db.delete_event(event_id)
            self.refresh_view()

    def refresh_view(self, day_filter=None):
        """Καθαρίζει και ξαναγεμίζει τον πίνακα με δεδομένα από τη βάση."""
        for i in self.tree.get_children(): self.tree.delete(i)
        for row in self.db.load_table(day_filter):
            # Ανακατασκευή αντικειμένου Event για χρήση της get_duration
            s = datetime.strptime(row[3], '%Y-%m-%d %H:%M')
            e = datetime.strptime(row[4], '%Y-%m-%d %H:%M')
            temp_ev = Event(row[0], row[1], row[2], s, e)
            
            self.tree.insert("", "end", values=(row[0], row[1], row[3], temp_ev.get_duration()))

if __name__ == "__main__":
    root = tk.Tk()
    app = CalendarUI(root)
    root.mainloop()