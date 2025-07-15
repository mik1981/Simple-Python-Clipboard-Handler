import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import subprocess
import threading
import webbrowser
import datetime

class ActionTab(ttk.Frame):
    def __init__(self, parent, link, actions, close_callback, save_history_callback=None, autoclose=False):
        super().__init__(parent)
        self.link = link
        self.save_history_callback = save_history_callback
        self.actions = actions
        self.close_callback = close_callback
        self.status = tk.StringVar(value="Attesa scelta utente")
        self.status_color = "#FFFFFF"
        self.autoclose = autoclose  # flag per autochiusura

        # Titolo e chiusura
        close_btn = tk.Button(self, text="X", command=self.close, fg="red")
        close_btn.pack(anchor='ne')

        tk.Label(self, text=f"Link: {link}", wraplength=400).pack(pady=5)


        # Frame pulsanti e opzioni
        self.buttons_frame = tk.Frame(self)
        self.buttons_frame.pack(pady=5)

        self.autorun_vars = []
        for idx, action in enumerate(actions):
            frame = tk.Frame(self.buttons_frame)
            frame.pack(fill='x', pady=2)

            btn = tk.Button(frame, text=action.label, command=lambda a=action: self.run_action(a))
            btn.pack(side='left')

            var_shell = tk.BooleanVar(value=action.run_in_shell)
            cb_shell = tk.Checkbutton(frame, text='Run in shell', variable=var_shell)
            cb_shell.pack(side='left', padx=5)

            var_autorun = tk.BooleanVar(value=action.autorun)
            cb_autorun = tk.Checkbutton(frame, text='Autorun', variable=var_autorun)
            cb_autorun.pack(side='left', padx=5)

            # Salviamo le variabili per aggiornare lo stato dopo
            self.autorun_vars.append((action, var_shell, var_autorun))

        # Text widget per output
        self.output_text = tk.Text(self, height=10, wrap='word')
        self.output_text.pack(expand=True, fill='both', pady=5)

        # Tag per evidenziazione
        self.output_text.tag_config('warning', foreground='orange')
        self.output_text.tag_config('note', foreground='blue')
        self.output_text.tag_config('error', foreground='red')

        # Stato
        self.status_label = tk.Label(self, textvariable=self.status, bg=self.status_color, justify='left')
        self.status_label.pack(fill='x', pady=5)
        self.status_label.bind('<Configure>', self._update_wraplength)


    def set_status(self, text, color):
        # Aggiorna testo e colore sfondo in modo thread-safe tramite .after
        def update():
            self.status.set(text)
            self.status_label.configure(bg=color)
        self.status_label.after(0, update)

    def _update_wraplength(self, event):
        # Imposta wraplength pari alla larghezza attuale del widget meno un margine
        new_wraplength = event.width - 10
        if new_wraplength < 20:
            new_wraplength = 20  # limite minimo per evitare problemi
        self.status_label.config(wraplength=new_wraplength)

    def run_action(self, action):
        def worker():
            self.set_status("In corso...", "#FFFFFF")
            self.output_text.delete('1.0', tk.END)
            filtered_url = action.filter_url(self.link)
            cmd = action.program.replace("{url}", filtered_url)

            # Aggiorniamo run_in_shell e autorun dai checkbox
            for a, var_shell, var_autorun in self.autorun_vars:
                if a == action:
                    a.run_in_shell = var_shell.get()
                    a.autorun = var_autorun.get()

            try:
                start_time = datetime.datetime.now()
                # subprocess con stdout e stderr pipe
                proc = subprocess.Popen(cmd, shell=action.run_in_shell,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        universal_newlines=True)
                output_lines = []
                for line in proc.stdout:
                    self._insert_output(line)
                    output_lines.append(line)
                proc.wait()
                exit_code = proc.returncode
                end_time = datetime.datetime.now()
                if exit_code == 0:
                    self.set_status("Completato!", "#A9F5A9")
                    if self.autoclose:
                        # Chiudi la tab dopo breve delay per permettere lettura stato
                        self.after(10000, self.close)
                else:
                    self.set_status(f"Terminato con codice {exit_code}", "#F5A9A9")

                # chiama la callback per salvare la cronologia
                if self.save_history_callback:
                    self.after(0, lambda: self.save_history_callback(
                        link=filtered_url,
                        start_time=start_time,
                        duration=(end_time - start_time).total_seconds(),
                        exit_code=exit_code,
                        outcome="OK" if exit_code == 0 else f"Errore {exit_code}",
                        action=action,
                        output="".join(output_lines)  # testo output
                    ))
            except Exception as e:
                self.set_status(f"Errore: {e}", "#F5A9A9")

        threading.Thread(target=worker, daemon=True).start()

    def _insert_output(self, text):
        lower = text.lower()
        tag = None
        if 'error' in lower:
            tag = 'error'
        elif 'warning' in lower:
            tag = 'warning'
        elif 'note' in lower:
            tag = 'note'

        self.output_text.insert(tk.END, text, tag)
        self.output_text.see(tk.END)

    def close(self):
        self.close_callback(self)

class ClipboardGUI(tk.Tk):
    def __init__(self, actions):
        super().__init__()
        self.title("Clipboard Link Handler")
        self.geometry("640x480")
        self.actions = actions
        self.tabs = []
        self.history = []

        # Notebook e aggiunta tab storico
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=1, fill='both')

        # self.history_tab = self.build_history_tab()
        # self.notebook.add(self.history_tab, text="Storico")
        self.history_viewer = HistoryViewer(self.notebook, self.history)
        self.notebook.add(self.history_viewer, text="Storico")

        # Frame superiore con combobox e checkbox
        frame_top = tk.Frame(self)
        frame_top.pack(fill='x', padx=10, pady=5)

        tk.Label(frame_top, text="Seleziona azione per autorun:").pack(side='left')

        self.autorun_var = tk.StringVar()
        self.labels = ["Nessuna"] + [a.label for a in self.actions]
        self.autorun_combo = ttk.Combobox(frame_top, values=self.labels, state='readonly', textvariable=self.autorun_var, width=40)
        self.autorun_combo.pack(side='left', padx=5)

        # Checkbox per autoclose
        self.autoclose_var = tk.BooleanVar(value=False)
        self.autoclose_check = tk.Checkbutton(frame_top, text="Auto-tab-close", variable=self.autoclose_var)
        self.autoclose_check.pack(side='left', padx=10)

        # Imposta valore iniziale autorun
        found_autorun = False
        for a in self.actions:
            if a.autorun:
                self.autorun_var.set(a.label)
                found_autorun = True
                break
        if not found_autorun:
            self.autorun_var.set("Nessuna")

        # Valore iniziale per autoclose
        self.autoclose_var.set(False)

        # Bind evento selezione
        self.autorun_combo.bind("<<ComboboxSelected>>", self.on_autorun_selected)
        # Bind evento cambio checkbox
        self.autoclose_var.trace_add('write', self.on_autoclose_changed)

        # Creazione della barra menu
        self.create_menu()

        # Variabili per autore e donazione
        self.authors = {
            "Gian Michele Pasinelli": "https://www.paypal.me/gianmichelepasinelli"
        }
        self.author = None

    def build_history_tab(self):
        frame = tk.Frame(self)
        columns = ("Link", "Data/Ora", "Durata", "Esito")

        self.tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='w')

        self.tree.pack(expand=True, fill='both')

        # On double-click: riapri tab chiuso associato
        self.tree.bind("<Double-1>", self.reopen_tab_from_history)
        return frame

    def save_to_history(self, link, start_time, duration, exit_code, outcome, action, output):
        record = {
            "link": link,
            "start_time": start_time,
            "duration": duration,
            "exit_code": exit_code,
            "outcome": outcome,
            "action": action,
            "output": output
        }
        self.history.append(record)

        # Aggiungi record e aggiorna vista
        if hasattr(self, 'history_viewer'):
            self.history_viewer.add_record(record)

        # # Inserisci nella treeview
        # readable_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
        # duration_str = f"{duration:.1f}s"
        # status = "OK" if exit_code == 0 else f"Errore {exit_code}"
        # self.tree.insert('', 'end', values=(link, readable_time, duration_str, status))

    def reopen_tab_from_history(self, event):
        item = self.tree.selection()[0]
        idx = self.tree.index(item)
        record = self.history[idx]

        # Ricrea un tab di ActionTab con output già pronto
        self.open_history_tab(record)

    def open_history_tab(self, record):
        tab = tk.Frame(self.notebook)
        # Mostra dettagli e output già salvato
        tk.Label(tab, text=f"Link: {record['link']}").pack(anchor='w')
        tk.Label(tab, text=f"Avviato: {record['start_time'].strftime('%Y-%m-%d %H:%M:%S')}").pack(anchor='w')
        tk.Label(tab, text=f"Durata: {record['duration']:.1f}s").pack(anchor='w')
        tk.Label(tab, text=f"Esito: {record['outcome']}").pack(anchor='w')

        output = tk.Text(tab, height=10, wrap='word')
        output.pack(expand=True, fill='both')
        output.insert('1.0', record['output'])
        output.config(state='disabled')

        # Frame per i bottoni
        btn_frame = tk.Frame(tab)
        btn_frame.pack(anchor='w', pady=4)

        copy_btn = tk.Button(btn_frame, text="Copia link", command=lambda: self.clipboard_append(record['link']))
        copy_btn.pack(side='left', padx=5)

        close_btn = tk.Button(btn_frame, text="Chiudi", command=lambda: self.close_tab(tab))
        close_btn.pack(side='left', padx=5)

        self.notebook.add(tab, text="Storico Dettaglio")
        self.notebook.select(tab)

    def on_autorun_selected(self, event):
        selected_label = self.autorun_var.get()
        # Disabilita autorun per tutte le azioni
        for a in self.actions:
            a.autorun = False

        if selected_label == "Nessuna":
            # messagebox.showinfo("Autorun disabilitato", "Nessuna azione sarà eseguita automaticamente.")
            return

        selected_actions = [a for a in self.actions if a.label == selected_label]
        if not selected_actions:
            messagebox.showerror("Errore", "Azione selezionata non trovata.")
            return

        selected_actions[0].autorun = True

        # autorun_count = sum(1 for a in self.actions if a.autorun)
        # if autorun_count > 1:
        #     messagebox.showwarning("Attenzione", "Più azioni sono impostate come autorun. Verrà eseguita la prima trovata.")
        #
        # messagebox.showinfo("Autorun impostato", f"L'azione '{selected_label}' è ora impostata per esecuzione automatica.")

    def on_autoclose_changed(self, *args):
        # selected_label = self.autorun_var.get()
        # selected_actions = [a for a in self.actions if a.label == selected_label]
        # if not selected_actions:
        #     return
        # action = selected_actions[0]
        # action.autoclose = self.autoclose_var.get()
        for action in self.actions:
            action.autoclose = self.autoclose_var.get()

    def create_menu(self):
        menubar = tk.Menu(self)

        # Menu File
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Apri Configurazione", command=self.select_config)
        filemenu.add_command(label="Mostra Configurazione", command=self.show_config_summary)
        filemenu.add_separator()
        filemenu.add_command(label="Esci", command=self.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        # # Menu Modifica (puoi aggiungere voci in futuro)
        # editmenu = tk.Menu(menubar, tearoff=0)
        # # Esempio: editmenu.add_command(label="Preferenze", command=self.open_preferences)
        # menubar.add_cascade(label="Modifica", menu=editmenu)

        # Menu Aiuto
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Guida", command=self.show_help)
        helpmenu.add_command(label="Autori e Donazioni", command=self.show_authors)
        helpmenu.add_command(label="Info", command=self.show_info)
        menubar.add_cascade(label="?", menu=helpmenu)

        self.config(menu=menubar)

    def show_config_summary(self):
        # import tkinter.scrolledtext as scrolledtext

        win = tk.Toplevel(self)
        win.title("Riepilogo configurazione")
        win.geometry("700x450")

        frame = tk.Frame(win)
        frame.pack(expand=True, fill='both', padx=10, pady=10)

        st = scrolledtext.ScrolledText(frame, wrap='none', font=("Courier New", 10))
        st.pack(side='top', expand=True, fill='both')

        xscroll = tk.Scrollbar(frame, orient='horizontal', command=st.xview)
        xscroll.pack(side='bottom', fill='x')

        # Definizione tag per colori
        st.tag_config('header', foreground='white', background='darkblue', font=('Courier New', 10, 'bold'))
        st.tag_config('label', foreground='darkgreen', font=('Courier New', 10, 'bold'))
        st.tag_config('value', foreground='black')
        st.tag_config('bool_true', foreground='green', font=('Courier New', 10, 'bold'))
        st.tag_config('bool_false', foreground='red', font=('Courier New', 10, 'italic'))

        # Intestazione tabella
        header = f"{'Azione':<6} {'Label':<30} {'Regex':<40} {'RunShell':<9} {'Autorun':<7} {'Autoclose':<9}\n"
        st.insert(tk.END, header, 'header')
        st.insert(tk.END, "-" * (6+30+40+9+7+9+5) + "\n", 'header')

        # Inserisci righe
        for i, action in enumerate(self.actions, 1):
            label = (action.label[:27] + '...') if len(action.label) > 30 else action.label
            regex = (action.pattern.pattern[:37] + '...') if len(action.pattern.pattern) > 40 else action.pattern.pattern

            line = f"{str(i):<6} {label:<30} {regex:<40} "

            # Inserisci prima parte testo
            st.insert(tk.END, line, 'value')

            # Colonna run_in_shell
            run_shell_str = str(getattr(action, 'run_in_shell', False))
            tag_shell = 'bool_true' if run_shell_str == 'True' else 'bool_false'
            st.insert(tk.END, f"{run_shell_str:<9} ", tag_shell)

            # Colonna autorun
            autorun_str = str(getattr(action, 'autorun', False))
            tag_autorun = 'bool_true' if autorun_str == 'True' else 'bool_false'
            st.insert(tk.END, f"{autorun_str:<7} ", tag_autorun)

            # Colonna autoclose
            autoclose_str = str(getattr(action, 'autoclose', False))
            tag_autoclose = 'bool_true' if autoclose_str == 'True' else 'bool_false'
            st.insert(tk.END, f"{autoclose_str:<9}\n", tag_autoclose)

            # Riga dettaglio programma e filtro (indentata)
            program_line = f"      Programma: {action.program}\n"
            filter_line = f"      Filtro: {getattr(action, 'filter_name', '')}\n"
            st.insert(tk.END, program_line, 'label')
            st.insert(tk.END, filter_line, 'label')

        st.configure(state='disabled')

        # Abilita scroll orizzontale
        st.config(xscrollcommand=xscroll.set)
        # st.config(xscrollcommand=lambda *args: st.xview(*args))
        st['wrap'] = 'none'

    def select_config(self):
        path = filedialog.askopenfilename(filetypes=[("Config files", "*.ini"), ("All files", "*.*")])
        if path:
            from config import load_config
            self.actions = load_config(path)
            messagebox.showinfo("Config caricato", f"Configurazione caricata da:\n{path}")

    def show_help(self):
        help_text = (
            "Guida all'uso del programma e configurazione del file INI:\n\n"
            "Il file di configurazione è suddiviso in più sezioni per una maggiore modularità:\n\n"

            "[DICT_REGEX]\n"
            "- Qui si definiscono le espressioni regolari con un nome identificativo.\n"
            "- Ad esempio:\n"
            "  youtube_download = https?://.*youtube\\.com/watch.*\n"
            "- Questi nomi vengono poi richiamati nella sezione [LINKS].\n\n"

            "[DICT_PROGRAMS]\n"
            "- Qui si definiscono i comandi o programmi da eseguire, associati a un nome.\n"
            "- Ad esempio:\n"
            "  program_yt = C:\\Users\\Pasinelli\\Desktop\\Archivio\\Script\\yt-dl\\yt-dlp.exe\n"
            "- Questi nomi vengono usati nella sezione [LINKS] per specificare il programma da lanciare.\n\n"

            "[FILTERS]\n"
            "- Qui si definiscono le regole di filtro per modificare i link prima dell'esecuzione.\n"
            "- Ogni filtro ha una regex di pattern e una stringa di sostituzione.\n"
            "- Ad esempio:\n"
            "  yt_pattern = (&list.*)\n"
            "  yt_replace =\n"
            "- Questo filtro rimuove tutto ciò che segue '&list' nel link.\n\n"

            "[LINKS]\n"
            "- Qui si associano le regex e i programmi definiti sopra per creare le azioni.\n"
            "- Per ogni azione si specificano:\n"
            "  * regexN = nome_regex (richiamato da [DICT_REGEX])\n"
            "  * programN = nome_programma + eventuali argomenti (richiamato da [DICT_PROGRAMS])\n"
            "  * labelN = testo del pulsante mostrato nella GUI\n"
            "  * filterN = nome filtro da applicare (opzionale)\n\n"

            "Esempio di configurazione di un'azione:\n"
            "  regex1 = youtube_download\n"
            "  program1 = program_yt -f 249 -x --paths \"C:\\Users\\Pasinelli\\Desktop\\Archivio\\Script\\yt-dl\\Download\" --audio-format mp3 --audio-quality 6 -k {url}\n"
            "  label1 = Scarica come musica mp3 249\n"
            "  filter1 = yt\n\n"

            "Note importanti:\n"
            "- Il placeholder {url} viene sostituito automaticamente con il link filtrato.\n"
            "- Puoi definire più azioni con diverse opzioni di download o programmi.\n"
            "- I filtri modificano il link prima di passarlo al programma (es. rimuovendo parametri non necessari).\n"
            "- Puoi caricare diversi file di configurazione dal menu File → Apri Configurazione.\n\n"

            "Funzionalità del programma:\n"
            "- Monitora la clipboard e rileva link compatibili con le regex configurate.\n"
            "- Mostra i pulsanti corrispondenti per eseguire i programmi configurati.\n"
            "- Permette di impostare un'esecuzione automatica per un'azione specifica.\n"
            "- Mostra l'output del programma con evidenziazione di warning, note ed errori.\n\n"

            "Per ulteriori informazioni, contatta l'autore o consulta la documentazione ufficiale."
        )
        # import tkinter.scrolledtext as scrolledtext

        help_win = tk.Toplevel(self)
        help_win.title("Guida all'uso")
        help_win.geometry("600x450")

        st = scrolledtext.ScrolledText(help_win, wrap='word', font=("Arial", 11))
        st.pack(expand=True, fill='both', padx=10, pady=10)
        st.insert(tk.END, help_text)
        st.configure(state='disabled')  # testo non modificabile

    def show_authors(self):
        # Finestra semplice con autori e link donazione cliccabili
        win = tk.Toplevel(self)
        win.title("Autori e Donazioni")
        tk.Label(win, text="Seleziona un autore per aprire la pagina di donazione:", pady=10).pack()

        for author, url in self.authors.items():
            link = tk.Label(win, text=author, fg="blue", cursor="hand2")
            link.pack()
            link.bind("<Button-1>", lambda e, url=url: webbrowser.open(url))

    def show_info(self):
        messagebox.showinfo("Info", "Clipboard Link Handler\nVersione 1.0\nCreato da Gian Michele Pasinelli\ncaludia@tiscali.it")

    def show_actions_for_link(self, link):
        matches = [a for a in self.actions if a.pattern.match(link)]
        if not matches:
            return

        # Se più match e c'è autorun, avvisa e scegli il primo
        autorun_matches = [a for a in matches if a.autorun]
        if autorun_matches:
            if len(autorun_matches) > 1:
                messagebox.showwarning("Attenzione", "Più azioni con autorun trovate, verrà eseguita la prima.")
            action = autorun_matches[0]
            # Apri tab con solo l'azione autorun e lanciala subito
            tab = ActionTab(self.notebook, link, matches, self.close_tab, save_history_callback=self.save_to_history, autoclose=action.autoclose)
            self.notebook.add(tab, text=link[:20] + " (Auto)")
            self.tabs.append(tab)
            self.notebook.select(tab)
            tab.run_action(action)
            return

        # Altrimenti mostra tutte le azioni
        tab = ActionTab(self.notebook, link, matches, self.close_tab, save_history_callback=self.save_to_history, autoclose=self.autoclose_var.get())
        self.notebook.add(tab, text=link[:20] + "...")
        self.tabs.append(tab)
        self.notebook.select(tab)

    def close_tab(self, tab):
        # Primo, controlla che il tab non sia quello storico
        if tab == self.history_viewer:
            # Ignora chiusura dello storico
            print("Tentativo di chiudere lo storico ignorato")
            return

        # Altrimenti chiudi il tab normalmente
        self.notebook.forget(tab)
        if tab in self.tabs:
            self.tabs.remove(tab)
        # idx = self.tabs.index(tab)
        # self.notebook.forget(idx)
        # self.tabs.remove(tab)


class HistoryViewer(tk.Frame):
    def __init__(self, parent, history_records=None):
        super().__init__(parent)
        self.history = history_records if history_records is not None else []

        # Divide in due pannelli con PanedWindow or Frame
        paned = ttk.Panedwindow(self, orient='horizontal')
        paned.pack(fill='both', expand=True)

        # Sinistra: Treeview
        left_frame = ttk.Frame(paned, width=400, relief='sunken')
        paned.add(left_frame, weight=1)

        columns = ("Data/Ora", "Link", "Durata")
        self.tree = ttk.Treeview(left_frame, columns=columns, show='headings', selectmode='browse')
        self.tree.pack(fill='both', expand=True, side='left')

        # Configura colonne (larghezza indicativa)
        self.tree.column("Data/Ora", width=140)
        self.tree.column("Link", width=200)
        self.tree.column("Durata", width=70, anchor='center')

        for col in columns:
            self.tree.heading(col, text=col)

        # Scrollbar verticale per Treeview
        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set)

        # Definisci tag per colore riga
        self.tree.tag_configure('success', background='#d0f0c0')  # verde chiaro
        self.tree.tag_configure('error', background='#f7c6c7')    # rosso chiaro

        # Inserisci dati
        for i, rec in enumerate(self.history):
            tag = 'success' if rec['exit_code'] == 0 else 'error'
            self.tree.insert('', 'end', iid=str(i), values=(
                rec['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                rec['link'] if len(rec['link']) < 40 else rec['link'][:37] + "...",
                f"{rec['duration']:.1f}s",
                "OK" if rec['exit_code'] == 0 else "ERRORE"
            ), tags=(tag,))

        # Destra: Text per output
        right_frame = ttk.Frame(paned, relief='sunken')
        paned.add(right_frame, weight=2)

        self.output_text = tk.Text(right_frame, wrap='word', state='disabled')
        self.output_text.pack(fill='both', expand=True)
        # Scrollbar verticale per output
        out_vsb = ttk.Scrollbar(right_frame, orient='vertical', command=self.output_text.yview)
        out_vsb.pack(side='right', fill='y')
        self.output_text.configure(yscrollcommand=out_vsb.set)

        # Bind selezione Treeview
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Selezione iniziale (prima voce se esiste)
        if self.history:
            self.tree.selection_set("0")
            self.show_output(0)

    def add_record(self, record):
        idx = len(self.history)
        self.history.append(record)

        tag = 'success' if record['exit_code'] == 0 else 'error'
        display_link = record['link'] if len(record['link']) < 40 else record['link'][:37] + "..."
        self.tree.insert('', 'end', iid=str(idx), values=(
            record['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
            display_link,
            f"{record['duration']:.1f}s"
        ), tags=(tag,))

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        self.show_output(idx)

    def show_output(self, idx):
        self.output_text.config(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, self.history[idx]['output'])
        self.output_text.config(state='disabled')

