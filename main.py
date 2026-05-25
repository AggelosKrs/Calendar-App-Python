import sqlite3
import customtkinter as ctk
import calendar
from tkinter import ttk, messagebox 
from datetime import datetime, timedelta
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Βασικές ρυθμίσεις εμφάνισης
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Χρώματα θέματος
SAND_COLOR = "#D3C4B7"  
ACTIVE_EVENT_COLOR = "#2ecc71" # Πράσινο για ενεργά
IDLE_EVENT_COLOR = "#95a5a6"   # Γκρι για ανενεργά


# --- 1. ΜΟΝΤΕΛΟ ΔΕΔΟΜΕΝΩΝ (MODEL) ---
class Event:
    """Αναπαριστά ένα μεμονωμένο γεγονός/ραντεβού στο ημερολόγιο"""

    def __init__(self, event_id, title, description, event_str, event_fsh, notification):
        """Αρχικοποιεί ένα νέο αντικείμενο γεγονότος (Event)"""

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
    """Διαχειρίζεται τη σύνδεση, τη δημιουργία πινάκων και τα ερωτήματα στη βάση δεδομένων SQLite"""

    def __init__(self):
        """Αρχικοποιεί τη σύνδεση με τη βάση δεδομένων SQLite και δημιουργεί τον απαραίτητο πίνακα αν δεν υπάρχει."""
        # Σύνδεση στη βάση - Αν δεν υπάρχει, το IF NOT EXISTS την δημιουργεί
        self.conn = sqlite3.connect("CalendarApp.db")
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """Δημιουργεί τον πίνακα CalendarApp στη βάση δεδομένων, ορίζοντας τις στήλες για ID, Τίτλο, Περιγραφή, Έναρξη, Λήξη και Ειδοποίηση"""

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
        """Ελέγχει αν το επιθυμητό χρονικό διάστημα επικαλύπτεται με ήδη υπάρχοντα γεγονότα στη βάση δεδομένων. Επιστρέφει True αν υπάρχει σύγκρουση"""

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

        # Ένα query το οποίο κάνει εισαγωγή στοιχείων στη βάση
        qr = "INSERT INTO CalendarApp (Title, Description, Event_str, Event_fsh, Notification) VALUES (?,?,?,?,?)"
        data = (
            # Το event είναι το αντικείμένο που κληρονομεί από την κλάση Event 
            event.title,
            event.description,
            event.event_str.strftime('%Y-%m-%d %H:%M'),
            event.event_fsh.strftime('%Y-%m-%d %H:%M'),
            event.notification
        )
        self.cursor.execute(qr, data)
        self.conn.commit()

    def load_table(self, day_filter=None):
        """Φορτώνει τα γεγονότα από τη βάση δεδομένων ταξινομημένα χρονικά. Αν δοθεί day_filter, επιστρέφει μόνο τα γεγονότα της συγκεκριμένης ημέρας"""

        if day_filter:
            # Αν υπάρχει φίλτρο, φέρε μόνο όσα ξεκινούν με αυτή την ημερομηνία
            self.cursor.execute("SELECT * FROM CalendarApp WHERE Event_str LIKE ? ORDER BY Event_str", (day_filter + "%",))
        else:
            # Φορτώνει όλα τα γεγονότα ταξινομημένα χρονικά.
            self.cursor.execute("SELECT * FROM CalendarApp ORDER BY Event_str")
        return self.cursor.fetchall()

    def delete_event(self, event_id):
        """Διαγράφει ένα γεγονός βάσει ID."""

        self.cursor.execute("DELETE FROM CalendarApp WHERE ID = ?", (event_id,))
        self.conn.commit()

    def get_yearly_stats(self, year):
        """Επιστρέφει μια λίστα με το πλήθος των γεγονότων ανά μήνα για το επιλεγμένο έτος"""

        # Φτιάχνουμε μια άδεια λίστα με 12 μηδενικά (Ιαν - Δεκ)
        monthly_counts = [0] * 12

        # Φέρνει μόνο την έναρξη (Event_str) για όσα γεγονότα ανήκουν στη χρονιά
        # Το f"{year}-%" μεταφράζεται π.χ. σε "2026-%", άρα πιάνει όλα τα "2026-01...", "2026-02..."
        self.cursor.execute("SELECT Event_str FROM CalendarApp WHERE Event_str LIKE ?", (f"{year}-%",))
        rows = self.cursor.fetchall()

        # Για κάθε γεγονός προσθέτω +1 στο monthly_count στο οποίο ανήκει
        for row in rows:
            # Το row[0] είναι ένα κείμενο τύπου "YYYY-MM-DD ΩΩ:ΛΛ"
            # Με το split('-')[1] κόβουμε το string και κρατάμε μόνο το 'ΜΜ' (δηλαδή τον μήνα)
            month_str = row[0].split('-')[1]
            
            # Βρίσκουμε το σωστό index για αυτό τον μήνα στον οποίο αναφέρεται το γεγονός
            # Αφαιρούμε 1 επειδή οι λίστες ξεκινάνε από το 0 (Ιανουάριος = Index 0).
            # Το μετατρέπουμε σε ακέραιο (πχ το '03' θα γίνει 3). 
            month_index = int(month_str) - 1

            # Προσθέτουμε +1 γεγονός στον αντίστοιχο μήνα
            monthly_counts[month_index] += 1

        return monthly_counts

# --- 3. ΓΡΑΦΙΚΟ ΠΕΡΙΒΑΛΛΟΝ (GUI) ---
class CalendarUI:
    """Διαχειρίζεται το GUI της εφαρμογής χρησιμοποιώντας CustomTkinter"""

    # Λίστα από μήνες για μελλοντική χρήση στο UI (Πρώτο στοιχείο = "" ώστε 1=Ιανουάριος)
    months_desc = ["", "Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος", "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος"]
    def __init__(self, root):
        """Αρχικοποιεί το γραφικό περιβάλλον της εφαρμογής (GUI), τη σύνδεση με τη βάση, τη σημερινή ημερομηνία και ξεκινάει τις ρουτίνες ανανέωσης"""
        now = datetime.now() # Παίρνουμε την ώρα συστήματος (τώρα)
        self.current_month = now.month # π.χ. 3
        self.current_year = now.year   # π.χ. 2026
        self.events_memory = {} # Το λεξικό που θα κρατάει ID, start_dt, end_dt
        self.root = root
        self.root.title("Project 22 - Ηλεκτρονικό Ημερολόγιο")
        self.root.geometry("1300x700")
        self.db = CalendarDB()
        self.setup_ui()
        self.refresh_view()
        self.update_countdowns()

    def setup_ui(self):
        """Ορίζει τη βασική διάταξη (grid layout) του παραθύρου και καλεί τις επιμέρους συναρτήσεις που χτίζουν το ημερολόγιο, τη φόρμα και τον πίνακα"""

        # Ορίζουμε την συμπεριφορά του grid layout με weights
        self.root.grid_rowconfigure(0, weight=0, minsize=360) # Το πάνω μέρος του παραθύρου μένει σταθερό, με minsize ώστε να παραμένει και όταν έχω λιγότερες σειρές
        self.root.grid_rowconfigure(1, weight=1) # Το κάτω μέρος του παραθύρου μένει σταθερό
        self.root.grid_columnconfigure(0, weight=2) # Το αριστερό μέρος του παραθύρου είναι ελαστικό και κλέβει τον πιο πολύ χώρο
        self.root.grid_columnconfigure(1, weight=1) # Το δεξί μέρος του παραθύρου είναι και αυτό ελαστικό αλλά του αναλογεί πιο λίγος χώρος

        # ΠΑΝΩ ΑΡΙΣΤΕΡΑ [Frame που περιέχει το calendar] (για να παραμένει σταθερή η θέση του σε κάθε refresh)
        # Φτιάχνουμε το container ΕΔΩ για να μην δημιουργείται ξανά και ξανά
        self.calendar_container = ctk.CTkFrame(self.root, width=650, height=350)
        self.calendar_container.grid(row=0, column=0, pady=10, padx=5, sticky="nsew")

        # Απαγορεύουμε στο Frame να αυξομειώνεται
        self.calendar_container.pack_propagate(False)

        # Καλούμε τη νέα συνάρτηση που φτιάχνει τα βελάκια ΜΙΑ ΦΟΡΑ
        self.build_calendar_navbar()

        self.calendar_inframe()
        self.manage_event()

        # ΚΑΤΩ ΑΡΙΣΤΕΡΑ [Frame TREEVIEW (ΠΙΝΑΚΑΣ)]
        self.tree_frame = ctk.CTkFrame(self.root)
        self.tree_frame.grid(row = 1, column=0, padx=5, pady=(0,10), sticky="nsew")

        self.tree = ttk.Treeview(self.tree_frame, columns=("Τίτλος", "Έναρξη", "Διάρκεια", "Notification"), show='headings')
        self.tree.heading("Τίτλος", text="Τίτλος")
        self.tree.heading("Έναρξη", text="Έναρξη")
        self.tree.heading("Διάρκεια", text="Διάρκεια")
        self.tree.heading("Notification", text="Ειδοποίηση")

        # Fixed πλάτος για στήλες
        self.tree.column("Έναρξη", width=130, anchor="center")
        self.tree.column("Διάρκεια", width=80, anchor="center")
        self.tree.column("Notification", width=150, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Όταν αφήνει ο χρήστης το mouse-1 πάνω σε μία εγγραφή, γεμίζω τα entries τα στοιχεία της
        self.tree.bind("<ButtonRelease-1>", self.fill_entries_from_event)

        # ΚΑΤΩ ΔΕΞΙΑ [Γράφημα & Σχόλιο]---------------------------
        self.graph_plot_inframe()
        self.draw_graph()
    
    def build_calendar_navbar(self):
        """Φτιάχνει το περίβλημα του ημερολογίου και τα βελάκια ΜΟΝΟ μια φορά."""
        
        self.label = ctk.CTkLabel(master = self.calendar_container ,text="Ημερολόγιο", font=('Arial', 14, 'bold'))
        self.label.pack(pady=2, padx=10, fill="x")

        # Ένα container για τα κουμπιά πλοήγησης
        nav_frame = ctk.CTkFrame(master = self.calendar_container, fg_color= "transparent")
        nav_frame.pack(pady=5, padx=10, anchor="n")

        # Κουμπιά με όνομα Μήνα / Χρονιάς ανάμεσα στα βελάκια

        # Ένα ενιαίο "pill" frame για τον Μήνα
        nav_month = ctk.CTkFrame(master = nav_frame, fg_color= SAND_COLOR, corner_radius=15)
        nav_month.grid(row=0, column=0, padx=10) # padx δημιουργεί κενό ανάμεσα στα δύο pill Μήνας / Έτος)
        # Κουμπί < Μήνα (padx αριστερά για να μην "κοβει" το rounded corner)
        ctk.CTkButton(nav_month, text="<", width=30, text_color="black", fg_color="transparent", hover_color="#C8C8C8",
                        command=lambda: self.change_month(-1)).pack(side="left", padx=(10, 0))
        # Zoom out button Μήνα με ένα σταθερό πλάτος (width=90) που αποθηκεύουμε σε μεταβλητή για να του αλλάζουμε το text αργότερα
        self.btn_month_label = ctk.CTkButton(nav_month, text=f"{self.months_desc[self.current_month]}", width=90, text_color="black", font=('Arial', 12, 'bold'), fg_color="transparent", hover_color="#C8C8C8", command=lambda: self.show_months())
        self.btn_month_label.pack(side="left")
        # Κουμπί > Μήνα (padx δεξιά για να μην "κοβει" το rounded corner)
        ctk.CTkButton(nav_month, text=">", width=30, text_color="black", fg_color="transparent", hover_color="#C8C8C8",
                        command=lambda: self.change_month(1)).pack(side="left", padx=(0, 10)) # Με λίγο padx για κενό
        
        # Ένα ενιαίο "pill" frame για το Έτος
        nav_year = ctk.CTkFrame(master = nav_frame, fg_color= SAND_COLOR, corner_radius=15)
        nav_year.grid(row=0, column=1)        
        # Κουμπί < Έτους
        ctk.CTkButton(nav_year, text="<", width=30, text_color="black", fg_color="transparent", hover_color="#C8C8C8",
                        command=lambda: self.change_year(-1)).pack(side="left", padx=(10, 5))
        # Label Έτους που αποθηκεύουμε σε μεταβλητή για να του αλλάζουμε το text αργότερα
        self.lbl_year_label = ctk.CTkLabel(master=nav_year, text=f"{self.current_year}", text_color="black", font=('Arial', 12, 'bold'))
        self.lbl_year_label.pack(side="left")
        # Κουμπί > Έτους
        ctk.CTkButton(nav_year, text=">", width=30, text_color="black", fg_color="transparent", hover_color="#C8C8C8",
                        command=lambda: self.change_year(1)).pack(side="left", padx=(5, 10))
        
        # Για customtkinter κάνω pack ακόμα ένα container του grid των κουμπιών
        self.cal_grid_container = ctk.CTkFrame(master = self.calendar_container, fg_color="transparent") # Το border το έχουμε προσωρινά για να μας βοηθά στην δημιουργία του UI
        self.cal_grid_container.pack(pady=5, padx=10, fill="both", expand=True)

    def calendar_inframe(self):
        """Σχεδιάζει το ημερολόγιο (μήνες, ημέρες, κουμπιά πλοήγησης) στο πάνω αριστερά τμήμα της εφαρμογής και χρωματίζει τις μέρες που έχουν γεγονότα."""

        # Ανανέωση των labels στο Navigation Bar (Δεν σβήνουμε τα κουμπιά, απλά αλλάζουμε το κείμενο)
        self.btn_month_label.configure(text=f"{self.months_desc[self.current_month]}")
        self.lbl_year_label.configure(text=f"{self.current_year}")

        # Καθαρίζουμε ΜΟΝΟ τον καμβά των ημερών (γρήγορο)
        for widget in self.cal_grid_container.winfo_children():
            widget.destroy()
            
        # Ξαναφτιάχνουμε τις στήλες (Το uniform="group1" θα δίνει ίδιο πλάτος σε όλα)
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
                    button_color = "#E0E0E0"
                    txt_color = "black"

                    if day in events_lookup:
                        if int(events_lookup[day]) == 1: # Cast ως int
                            button_color = ACTIVE_EVENT_COLOR
                            txt_color = "white"
                        else:
                            button_color = IDLE_EVENT_COLOR
                            txt_color = "white"

                    # Σύνδεση με τη συμπλήρωση των πεδίων (προαιρετικό αλλά χρήσιμο)
                    btn = ctk.CTkButton(self.cal_grid_container, text=str(day), width=40, height=35,
                                        fg_color=button_color, text_color=txt_color,
                                        hover_color=SAND_COLOR, 
                                        command=lambda d=day: self.fill_entries_from_cal(d))
                    btn.grid(row=r+1, column=c, padx=3, pady=3, sticky="we")


    def manage_event(self):
        """Δημιουργεί τη φόρμα εισαγωγής στοιχείων (πάνω δεξιά) με τα πεδία για τον τίτλο, την ημερομηνία, τις ώρες και το σχόλιο του γεγονότος"""

        # ΠΑΝΩ ΔΕΞΙΑ [Frame Εισαγωγής]
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
        self.ent_title = ctk.CTkEntry(in_grid_container, placeholder_text="Εισάγετε Τίτλο ή επιλέξτε ένα γεγονός")
        self.ent_title.grid(row=0, column=1, sticky="we", padx=5, pady=2)

        ctk.CTkLabel(in_grid_container, text="Ημερομηνία:").grid(row=1, column=0, sticky="w")
        date_subframe = ctk.CTkFrame(in_grid_container)
        date_subframe.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        self.ent_day = ctk.CTkEntry(date_subframe, width=40, placeholder_text="ΗΗ")
        self.ent_day.pack(side="left")
        ctk.CTkLabel(date_subframe, text="/").pack(side="left")
        self.ent_month = ctk.CTkEntry(date_subframe, width=40, placeholder_text="ΜΜ")
        self.ent_month.pack(side="left")
        ctk.CTkLabel(date_subframe, text="/").pack(side="left")
        self.ent_year = ctk.CTkEntry(date_subframe, width=50, placeholder_text="ΕΕΕΕ")
        self.ent_year.pack(side="left")

        ctk.CTkLabel(in_grid_container, text="Ώρα Έναρξης:").grid(row=2, column=0, sticky="w")
        self.ent_time_start = ctk.CTkEntry(in_grid_container, placeholder_text="ΩΩ:ΛΛ")
        self.ent_time_start.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(in_grid_container, text="Ώρα Λήξης:").grid(row=3, column=0, sticky="w", pady=2)
        self.ent_time_end = ctk.CTkEntry(in_grid_container, placeholder_text="ΩΩ:ΛΛ")
        self.ent_time_end.grid(row=3, column=1, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(in_grid_container, text="Σχόλιο:").grid(row=4, column=0, sticky="w", pady=2)
        self.ent_comment = ctk.CTkTextbox(in_grid_container, height=120, border_width=2, border_color="#979DA2") # Αυτό το border_width, και border_color μπαίνουν για να μοιάζει το πεδίο "Σχόλιο" με τα υπόλοιπα
        self.ent_comment.grid(row=4, column=1, sticky="we", padx=5, pady=2)
        
        # Κουμπιά Ενεργειών
        btn_frame = ctk.CTkFrame(in_grid_container)
        btn_frame.grid(row=5, columnspan=2, pady=20, sticky="we") # we για stretch δεξιά/αριστερά

        # Προσαρμογή buttons για customtkinter
        ctk.CTkButton(btn_frame, text="Αποθήκευση", command=self.save_event, fg_color="#27ae60", hover_color="#2ecc71", text_color="white").pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_frame, text="Διαγραφή", command=self.delete_selected, fg_color="#c0392b", hover_color="#e74c3c", text_color="white").pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_frame, text="Εμφάνιση Όλων", command=self.refresh_view, fg_color="#2980b9", hover_color="#3498db", text_color="white").pack(side="left", padx=5, expand=True)        

    def graph_plot_inframe(self):
        """Στήνει το κάτω δεξιά τμήμα της εφαρμογής που περιέχει το ραβδόγραμμα στατιστικών"""

        # ΚΑΤΩ ΔΕΞΙΑ [Γράφημα]
        # Φτιάχνουμε το graph_frame με στρογγυλές γωνίες και το βάζουμε στο root
        self.graph_frame = ctk.CTkFrame(self.root)

        # To padx=10 και pady=10 το κρατάει σε απόσταση από τους τοίχους του παραθύρου
        self.graph_frame.grid(row=1, column=1, padx=5, pady=(0,10), sticky="nsew")

    def draw_graph(self):
        """Σχεδιάζει ράβδους γεγονότων ανά μήνα μέσα στο self.graph_frame"""

        # Μικρό Description μηνών για το γράφημα
        short_months = ["Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαι", "Ιουν", "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ"]

        # Παίρνουμε τα στατιστικά: 
        stats = self.db.get_yearly_stats(self.current_year)
        
        # Καθαρίζουμε το παλιό γράφημα (αν υπάρχει)
        for widget in self.graph_frame.winfo_children(): # Όλα τα αντικείμενα του self.graph_frame
            widget.destroy()
        
        # Φτιάχνουμε το νέο γράφημα του Matplotlib (με Figure και FigureCanvasTkAgg για να γίνει embed και όχι pop-up window)
        fig = Figure(figsize=(5, 3), dpi=100)
        
        # Το DBDBDB είναι το default χρώμα του customTkinter, έτσι δεν θα ζωγραφιστούν "sharp corners" ως περίγραμμα του γραφήματος
        fig.patch.set_facecolor('#DBDBDB') 
        ax = fig.add_subplot(111) 
        ax.set_facecolor('#DBDBDB')

        # Αφαίρεση του περιγράμματος γύρω από το γράφημα
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Σχεδίαση μπάρας
        bars = ax.bar(short_months, stats, color="#2980b9", width=0.6) # Μπλε χρώμα

        # Τίτλος και ρυθμίσεις αξόνων
        #ax.set_title(f"Γεγονότα ανά Μήνα ({self.current_year})", fontsize=10, fontweight='bold') # Label γραφήματος
        ax.tick_params(axis='x', labelsize=9, rotation=45) # Γυρνάμε τα ονόματα των μηνών 45 μοίρες
        ax.tick_params(axis='y', labelsize=9)

        # Προσθήκη του αριθμού γεγονότων πάνω από κάθε μπάρα (αν δεν είναι 0)
        for bar in bars:
            event_count = bar.get_height()
            if event_count > 0:
                ax.text(bar.get_x() + bar.get_width()/2, event_count + 0.1, int(event_count), ha='center', va='bottom', fontsize=9)

        # Ενσωμάτωση στο self.graph_frame
        fig.tight_layout() # Προσαρμόζει αυτόματα τα περιθώρια
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        ctk.CTkLabel(master=self.graph_frame, text=f"Γεγονότα ανά Μήνα ({self.current_year})", font=('Arial', 14, 'bold')).pack(fill="x", pady=5)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def clear_entries(self, day_filter=None): # Φίλτρο ημέρας που θα περαστεί στην refresh_view αν χρειάζεται, όπως πχ όταν καλείται από delete_selected
        """Καθαρίζει τα πεδία εισαγωγής και το TextBox της σύνοψης"""

        self.ent_title.delete(0, "end")
        self.ent_comment.delete("1.0", "end") # Το comment είναι textbox και δεν δέχεται την .delete(0, "end")
        self.ent_day.delete(0, "end")
        self.ent_month.delete(0, "end")
        self.ent_year.delete(0, "end")
        self.ent_time_start.delete(0, "end")
        self.ent_time_end.delete(0, "end")

        # Για να συνεχίσουν να φαίνονται τα Placeholders στα CTkEntries
        # Κάνουμε ένα "κόλπο" Focus Toggle για ΟΛΑ τα πεδία
        # Βάζουμε στη λίστα όσα πεδία έχουν placeholder
        entries_with_placeholders = [self.ent_title, self.ent_day, self.ent_month, self.ent_year, self.ent_time_start, self.ent_time_end]
        
        for entry in entries_with_placeholders:
            entry.focus_set() # Δίνει εστίαση στιγμιαία στο καθένα
            
        self.root.focus_set()           # Το main window παίρνει την εστίαση στο τέλος
        self.root.update_idletasks()    # Ζωγραφίζει ξανά την οθόνη

        self.refresh_view(day_filter)

    def show_months(self):
        """Αντικαθιστά προσωρινά το πλέγμα των ημερών στο ημερολόγιο με ένα πλέγμα 12 κουμπιών για την επιλογή μήνα"""

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
                    btn = ctk.CTkButton(self.cal_grid_container, text=curr_month_btn, fg_color="#E0E0E0", text_color="black", hover_color=SAND_COLOR,
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
            self.draw_graph() # Reload graph για νέα χρονιά
        #Εδώ ακριβώς το ανάποδο από το if
        elif self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
            self.draw_graph() # Reload graph για νέα χρονιά
        self.calendar_inframe() # Κλήση της σωστής μεθόδου

    def change_year(self, delta):
        """Νέα μέθοδος για αλλαγή έτους"""

        self.current_year += delta
        self.calendar_inframe() # Reload calendar
        self.draw_graph() # Reload graph
    
    def fill_entries_from_cal(self, day):
        """Βοηθητική μέθοδος για να γεμίζουν τα Entries όταν πατάς μια μέρα"""

        # Φτιάχνουμε την ημερομηνία σε μορφή YYYY-MM-DD
        date_str = f"{self.current_year}-{self.current_month:02d}-{day:02d}"

        # Καθαρίζουμε τα υπόλοιπα πεδία
        self.ent_title.delete(0, "end")
        self.ent_time_start.delete(0, "end")
        self.ent_time_end.delete(0, "end")
        self.ent_comment.delete("1.0", "end")
    
        # Ενημερώνουμε τα κουτάκια (Entries) (Μέρα, Μήνας, Χρόνος)
        self.ent_day.delete(0, "end"); self.ent_day.insert(0, str(day))
        self.ent_month.delete(0, "end"); self.ent_month.insert(0, str(self.current_month))
        self.ent_year.delete(0, "end"); self.ent_year.insert(0, str(self.current_year))

        # Για να συνεχίσουν να φαίνονται τα Placeholders στα CTkEntries
        # Κάνουμε ένα "κόλπο" Focus Toggle για ΟΛΑ τα πεδία
        # Βάζουμε στη λίστα όσα πεδία έχουν placeholder
        entries_with_placeholders = [self.ent_title, self.ent_day, self.ent_month, self.ent_year, self.ent_time_start, self.ent_time_end]
        
        for entry in entries_with_placeholders:
            entry.focus_set() # Δίνει εστίαση στιγμιαία στο καθένα
            
        self.root.focus_set()           # Το main window παίρνει την εστίαση στο τέλος
        self.root.update_idletasks()    # Ζωγραφίζει ξανά την οθόνη

        # Καλούμε την refresh_view με την ημερομηνία-φίλτρο!
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
        event_comment = self.events_memory[selected_item]["comment"]

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
            self.ent_comment.delete("1.0", "end"); self.ent_comment.insert("1.0", event_comment)
            
            self.ent_day.delete(0, "end"); self.ent_day.insert(0, d)
            self.ent_month.delete(0, "end"); self.ent_month.insert(0, m)
            self.ent_year.delete(0, "end"); self.ent_year.insert(0, y)
            
            self.ent_time_start.delete(0, "end"); self.ent_time_start.insert(0, time_start)
            self.ent_time_end.delete(0, "end"); self.ent_time_end.insert(0, time_end)

    def save_event(self):
        """Διαβάζει τα δεδομένα από τη φόρμα, ελέγχει (απουσία επικάλυψης, σωστές ώρες) και αποθηκεύει το νέο γεγονός στη βάση"""

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

            # 4. Η λήξη πρέπει να είναι μετά την έναρξη
            if end_dt <= start_dt:
                messagebox.showwarning("Εσφαλμένη Ώρα", "Η ώρα λήξης πρέπει να είναι μετά την ώρα έναρξης!")
                return

            # 5. Έλεγχος Επικάλυψης
            if self.db.is_slot_busy(start_dt, end_dt):
                messagebox.showwarning("Σύγκρουση", "Η συγκεκριμένη ώρα είναι ήδη δεσμευμένη!")
                return

            if now <= end_dt: # Αν βάλουμε start_dt <= now <= end_dt , σε μία αυριανή ημερομηνία now <= start_dt άρα θα μας το κάνει inactive
                is_active = 1
            else:
                is_active = 0
            
            # 6. Αποθήκευση
            new_ev = Event(None, self.ent_title.get(), self.ent_comment.get("1.0", "end-1c"), start_dt, end_dt, notification=is_active)
            self.db.new_event(new_ev)
            messagebox.showinfo("Επιτυχία", "Το γεγονός προστέθηκε!")

            # 7. Φίλτρο για το refresh_view ώστε να προβληθεί η μέρα στην οποία ανήκει το αποθηκευμένο event
            day_to_show = start_dt.strftime('%Y-%m-%d') # Παίρνουμε το YYYY-MM-DD
            self.refresh_view(day_to_show) # Ανανεώνουμε μόνο για αυτή τη μέρα
            self.draw_graph() # Reload graph (Για να περιέχει το νέο γεγονός)
        except ValueError:
            messagebox.showerror("Λάθος", "Παρακαλώ εισάγετε σωστή ημερομηνία και ώρα (π.χ. 12:00)")
            

    def delete_selected(self):
        """Διαγράφει το επιλεγμένο γεγονός από τον πίνακα (Treeview) και από τη βάση δεδομένων, αφού ζητήσει επιβεβαίωση από τον χρήστη"""

        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Επιλογή", "Παρακαλώ επιλέξτε ένα γεγονός από τον πίνακα.")
            return
        
        selected_item = selected_items[0] # Παίρνουμε την "ταμπέλα" του tree (π.χ. 'I001')
        event_id = self.events_memory[selected_item]["db_id"]

        # Βρίσκουμε τη μέρα που αφορά το γεγονός ΠΡΙΝ το διαγράψουμε
        event_start = self.events_memory[selected_item]["start"]
        day_to_show = event_start.strftime('%Y-%m-%d')
        
        if messagebox.askyesno("Επιβεβαίωση", "Θέλετε σίγουρα να διαγράψετε αυτό το γεγονός;"):
            self.db.delete_event(event_id)
            self.clear_entries(day_to_show) # Η clear_entries περιέχει και την refresh_view, με φίλτρο την ημέρα του γεγονότος που διαγράφεται
            self.draw_graph() # Reload graph (Για να διαγραφεί το γεγονός και από το γράφημα)

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
            item_id = self.tree.insert("", "end", values=(row[1], row[3], temp_ev.get_duration(), " ")) # Στην ειδοποίηση βάζω προρσωρινά κενό
            # Η insert στην tkinter θα μας δώσει το id που έχει αυτό το αντικείμενο στον πίνακα

            # Εισαγωγή απαραίτητων δεδομένων στο λεξικό
            self.events_memory[item_id] = {
                "db_id": row[0],
                "comment": row[2], # Αποθήκευση σχόλιου για χρήση σε comment box, και fill_entries_from_event
                "start": start,
                "end": end,
                "status": status_note
            }

        # Ανανέωση των κουμπιών (Για να έχουμε χρώματα σωστά)
        self.calendar_inframe()
#=========================================================================================  

    def update_countdowns(self):
        """Ανανεώνει την αντίστροφη μέτρηση ή την κατάσταση (Σε εξέλιξη / Έληξε) για κάθε γεγονός του πίνακα. Εκτελείται αναδρομικά κάθε 1s"""

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

            try:
                # Περίπτωση 1: Το Event είναι στο Μέλλον (Αντ. Μέτρηση)
                if now < start_dt:
                        diff = start_dt - now
                        hours, remainder = divmod(diff.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        values[3] = f"{diff.days}ημ {hours:02d}:{minutes:02d}:{seconds:02d}"
                        self.tree.item(item, values=values)
                
                # Περίπτωση 2: Το Event είναι στο Παρόν (Σε εξέλιξη)
                elif start_dt <= now <= end_dt:
                    if values[3] != "Σε εξέλιξη": # Για να μην ενημερώνεται το tree κάθε δευτερόλεπτο άδικα 
                        values[3] = "Σε εξέλιξη"
                        self.tree.item(item, values=values)

                # Περίπτωση 3: Το Event ήταν στο παρελθόν (Έλήξε)
                else:
                    # Αλλάζουμε το Tree στην οθόνη, αν δεν είναι ήδη "Έληξε"
                    if values[3] != "Έληξε":
                        values[3] = "Έληξε"
                        self.tree.item(item, values=values)

                    # Αν το Event είναι ακόμα σε εξέλιξη σύμφωνα με την μνήμη μας (λεξικό), αυτό σημαίνει οτι μόλις έληξε
                    # Άρα πρέπει να ενημερώνουμε την βάση με notification 0
                    if item_mem["status"] == 1:
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