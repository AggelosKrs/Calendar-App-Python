import sqlite3
import customtkinter as ctk
from tkinter import ttk, messagebox 
from datetime import datetime, timedelta
#pip3 install tkcalendar --user
from tkcalendar import *
import calendar

# Maybe use this colour for the theme later? "#D3C4B7"

ctk.set_appearance_mode("light")  # Προσαρμογή σε system theme
ctk.set_default_color_theme("blue") # Μπορούμε να αλλάξουμε σε green ή dark-blue

# --- 1. ΜΟΝΤΕΛΟ ΔΕΔΟΜΕΝΩΝ (MODEL) ---
class Event:
    def __init__(self, event_id, title, description, event_str, event_fsh, notification):
        self.id = event_id 
        self.title = title 
        self.description = description 
        self.event_str = event_str # Αντικείμενο datetime
        self.event_fsh = event_fsh # Αντικείμενο datetime
        self.notification = notification

    def get_duration(self):
        """Υπολογίζει τη διάρκεια μεταξύ έναρξης και λήξης."""
        duration = self.event_fsh - self.event_str
            
        tr_sec = int(duration.total_seconds())
        #Διορθώνε το πρόβλημα αν η ώρα εινα 00:00 το βράδυ
        if tr_sec < 0:
            tr_sec += 86400
        
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
                Event_fsh TEXT,
                Notification INTEGER DEFAULT 0                            
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
        qr = "INSERT INTO CalendarApp (Title, Description, Event_str, Event_fsh, Notification) VALUES (?,?,?,?,?)"
        data = (
            #Το event είναι το αντικείμένο που κληρονομεί από την κλάση Event 
            event.title,
            event.description,
            event.event_str.strftime('%Y-%m-%d %H:%M'),
            event.event_fsh.strftime('%Y-%m-%d %H:%M'),
            event.notification
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

# --- 3. ΓΡΑΦΙΚΟ ΠΕΡΙΒΑΛΛΟΝ (GUI) ---
class CalendarUI:
    # Λίστα από μήνες για μελλοντική χρήση στο UI (Πρώτο στοιχείο = "" ώστε 1=Ιανουάριος)
    months_desc = ["", "Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος", "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος"]
    def __init__(self, root):
        now = datetime.now() # Παίρνουμε την ώρα συστήματος (τώρα)
        self.current_month = now.month # π.χ. 3
        self.current_year = now.year   # π.χ. 2026
        self.events_memory = {} # Το λεξικό που θα κρατάει ID, start_dt, end_dt
        self.root = root
        self.root.title("Project 22 - Ηλεκτρονικό Ημερολόγιο")
        self.root.geometry("1300x600")
        self.db = CalendarDB()
        self.setup_ui()
        self.refresh_view()
        self.update_countdowns()

    def setup_ui(self):
        # Ορίζουμε την συμπεριφορά του grid layout με weights
        self.root.grid_rowconfigure(0, weight=0, minsize=340) # Το πάνω μέρος του παραθύρου μένει σταθερό, με minsize ώστε να παραμένει και όταν έχω λιγότερες σειρές
        self.root.grid_rowconfigure(1, weight=1) # Το κάτω μέρος του παραθύρου μένει σταθερό
        self.root.grid_columnconfigure(0, weight=2) # Το αριστερό μέρος του παραθύρου είναι ελαστικό και κλέβει τον πιο πολύ χώρο
        self.root.grid_columnconfigure(1, weight=1) # Το δεξί μέρος του παραθύρου είναι και αυτό ελαστικό αλλά του αναλογεί πιο λίγος χώρος

        # ΠΑΝΩ ΑΡΙΣΤΕΡΑ [Frame που περιέχει το calendar]---------------------------
        # (για να παραμένει σταθερή η θέση του σε κάθε refresh)
        self.calendar_inframe()
        self.manage_event()


        # ΚΑΤΩ ΑΡΙΣΤΕΡΑ [Frame TREEVIEW (ΠΙΝΑΚΑΣ)]---------------------------------------
        self.tree_frame = ctk.CTkFrame(self.root)
        self.tree_frame.grid(row = 1, column=0, padx=5, pady=(0,10), sticky="nsew")

        self.tree = ttk.Treeview(self.tree_frame, columns=("Τίτλος", "Σχόλιο", "Έναρξη", "Διάρκεια", "Notification"), show='headings')
        self.tree.heading("Τίτλος", text="Τίτλος")
        self.tree.heading("Σχόλιο", text="Σχόλιο")
        self.tree.heading("Έναρξη", text="Έναρξη")
        self.tree.heading("Διάρκεια", text="Διάρκεια")
        self.tree.heading("Notification", text="Ειδοποίηση")

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Όταν αφήνει ο χρήστης το mouse-1 πάνω σε μία εγγραφή, γεμίζω τα entries τα στοιχεία της
        self.tree.bind("<ButtonRelease-1>", self.fill_entries_from_event)

        # ΚΑΤΩ ΔΕΞΙΑ [Frame Summary ημέρας]----------------------------------------------
        self.summary_frame = ctk.CTkFrame(self.root)
        self.summary_frame.grid(row = 1, column=1, padx=5, pady=(0,10), sticky="nsew")
        self.summary_label = ctk.CTkLabel(master = self.summary_frame ,text="Σύνοψη Ημέρας", font=('Arial', 14, 'bold'))
        self.summary_label.pack(pady=5)

        self.insert_button = ctk.CTkButton(self.summary_frame, text="Αποθήκευση", command="")
        self.insert_button.pack(side = "left", padx=40)

        self.summary_txt = ctk.CTkTextbox(self.summary_frame, state="disabled", fg_color="transparent") # disabled για read-only
        self.summary_txt.pack(fill="both", expand=True, padx=10, pady=10)

    def calendar_inframe(self):

        self.calendar_container = ctk.CTkFrame(self.root)
        self.calendar_container.grid(row=0, column=0, pady=10, padx=5, sticky="nsew")
        # ΕΛΕΓΧΟΣ: Αν υπάρχει ήδη το frame, το διαγράφουμε πριν το ξαναφτιάξουμε
        if hasattr(self, 'calendar_frame'):
            self.calendar_frame.destroy()

        # Προσαρμογή σε customtkinter (χωρίς φυτεμένο label στο frame)
        # Διόρθωση root σε self.root ώστε να αλλάζει δυναμικα
        self.calendar_frame = ctk.CTkFrame(master = self.calendar_container, fg_color="transparent")
        self.calendar_frame.pack(fill="x", padx=10, anchor="n", expand=True)
        self.label = ctk.CTkLabel(master = self.calendar_frame ,text="Ημερολόγιο", font=('Arial', 14, 'bold'))
        self.label.pack(pady=2, padx=10, fill="x")

        # Ένα container για τα κουμπιά πλοήγησης
        nav_frame = ctk.CTkFrame(master = self.calendar_frame, fg_color= "transparent")
        nav_frame.pack(pady=5, padx=10, anchor="n")

        # Νεα κουμπιά με όνομα Μήνα / Χρονιάς ανάμεσα στα κουμπιά
        # Ένα ενιαίο "pill" frame για τον Μήνα
        nav_month = ctk.CTkFrame(master = nav_frame, fg_color= "#E9E9E9", corner_radius=15)
        nav_month.grid(row=0, column=0, padx=10) # padx δημιουργεί κενό ανάμεσα στα δύο pill Μήνας / Έτος)


        # Κουμπί < Μήνα (padx αριστερά για να μην "κοβει" το rounded corner)
        ctk.CTkButton(nav_month, text="<", width=30, text_color="black", fg_color="transparent", hover_color="#C8C8C8",
                        command=lambda: self.change_month(-1)).pack(side="left", padx=(10, 0))
        # NEW BUTTON για zoom out Μήνα με ένα σταθερό πλάτος (width=80)
        ctk.CTkButton(nav_month, text=f"{self.months_desc[self.current_month]}", width=80, text_color="black", font=('Arial', 12, 'bold'), fg_color="transparent", hover_color="#C8C8C8",
                        command=lambda: self.show_months()).pack(side="left")
        # Κουμπί > Μήνα (padx δεξιά για να μην "κοβει" το rounded corner)
        ctk.CTkButton(nav_month, text=">", width=30, text_color="black", fg_color="transparent", hover_color="#C8C8C8",
                        command=lambda: self.change_month(1)).pack(side="left", padx=(0, 10)) # Με λίγο padx για κενό
        
        # Ένα ενιαίο "pill" frame για το Έτος
        nav_year = ctk.CTkFrame(master = nav_frame, fg_color= "#E9E9E9", corner_radius=15)
        nav_year.grid(row=0, column=1)        
        # Κουμπί < Έτους
        ctk.CTkButton(nav_year, text="<", width=30, text_color="black", fg_color="transparent", hover_color="#C8C8C8",
                        command=lambda: self.change_year(-1)).pack(side="left", padx=(10, 5))
        # Label Έτους
        ctk.CTkLabel(master = nav_year, text=f"{self.current_year}", text_color="black", font=('Arial', 12, 'bold')).pack(side="left")
        # Κουμπί > Έτους
        ctk.CTkButton(nav_year, text=">", width=30, text_color="black", fg_color="transparent", hover_color="#C8C8C8",
                        command=lambda: self.change_year(1)).pack(side="left", padx=(5, 10))
        
        # Για customtkinter κάνω pack ακόμα ένα container του grid των κουμπιών
        self.cal_grid_container = ctk.CTkFrame(master = self.calendar_frame, fg_color="transparent")#Το border το έχουμε προσορινά για να μας βοηθά στην δημιουργία του UI
        self.cal_grid_container.pack(pady=5, padx=10, fill="both", expand=True)
        
        #Το uniform="group1" θα δίνει ίδιο πλάτος για όλα
        for i in range(7):
            self.cal_grid_container.grid_columnconfigure(i, weight=1, uniform="group1")

        # Επικεφαλίδες ημερών (Δευ, Τρι κλπ)
        days_of_week = ["Δευ", "Τρι", "Τετ", "Πεμ", "Παρ", "Σαβ", "Κυρ"]
        for i, day in enumerate(days_of_week):
            ctk.CTkLabel(self.cal_grid_container, text=day, font=('Arial', 14, 'bold')).grid(row=0, column=i, pady=(0, 5), sticky="we")

        all_events = self.db.load_table()
        events_lookup = {}
        for row in all_events:
            try:
                # row[3] είναι το 'YYYY-MM-DD HH:MM'
                ev_dt = datetime.strptime(row[3], '%Y-%m-%d %H:%M')
                if ev_dt.month == self.current_month and ev_dt.year == self.current_year:
                    # Παίρνω το 0  αν δεν υπάρχει γεγονός σήμερα, αλλιώς παίρνω το status
                    current_status = events_lookup.get(ev_dt.day, 0)

                    # Με τον παρακάρω έλεγχο αν έστω και ένα γεγονός της μέρας είναι ενεργό θα έχω status 1 (Η μέρα θα μένει πράσινη αργότερα)
                    # Ελέγχω και το τωρινό γεγονός της βάσης, και τα γεγονότα αυτής της μέρας (current_status)
                    if int(row[5]) == 1 or int(current_status) == 1:
                        events_lookup[ev_dt.day] = 1 # Αποθηκεύω status 1 με κλειδί την μέρα
                    else:
                    # Μόνο αν δεν υπάρχει κανένα ενεργό γεγονός
                        events_lookup[ev_dt.day] = 0 # Αποθηκεύω status 0 με κλειδί την μέρα

            except Exception as e:
                print(f"Error parsing date: {e}")

        # Δημιουργία των ημερών του μήνα
        month_table = calendar.monthcalendar(self.current_year, self.current_month)
        for r, week in enumerate(month_table):
            for c, day in enumerate(week):
                if day != 0:
                    button_color = "#3b8ed0"

                    if day in events_lookup:
                        if int(events_lookup[day]) == 1: # Cast ως int
                            button_color = "green"
                        else:
                            button_color = "gray"

                    # Σύνδεση με τη συμπλήρωση των πεδίων (προαιρετικό αλλά χρήσιμο)
                    btn = ctk.CTkButton(self.cal_grid_container, text=str(day), width=40,
                                        fg_color= button_color,
                                        hover_color="#34495e",  
                                        command=lambda d=day: self.fill_entries_from_cal(d)) # Διέγραψα το height
                    btn.grid(row=r+1, column=c, padx=3, pady=3, sticky="we")


    def manage_event(self):
        # ΠΑΝΩ ΔΕΞΙΑ [Frame Εισαγωγής]---------------------------------------------
        # (προσαρμογή σε CTk Frame με ξεχωριστό label)

        # Ένα "Outer Shell" frame που θα περιέχει τα input
        self.main_input_frame = ctk.CTkFrame(self.root)
        self.main_input_frame.grid(row=0, column=1, pady=10, padx=5, sticky="nsew") # fill not posible according to doc?

        self.input_label = ctk.CTkLabel(master = self.main_input_frame ,text="Διαχείριση Γεγονότος", font=('Arial', 14, 'bold'))
        self.input_label.pack(pady=5)

        # Εσωτερικό Frame που ανήκει στο main_input_frame, που θα περιέχει grid μέσα του
        in_grid_container = ctk.CTkFrame(master = self.main_input_frame, fg_color="transparent")
        in_grid_container.pack(pady=5, padx=10, fill="both", expand=True) # Should i fill or expand? CHECK LATER
        in_grid_container.grid_columnconfigure(1, weight=1) # Ελαστικότητα στην στήλη 1 (Κουτάκια Εισαγωγής)

        # Μετά αφήνω τα πεδία input όπως πριν απλά τα κάνω "παιδιά" του in_grid_container
        ctk.CTkLabel(in_grid_container, text="Τίτλος:").grid(row=0, column=0, sticky="w")
        self.ent_title = ctk.CTkEntry(in_grid_container)
        self.ent_title.grid(row=0, column=1, sticky="we", pady=2)

        ctk.CTkLabel(in_grid_container, text="Ημερομηνία (ΗΗ/ΜΜ/ΕΕΕΕ):").grid(row=1, column=0, sticky="w")
        date_subframe = ctk.CTkFrame(in_grid_container)
        date_subframe.grid(row=1, column=1, sticky="w", pady=2)
        self.ent_day = ctk.CTkEntry(date_subframe, width=40, placeholder_text="ΗΗ")
        self.ent_day.pack(side="left")
        ctk.CTkLabel(date_subframe, text="/").pack(side="left")
        self.ent_month = ctk.CTkEntry(date_subframe, width=40, placeholder_text="ΜΜ")
        self.ent_month.pack(side="left")
        ctk.CTkLabel(date_subframe, text="/").pack(side="left")
        self.ent_year = ctk.CTkEntry(date_subframe, width=60, placeholder_text="ΕΕΕΕ")
        self.ent_year.pack(side="left")

        ctk.CTkLabel(in_grid_container, text="Ώρα Έναρξης (ΩΩ:ΛΛ):").grid(row=2, column=0, sticky="w")
        self.ent_time_start = ctk.CTkEntry(in_grid_container, placeholder_text="ΩΩ:ΛΛ")
        self.ent_time_start.grid(row=2, column=1, sticky="w", pady=2)

        ctk.CTkLabel(in_grid_container, text="Ώρα Λήξης (ΩΩ:ΛΛ):").grid(row=3, column=0, sticky="w", pady=2)
        self.ent_time_end = ctk.CTkEntry(in_grid_container, placeholder_text="ΩΩ:ΛΛ")
        self.ent_time_end.grid(row=3, column=1, sticky="w", pady=2)

        ctk.CTkLabel(in_grid_container, text="Σχόλιο:").grid(row=4, column=0, sticky="w", pady=2)
        self.ent_comment = ctk.CTkEntry(in_grid_container)
        self.ent_comment.grid(row=4, column=1, sticky="we", pady=2)
        
        # Κουμπιά Ενεργειών
        btn_frame = ctk.CTkFrame(in_grid_container)
        btn_frame.grid(row=5, columnspan=2, pady=10, sticky="we") # we για stretch δεξιά/αριστερά

        # Προσαρμογή buttons για customtkinter
        ctk.CTkButton(btn_frame, text="Αποθήκευση", command=self.save_event, fg_color="green", text_color="white").pack(side="left", padx=2, expand=True)
        ctk.CTkButton(btn_frame, text="Διαγραφή Επιλεγμένου", command=self.delete_selected, fg_color="red", text_color="white").pack(side="left", padx=2, expand=True)
        ctk.CTkButton(btn_frame, text="Συμβάντα", command=self.refresh_view, fg_color="blue", text_color="white").pack(side="left", padx=2, expand=True)        


    def show_months(self):
        # Καταστρέφουμε τα κουμπιά που περιέχουν ημέρες (παιδιά της cal_grid_container)
        for item in self.cal_grid_container.winfo_children():
            item.destroy()
        
        # Ακυρώνουμε την ελαστικότητα στις στήλες 4,5,6 που υπάρχει από calendar_inframe, και την κρατάμε για 0,1,2,3
        for i in range(7):
            if i < 4:
                self.cal_grid_container.grid_columnconfigure(i, weight=1, uniform="group2")
            else:
                self.cal_grid_container.grid_columnconfigure(i, weight=0, uniform="")


        # Επανάληψη για την δημιουργία των μηνών μέσα στο grid
        for month in range(1, 13):
                    # (Τρόπος χωρίσματος σε grid όπως θα έφτιαχνε κάποιος μια σκακιέρα)
                    month_idx = month - 1 # index για τον μήνα π.χ. 0 για Ιανουάριο, 1 για Φεβρουάριο κτλ
                    # Ακέραιη διαίρεση με 4 για την σειρά (0//4 = 0, 1//4 = 0, ..., 4//4 = 1)
                    r = month_idx // 4
                    # Modulo με 4 για την στήλη (0%4 = 0, 1%4 = 1, ..., 4%4 = 0)
                    c = month_idx % 4
                    
                    # Παίρνω το όνομα του μήνα που θα μπει στο κουμπί
                    curr_month_btn = self.months_desc[month]
                    
                    # Δημιουργία του κουμπιού
                    btn = ctk.CTkButton(self.cal_grid_container, text=curr_month_btn, 
                                        command=lambda m=month: self.select_month(m))
                    # Placement στο grid
                    btn.grid(row=r, column=c, padx=3, pady=3, sticky="we")  

    def select_month(self, selected_month):
        """Μέθοδος για μεταπήδηση σε συγκεκριμένο μήνα στο calendar grid"""
        # Αλλαγή του current μήνα
        self.current_month = selected_month
        # Καλούμε την συνάρτηση που θα ξανά ζωγραφίσει το ημερολόγιο
        self.calendar_inframe()

    def change_month(self, delta):
        """Μέθοδος για αλλαγή μήνα"""
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

    def change_year(self, delta):
        """Νέα μέθοδος για αλλαγή έτους"""
        self.current_year += delta
        self.calendar_inframe()
    
    def fill_entries_from_cal(self, day):
        """Βοηθητική μέθοδος για να γεμίζουν τα Entries όταν πατάς μια μέρα"""
        # 1. Φτιάχνουμε την ημερομηνία σε μορφή YYYY-MM-DD
        date_str = f"{self.current_year}-{self.current_month:02d}-{day:02d}"
    
        # 2. Ενημερώνουμε τα κουτάκια (Entries)
        # Για customtkinter tk.end -> "end" Απλό string

        self.ent_day.delete(0, "end"); self.ent_day.insert(0, str(day))
        self.ent_month.delete(0, "end"); self.ent_month.insert(0, str(self.current_month))
        self.ent_year.delete(0, "end"); self.ent_year.insert(0, str(self.current_year))

        # 3. Καλούμε την refresh_view με την ημερομηνία-φίλτρο!
        self.refresh_view(date_str)

    def fill_entries_from_event(self, event):
        """Βοηθητική μέθοδος για να γεμίζουν τα Entries όταν πατάς ένα γεγονός του πίνακα"""
        # Αν δεν έχει επιλεχθεί κάτι
        selected_item = self.tree.selection()[0] # (π.χ. 'I001')
        if not selected_item:
            return
        
        # 1. Λήψη δεδομένων από τον πίνακα και ID από την μνήμη/λεξικό
        entry_data = self.tree.item(selected_item)["values"]
        event_id = self.events_memory[selected_item]["db_id"]
        event_title = entry_data[0]
        event_comment = entry_data[1]

        # 2. Παίρνω την ημερομηνία / ώρες από την βάση επειδή η ώρα λήξης δεν φαίνεται στον πίνακα
        self.db.cursor.execute("SELECT Event_str, Event_fsh FROM CalendarApp WHERE ID = ?", (event_id,)) # , για να το πάρει σαν λίστα
        row = self.db.cursor.fetchone() # Παίρνω μόνο μία γραμμή για το επιλεγμένο ID

        if row: # Αμυντικός προγραμματισμός
            full_start, full_end = row[0], row[1]

            # Μετατροπή string σε ανικείμενα χρόνου
            # Ορισμός έναρξης
            start_dt = datetime.strptime(full_start, "%Y-%m-%d %H:%M")
            # Ορισμός λήξης
            end_dt = datetime.strptime(full_end, "%Y-%m-%d %H:%M")

            # Εξαγωγή των στοιχείων
            y = str(start_dt.year)
            m = str(start_dt.month)
            d = str(start_dt.day)

            # Μορφοποίηση της ώρας (π.χ. "11:33")
            time_start = start_dt.strftime("%H:%M")
            time_end = end_dt.strftime("%H:%M")

            # 3. Καθαρισμός και Εισαγωγή στα CTk Entries
            self.ent_title.delete(0, "end"); self.ent_title.insert(0, event_title)
            self.ent_comment.delete(0, "end"); self.ent_comment.insert(0, event_comment)
            
            self.ent_day.delete(0, "end"); self.ent_day.insert(0, d)
            self.ent_month.delete(0, "end"); self.ent_month.insert(0, m)
            self.ent_year.delete(0, "end"); self.ent_year.insert(0, y)
            
            self.ent_time_start.delete(0, "end"); self.ent_time_start.insert(0, time_start)
            self.ent_time_end.delete(0, "end"); self.ent_time_end.insert(0, time_end)

    def save_event(self):
        try:
            # 1. Λήψη δεδομένων
            d, m, y = self.ent_day.get(), self.ent_month.get(), self.ent_year.get()
            t_start = self.ent_time_start.get()
            t_end = self.ent_time_end.get()
            now = datetime.now()

            # 2. Ορισμός έναρξης
            start_dt = datetime.strptime(f"{y}-{m}-{d} {t_start}", "%Y-%m-%d %H:%M")
            
            # 3. Ορισμός λήξης
            end_dt = datetime.strptime(f"{y}-{m}-{d} {t_end}", "%Y-%m-%d %H:%M")

#--------------------------- 4. Η λήξη πρέπει να είναι μετά την έναρξη----------------------------------------------------
            #if end_dt <= start_dt:
            #   messagebox.showwarning("Εσφαλμένη Ώρα", "Η ώρα λήξης πρέπει να είναι μετά την ώρα έναρξης!")
            #  return
#-------------------------------------------------------------------------------------------------------------------------
            
            # 5. Έλεγχος Επικάλυψης
            if self.db.is_slot_busy(start_dt, end_dt):
                messagebox.showwarning("Σύγκρουση", "Η συγκεκριμένη ώρα είναι ήδη δεσμευμένη!")
                return

            if now <= end_dt: # Αν βάλουμε start_dt <= now <= end_dt , σε μία αυριανή ημερομηνία now <= start_dt άρα θα μας το κάνει inactive
                is_active = 1
            else:
                is_active = 0
            
            # 6. Αποθήκευση
            new_ev = Event(None, self.ent_title.get(), self.ent_comment.get(), start_dt, end_dt, notification=is_active)
            self.db.new_event(new_ev)
            messagebox.showinfo("Επιτυχία", "Το γεγονός προστέθηκε!")
            self.refresh_view()
        except ValueError:
            messagebox.showerror("Λάθος", "Παρακαλώ εισάγετε σωστή ημερομηνία και ώρα (π.χ. 12:00)")
            

    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Επιλογή", "Παρακαλώ επιλέξτε ένα γεγονός από τον πίνακα.")
            return
        
        selected_item = selected_items[0] # Παίρνουμε την "ταμπέλα" του tree (π.χ. 'I001')
        event_id = self.events_memory[selected_item]["db_id"]
        
        if messagebox.askyesno("Επιβεβαίωση", "Θέλετε σίγουρα να διαγράψετε αυτό το γεγονός;"):
            self.db.delete_event(event_id)
            self.refresh_view()

    def refresh_view(self, day_filter=None):
        """Καθαρίζει και ξαναγεμίζει τον πίνακα, και το λεξικό events_memory με δεδομένα από τη βάση."""
        # Καθαρισμός Tree
        for i in self.tree.get_children(): 
            self.tree.delete(i)
        
        # Καθαρισμός λεξικού
        self.events_memory.clear()

        # Λήψη δεδομένων από DB ανά γραμμή
        for row in self.db.load_table(day_filter):
            start = datetime.strptime(row[3], '%Y-%m-%d %H:%M')
            end = datetime.strptime(row[4], '%Y-%m-%d %H:%M')
            status_note = int(row[5]) # Μετατροπή σε ακέραιο
#========================================================================================

            # Ανακατασκευή αντικειμένου Event για χρήση της get_duration
            temp_ev = Event(row[0], row[1], row[2], start, end, status_note)
            
            # Εισαγωγή δεδομένων DB και διάρκειας στο tree
            item_id = self.tree.insert("", "end", values=(row[1], row[2], row[3], temp_ev.get_duration(), " ")) # Στην ειδοποίηση βάζω προρσωρινά κενό
            # Η insert στην tkinter θα μας δώσει το id που έχει αυτό το αντικείμενο στον πίνακα

            # Εισαγωγή απαραίτητων δεδομένων στο λεξικό
            self.events_memory[item_id] = {
                "db_id": row[0],
                "start": start,
                "end": end,
                "status": status_note
            }

            # Ανανέωση των κουμπιών (Για να έχουμε χρώματα σωστά)
            self.calendar_inframe()
#=========================================================================================  

    def update_countdowns(self):
        now = datetime.now()
    
        for item in self.tree.get_children():
            # Για να αποφύγουμε KeyError, σε περίπτωση που υπάρχει item στο tree αλλά όχι στο λεξικό ακόμα
            if item not in self.events_memory:
                continue

            # Παίρνουμε όλα τα δεδομένα μας για το item απο το λεξικό
            item_mem = self.events_memory[item]
            event_db_id = item_mem["db_id"]
            start_dt = item_mem["start"]
            end_dt = item_mem["end"]

            values = list(self.tree.item(item, 'values'))
            #current_status = values[5] # Η στήλη Notification 

            try:
                # Περίπτωση 1: Το Event είναι στο Μέλλον (Αντ. Μέτρηση)
                if now < start_dt:
                        diff = start_dt - now
                        hours, remainder = divmod(diff.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        values[5] = f"{diff.days}ημ {hours:02d}:{minutes:02d}:{seconds:02d}"
                        self.tree.item(item, values=values)
                
                # Περίπτωση 2: Το Event είναι στο Παρόν (Σε εξέλιξη)
                elif start_dt <= now <= end_dt:
                    if values[5] != "Σε εξέλιξη": # Για να μην ενημερώνεται το tree κάθε δευτερόλεπτο άδικα 
                        values[5] = "Σε εξέλιξη"
                        self.tree.item(item, values=values)

                # Περίπτωση 3: Το Event ήταν στο παρελθόν (Έλήξε)
                else:
                    # Αν το Event είναι ακόμα σε εξέλιξη (Σύμφωνα με το δεδομένο στο λεξικό μας) πρέπει να το αλλάξουμε
                    if item_mem["status"] == 1:
                        # Αλλάζουμε το Tree στην οθόνη
                        values[5] = "Έληξε"
                        self.tree.item(item, values=values)

                        # Ενημερώνουμε τη βάση
                        self.db.cursor.execute("UPDATE CalendarApp SET Notification = 0 WHERE ID = ?", (event_db_id,))
                        self.db.conn.commit()

                        # Ενημερώνουμε την "μνήμη" μας για να μην ξανατρέξει το UPDATE
                        item_mem["status"] = 0
                        self.calendar_inframe() # Ανανέωση κουμπιών για να αλλάξει το χρώμα
                        print(f"Το συμβάν {event_db_id} έληξε και απενεργοποιήθηκε στη βάση.")

            except Exception as e:
                print(f"Σφάλμα στο countdown: {e}")
                continue

        # Επανάληψη ανά δευτερόλεπτο
        self.root.after(1000, self.update_countdowns)

if __name__ == "__main__":
    root = ctk.CTk()
    app = CalendarUI(root)
    root.mainloop()