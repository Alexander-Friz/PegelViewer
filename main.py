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
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt



# Tkinter-Hauptfenster
root = tk.Tk()
root.title("Pegel-Monitor")
root.geometry("1200x800")

# Scrollbarer Bereich erstellen
canvas = Canvas(root)
scroll_y = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
frame = Frame(canvas)

frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")
def on_frame_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

frame.bind("<Configure>", on_frame_configure)

# Scrollen mit der Maus aktivieren
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows/macOS
canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux scroll up
canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))   # Linux scroll down



for i in range(3):
    frame.grid_columnconfigure(i, weight=1)

canvas.configure(yscrollcommand=scroll_y.set)
canvas.pack(side="left", fill="both", expand=True)
scroll_y.pack(side="right", fill="y")

# Variablen
dark_mode = False
station_entries = []
refresh_interval = 300  # 5 Minuten
refresh_thread = None

# Standard-Messstationen
default_stations = [
    "https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00063",
    "https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00061",
    "https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00032",
    "https://hvz.baden-wuerttemberg.de/pegel.html?id=00066",
    "https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00065",
    "https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00045",
    "https://hvz.baden-wuerttemberg.de/pegel.html?id=00152",
    "https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00105"
]

def show_history_plot():
    if not station_entries:
        print("⚠️ Keine Daten vorhanden.")
        return

    plt.figure(figsize=(10, 6))

    for entry in station_entries:
        times = [t[0] for t in entry["history"]]
        values = [t[1] for t in entry["history"]]
        pegel_id = entry["url"].split("id=")[-1]
        if times and values:
            plt.plot(times, values, label=f"Station {pegel_id}")

    plt.xlabel("Zeit")
    plt.ylabel("Wasserstand (cm)")
    plt.title("Pegelverlauf")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def rearrange_station_frames():
    width = root.winfo_width()
    if width > 1000:
        columns = 3
    elif width > 600:
        columns = 2
    else:
        columns = 1

    for i in range(columns):
        frame.grid_columnconfigure(i, weight=1)

    for index, entry in enumerate(station_entries):
        row = index // columns
        col = index % columns
        entry["frame"].grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

def toggle_dark_mode():
    global dark_mode
    dark_mode = not dark_mode

    bg_color = "#2e2e2e" if dark_mode else "white"
    fg_color = "white" if dark_mode else "black"

    root.configure(bg=bg_color)
    frame.configure(bg=bg_color)
    canvas.configure(bg=bg_color)

    for entry in station_entries:
        entry["frame"].configure(bg=bg_color)
        for widget in entry["widgets"].values():
            widget.configure(bg=bg_color, fg=fg_color)
def fetch_data(pegel_url, widgets):
    pegel_id = pegel_url.split("id=")[-1]
    driver = None  # wichtig

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

        selected_position = driver.find_element(By.ID, "ID_SELECT_POS").text
        wasserstand = driver.find_element(By.ID, "ID_INFO_W").text
        wasserstand_wd = driver.find_element(By.ID, "ID_INFO_WD").text
        wasserstand_wz = driver.find_element(By.ID, "ID_INFO_WZ").text
        abfluss = driver.find_element(By.ID, "ID_INFO_Q").text
        abfluss_qd = driver.find_element(By.ID, "ID_INFO_QD").text
        abfluss_qz = driver.find_element(By.ID, "ID_INFO_QZ").text

    except Exception as e:
        print(f"⚠️ Fehler bei {pegel_url}: {e}")
        return

    finally:
        if driver:
            driver.quit()  # Nur aufrufen, wenn wirklich initialisiert


    def update_ui():
        now = datetime.now().strftime("%H:%M:%S")
        widgets["label_wasserstand"].config(text=f"Wasserstand: {wasserstand} cm ({wasserstand_wd}) - {wasserstand_wz}")
        widgets["label_abfluss"].config(text=f"Abfluss: {abfluss} m³/s ({abfluss_qd}) - {abfluss_qz}")
        widgets["title_label"].config(text=f"Messstation {pegel_id} - {selected_position}")
        widgets["last_updated"].config(text=f"Letzte Aktualisierung: {now}")
        print(f"🔄 {selected_position} (ID: {pegel_id}) aktualisiert um {now}")

        for entry in station_entries:
            if entry["url"] == pegel_url:
                try:
                    value = int(wasserstand)
                    entry["history"].append((datetime.now(), value))
                except ValueError:
                    print(f"⚠️ Ungültiger Wert für Wasserstand: {wasserstand}")
            #break


    root.after(0, update_ui)

def show_diagram(pegel_url, diagram_type):
    pegel_id = pegel_url.split("id=")[-1]
    diagram_url = f"https://www.hvz.baden-wuerttemberg.de/gifs/{pegel_id}-{140 if diagram_type == 'wasserstand' else 340}.GIF"

    def load_image_from_url(url):
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return ImageTk.PhotoImage(img)

    diagram_window = Toplevel(root)
    diagram_window.title(f"{diagram_type.capitalize()}-Diagramm - Messstation {pegel_id}")
    diagram_window.geometry("800x600")

    img = load_image_from_url(diagram_url)

    label = tk.Label(diagram_window, text=f"{diagram_type.capitalize()}-Diagramm")
    label.pack()
    canvas = tk.Canvas(diagram_window, width=img.width(), height=img.height())
    canvas.pack()
    canvas.create_image(0, 0, anchor=tk.NW, image=img)
    diagram_window.mainloop()

def auto_refresh():
    global refresh_thread
    while True:
        time.sleep(refresh_interval)
        for entry in station_entries:
            threading.Thread(target=fetch_data, args=(entry["url"], entry["widgets"]), daemon=True).start()

def restart_auto_refresh():
    global refresh_thread
    if refresh_thread:
        refresh_thread = None
    refresh_thread = threading.Thread(target=auto_refresh, daemon=True)
    refresh_thread.start()

def set_refresh_rate():
    popup = Toplevel(root)
    popup.title("Refresh-Rate ändern")
    popup.geometry("300x150")

    Label(popup, text="Neue Refresh-Rate (Minuten):", font=("Arial", 12)).pack(pady=10)
    entry = Entry(popup, width=10)
    entry.insert(0, str(refresh_interval // 60))
    entry.pack(pady=5)

    def update_refresh():
        global refresh_interval
        try:
            new_rate = int(entry.get()) * 60
            if new_rate > 0:
                refresh_interval = new_rate
                popup.destroy()
                print(f"✅ Neue Refresh-Rate: {refresh_interval // 60} Minuten")
                restart_auto_refresh()
            else:
                print("⚠️ Bitte eine positive Zahl eingeben.")
        except ValueError:
            print("⚠️ Ungültige Eingabe! Bitte eine Zahl eingeben.")

    Button(popup, text="Speichern", command=update_refresh, bg="lightblue", font=("Arial", 12)).pack(pady=10)

def open_url_popup():
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
    pegel_id = pegel_url.split("id=")[-1]
    station_frame = tk.Frame(frame, bd=2, relief="ridge", padx=10, pady=10)

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

    widgets = {
        "title_label": title_label,
        "label_wasserstand": label_wasserstand,
        "label_abfluss": label_abfluss,
        "last_updated": last_updated
    }

    station_entries.append({
    "url": pegel_url,
    "frame": station_frame,
    "widgets": widgets,
    "history": []
})


    rearrange_station_frames()
    threading.Thread(target=fetch_data, args=(pegel_url, widgets), daemon=True).start()

# Menü
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)
menu_bar.add_command(label="Messstation hinzufügen", command=open_url_popup)
menu_bar.add_command(label="Refresh-Rate ändern", command=set_refresh_rate)
menu_bar.add_command(label="Pegelverlauf anzeigen", command=show_history_plot)
menu_bar.add_command(label="Darkmode umschalten", command=toggle_dark_mode)

# Initiale Stationen laden
for url in default_stations:
    add_station(url)

# Event-Bindings & Start
root.bind("<Configure>", lambda e: rearrange_station_frames())
restart_auto_refresh()
root.mainloop()
