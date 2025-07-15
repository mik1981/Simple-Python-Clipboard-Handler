from config import load_config
from clipboard_monitor import ClipboardMonitor
from gui import ClipboardGUI
import os, sys
from tkinter import filedialog, messagebox


def find_or_select_config(default_paths=None):
    """
    Prova a cercare il file config.ini in una lista di posizioni di default.
    Se non lo trova, apre una finestra per selezione manuale.

    :param default_paths: lista di percorsi dove cercare il config.ini
    :return: percorso completo del config.ini trovato o selezionato, oppure None
    """
    default_paths = default_paths or []

    for path in default_paths:
        if os.path.isfile(path):
            print(path)
            return path

    messagebox.showwarning("File config.ini non trovato",
                           "Il file di configurazione 'config.ini' non è stato trovato nelle posizioni predefinite.\n"
                           "Selezionane uno manualmente, oppure annulla per uscire.")

    filepath = filedialog.askopenfilename(
        title="Seleziona il file config.ini",
        filetypes=[("File INI", "*.ini"), ("Tutti i file", "*.*")]
    )
    if filepath and os.path.isfile(filepath):
        return filepath
    return None

def getDefaultPaths():
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        # Se non in bundle, base è la cartella esecuzione script
        base_path = os.path.abspath(".")
    return [
        os.path.join(os.getcwd(), "config.ini"),                  # cartella corrente
        os.path.join(base_path, "config.ini"),
        os.path.join(os.path.expanduser("~"), ".config", "app", "config.ini"),  # profilo utente linux/mac
        os.path.join(os.getenv("APPDATA", ""), "AppName", "config.ini"),        # Windows APPDATA
        # aggiungi altre posizioni di default valide per te
    ]

def main():
    # Lista posizioni preferenziali dove cercare config.ini
    default_config_paths = getDefaultPaths()
    # print(default_config_paths)

    config_path = find_or_select_config(default_config_paths)
    if not config_path:
        messagebox.showerror("Configurazione assente", "Impossibile trovare il file di configurazione. Il programma verrà chiuso.")
        sys.exit(1)

    # Carica config di default usando il percorso `config_path`
    # config_path = 'config.ini'
    actions = load_config(config_path)
    gui = ClipboardGUI(actions)

    def on_clipboard_change(text):
        if any(a.pattern.match(text) for a in gui.actions):
            gui.after(0, lambda: gui.show_actions_for_link(text))

    monitor = ClipboardMonitor(on_clipboard_change)
    monitor.daemon = True
    monitor.start()

    try:
        gui.mainloop()
    finally:
        monitor.stop()

if __name__ == "__main__":
    main()
