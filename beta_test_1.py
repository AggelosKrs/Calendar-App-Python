#Βάζουμε τις απαρέτητες βιβλιοθίκες
import customtkinter as ctk
import sqlite3
import calendar
from datetime import datetime
import os

#Ρύθμιση για τη βάση δεδομένων
db_name = "Callendar_event.db"


def init_db():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS events 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       title TEXT, 
                       start_time TEXT, 
                       end_time TEXT)''')
    conn.commit()
    conn.close()

#Η εφαρμογή
class CallendarApp(ctk.CTk):
    def __init__(self):
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month

        super().__init__()
        
        self.title("Ημερολόγιο")
        self.geometry("800x800")

        ctk.set_appearance_mode("dark")

        # Δημιουργία βάσης αν δεν υπάρχει
        init_db() 
        #Καλούμε το UI
        self.setup_ui()
        #Ενημέρωση σε πραγματικό χρόνο
        self.update_loop()
    
    def setup_ui(self):
        self.label = ctk.CTkLabel(self, text="Το Ημερολόγιό μου", font=("Arial", 24, "bold"))
        self.label.pack(pady=20)

        self.calendar_widget()

        #Μετά από πολύ ψάξημο καταλαβαίνουμε ότι πρέπει να κάνουμε ένα container για τα κουμπιά  
        #και για το κάθε σημείο καλό είναι να φτιάχνουμε ένα ώστε να μπορούμε να τοποθετούμε τα πραγματα όπου θέλουμε με ευκολεία
        self.button_container = ctk.CTkFrame(self, fg_color = "transparent")
        self.button_container.pack (pady=10)

        self.insert_button = ctk.CTkButton(self, text="Αποθήκευση", command=self.button_callback)
        self.insert_button.pack(side = "left", padx=10)

        self.delete_button = ctk.CTkButton(self, text="Διαγραφή", command=self.button_callback)
        self.delete_button.pack(side = "left", padx=5)


#---------------------------------------------------------------------------------
    def calendar_widget(self):
      # 1. Καθαρισμός παλιού frame αν υπάρχει
        if hasattr(self, 'calendar_frame'):
            self.calendar_frame.destroy()

        # Κεντρικό Frame Ημερολογίου
        self.calendar_frame = ctk.CTkFrame(self)
        self.calendar_frame.pack(pady=20, padx=20)

        # --- HEADER: Κουμπιά < > και Τίτλος Μήνα ---
        header = ctk.CTkFrame(self.calendar_frame, fg_color="transparent")
        header.pack(fill="x", pady=10)

        btn_prev = ctk.CTkButton(header, text="<", width=40, command=self.prev_month)
        btn_prev.pack(side="left", padx=10)

        # Μετατρέπουμε τον αριθμό μήνα σε όνομα (π.χ. 4 -> April)
        month_name = calendar.month_name[self.current_month]
        lbl_month = ctk.CTkLabel(header, text=f"{month_name} {self.current_year}", font=("Arial", 18, "bold"))
        lbl_month.pack(side="left", expand=True)

        btn_next = ctk.CTkButton(header, text=">", width=40, command=self.next_month)
        btn_next.pack(side="left", padx=10)

        # --- ΠΛΕΓΜΑ ΗΜΕΡΩΝ (Grid System) ---
        days_container = ctk.CTkFrame(self.calendar_frame, fg_color="transparent")
        days_container.pack(pady=5, padx=10)

        # Επικεφαλίδες Δευ-Κυρ
        days_head = ["Δευ", "Τρι", "Τετ", "Πεμ", "Παρ", "Σαβ", "Κυρ"]
        for i, d in enumerate(days_head):
            ctk.CTkLabel(days_container, text=d, font=("Arial", 12, "bold")).grid(row=0, column=i, pady=5)

        # Υπολογισμός ημερών μήνα
        # first_day: 0=Δευτέρα, ..., 6=Κυριακή
        first_day, num_days = calendar.monthrange(self.current_year, self.current_month)

        day_counter = 1
        for row in range(1, 7):
            for col in range(7):
                if row == 1 and col < first_day:
                    # Κενό label για τις μέρες πριν την 1η του μηνός
                    ctk.CTkLabel(days_container, text="").grid(row=row, column=col)
                elif day_counter > num_days:
                    break
                else:
                    btn = ctk.CTkButton(days_container, text=str(day_counter), 
                                        width=45, height=45, corner_radius=8,
                                        fg_color="transparent", border_width=1,
                                        command=lambda d=day_counter: self.day_click(d))
                    btn.grid(row=row, column=col, padx=3, pady=3)
                    day_counter += 1

#---------------------------------------- ΣΥΝΑΡΤΗΣΕΙΣ ΠΛΟΗΓΗΣΗΣ-------------------------
    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.calendar_widget() # Ξανασχεδιάζει το ημερολόγιο
    
    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.calendar_widget() # Ξανασχεδιάζει το ημερολόγιο

#--------------------------------------------------------------------------------------

    
    def button_callback(self):
        print("Το κουμπί πατήθηκε επιτυχώς!")

    def update_loop(self):
        # Αυτή η συνάρτηση τρέχει κάθε 5 δευτερόλεπτα και ανανεώνει τα χρώματα
        #self.refresh_list()
        self.after(5000, self.update_loop)

if __name__== "__main__":
    app = CallendarApp()
    app.mainloop()