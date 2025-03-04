import requests
import tkinter as tk
from tkinter import ttk, Canvas, Frame, Button, Toplevel, Label, Entry
from PIL import Image, ImageTk
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import threading
import time
from datetime import datetime

# Tkinter-Hauptfenster
root = tk.Tk()
root.title("Pegel-Monitor")
root.geometry("1200x800")

# Scrollbarer Bereich erstellen
canvas = Canvas(root)
scroll_y = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
frame = Frame(canvas)

frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=frame, anchor="nw")
canvas.configure(yscrollcommand=scroll_y.set)

canvas.pack(side="left", fill="both", expand=True)
scroll_y.pack(side="right", fill="y")

# Liste für Messstationen
station_frames = {}
refresh_interval = 300  # Standard-Refresh-Rate auf 5 Minuten
refresh_thread = None


def fetch_data(pegel_url, frame):
    """Holt aktuelle Pegeldaten für eine bestimmte Messstation und aktualisiert die Anzeige."""
    pegel_id = pegel_url.split("id=")[-1]

    try:
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(service=service, options=options)
        driver.get(pegel_url)
        time.sleep(5)

        try:
            selected_position = driver.find_element(By.ID, "ID_SELECT_POS").text
        except Exception:
            selected_position = "Unbekannte Position"

        wasserstand = driver.find_element(By.ID, "ID_INFO_W").text
        wasserstand_wd = driver.find_element(By.ID, "ID_INFO_WD").text
        wasserstand_wz = driver.find_element(By.ID, "ID_INFO_WZ").text
        abfluss = driver.find_element(By.ID, "ID_INFO_Q").text
        abfluss_qd = driver.find_element(By.ID, "ID_INFO_QD").text
        abfluss_qz = driver.find_element(By.ID, "ID_INFO_QZ").text
    
    except Exception as e:
        print(f"⚠️ Fehler bei {pegel_url}: {e}")
        driver.quit()
        return
    
    finally:
        driver.quit()

    def update_ui():
        # Zeitpunkt des Refreshs speichern
        now = datetime.now().strftime("%H:%M:%S")
        frame["label_wasserstand"].config(text=f"Wasserstand: {wasserstand} cm ({wasserstand_wd}) - {wasserstand_wz}")
        frame["label_abfluss"].config(text=f"Abfluss: {abfluss} m³/s ({abfluss_qd}) - {abfluss_qz}")
        frame["title_label"].config(text=f"Messstation {pegel_id} - {selected_position}")
        frame["last_updated"].config(text=f"Letzte Aktualisierung: {now}")

        print(f"🔄 {selected_position} (ID: {pegel_id}) aktualisiert um {now}")

    root.after(0, update_ui)


def show_diagram(pegel_url, diagram_type):
    """Öffnet ein separates Fenster mit dem ausgewählten Diagramm."""
    pegel_id = pegel_url.split("id=")[-1]
    diagram_url = f"https://www.hvz.baden-wuerttemberg.de/gifs/{pegel_id}-{140 if diagram_type == 'wasserstand' else 340}.GIF"
    
    def load_image_from_url(url):
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return ImageTk.PhotoImage(img)

    diagram_window = Toplevel(root)
    diagram_window.title(f"{ 'Wasserstand' if diagram_type == 'wasserstand' else 'Abfluss' }-Diagramm - Messstation {pegel_id}")
    diagram_window.geometry("800x600")

    img = load_image_from_url(diagram_url)

    label = tk.Label(diagram_window, text=f"{ 'Wasserstand' if diagram_type == 'wasserstand' else 'Abfluss' }-Diagramm")
    label.pack()
    canvas = tk.Canvas(diagram_window, width=img.width(), height=img.height())
    canvas.pack()
    canvas.create_image(0, 0, anchor=tk.NW, image=img)

    diagram_window.mainloop()

def auto_refresh():
    """Aktualisiert alle Messstationen nach der eingestellten Zeit."""
    global refresh_thread
    while True:
        time.sleep(refresh_interval)
        for pegel_url in station_frames.keys():
            threading.Thread(target=fetch_data, args=(pegel_url, station_frames[pegel_url]), daemon=True).start()


def restart_auto_refresh():
    """Stoppt den alten Refresh-Thread und startet ihn mit der neuen Rate."""
    global refresh_thread
    if refresh_thread:
        refresh_thread = None  # Den alten Thread beenden
    refresh_thread = threading.Thread(target=auto_refresh, daemon=True)
    refresh_thread.start()


def set_refresh_rate():
    """Öffnet ein Fenster zum Setzen der Refresh-Rate in Minuten."""
    popup = Toplevel(root)
    popup.title("Refresh-Rate ändern")
    popup.geometry("300x150")

    Label(popup, text="Neue Refresh-Rate (Minuten):", font=("Arial", 12)).pack(pady=10)

    entry = Entry(popup, width=10)
    entry.insert(0, str(refresh_interval // 60))  # Sekunden in Minuten umrechnen
    entry.pack(pady=5)

    def update_refresh():
        global refresh_interval
        try:
            new_rate = int(entry.get()) * 60  # Minuten in Sekunden umrechnen
            if new_rate > 0:
                refresh_interval = new_rate
                popup.destroy()
                print(f"✅ Neue Refresh-Rate: {refresh_interval // 60} Minuten")
                restart_auto_refresh()  # Den Refresh-Prozess mit der neuen Rate neu starten
            else:
                print("⚠️ Bitte eine positive Zahl eingeben.")
        except ValueError:
            print("⚠️ Ungültige Eingabe! Bitte eine Zahl eingeben.")

    Button(popup, text="Speichern", command=update_refresh, bg="lightblue", font=("Arial", 12)).pack(pady=10)


def open_url_popup():
    """Öffnet ein Popup-Fenster zur Eingabe der Pegel-URL."""
    popup = Toplevel(root)
    popup.title("Messstation hinzufügen")
    popup.geometry("400x200")

    Label(popup, text="Pegel-URL eingeben:", font=("Arial", 12)).pack(pady=10)
    url_entry = Entry(popup, width=40)
    url_entry.pack(pady=5)

    def submit_url():
        pegel_url = url_entry.get()
        if pegel_url:
            add_station(pegel_url)
            popup.destroy()

    Button(popup, text="Hinzufügen", command=submit_url, bg="lightblue", font=("Arial", 12)).pack(pady=10)
    url_entry.bind("<Return>", lambda event: submit_url())


def add_station(pegel_url):
    """Fügt eine neue Messstation über die URL hinzu."""
    pegel_id = pegel_url.split("id=")[-1]

    station_frame = tk.Frame(frame, bd=2, relief="ridge", padx=10, pady=10)
    station_frame.pack(fill="x", padx=10, pady=5)

    title_label = tk.Label(station_frame, text=f"Messstation {pegel_id} - Lädt...", font=("Arial", 16, "bold"))
    title_label.pack()

    label_wasserstand = tk.Label(station_frame, text="Wasserstand: -- cm", font=("Arial", 12))
    label_wasserstand.pack()

    label_abfluss = tk.Label(station_frame, text="Abfluss: -- m³/s", font=("Arial", 12))
    label_abfluss.pack()

    Button(station_frame, text="Wasserstand-Diagramm anzeigen", command=lambda: show_diagram(pegel_url, "wasserstand")).pack()
    Button(station_frame, text="Abfluss-Diagramm anzeigen", command=lambda: show_diagram(pegel_url, "abfluss")).pack()

    last_updated = tk.Label(station_frame, text="Letzte Aktualisierung: --:--:--", font=("Arial", 10, "italic"))
    last_updated.pack()

    station_frames[pegel_url] = {"title_label": title_label, "label_wasserstand": label_wasserstand, "label_abfluss": label_abfluss, "last_updated": last_updated}
    threading.Thread(target=fetch_data, args=(pegel_url, station_frames[pegel_url]), daemon=True).start()


menu_bar = tk.Menu(root)
root.config(menu=menu_bar)
menu_bar.add_command(label="Messstation hinzufügen", command=open_url_popup)
menu_bar.add_command(label="Refresh-Rate ändern", command=set_refresh_rate)

restart_auto_refresh()  # Startet den Auto-Refresh direkt beim Start
root.mainloop()
