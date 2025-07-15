import configparser
import re

class LinkAction:
    def __init__(self, pattern, program, label, filter_name=None, filters=None, run_in_shell=False, autorun=False):
        self.pattern = re.compile(pattern)
        self.program = program
        self.label = label
        self.filter_name = filter_name
        self.filters = filters or {}
        self.run_in_shell = run_in_shell
        self.autorun = autorun

    def filter_url(self, url):
        if self.filter_name and self.filter_name in self.filters:
            pattern, replace = self.filters[self.filter_name]
            return pattern.sub(replace, url)
        return url


def load_config(config_path='config.ini'):
    config = configparser.ConfigParser()
    config.read(config_path)

    # Carica le label da [DICT_REGEX]
    dict_regexs_labels = {}
    if 'DICT_REGEX' in config:
        dict_regexs_labels = dict(config['DICT_REGEX'])

    # Carica le label da [DICT_PROGRAMS]
    dict_programs_labels = {}
    if 'DICT_PROGRAMS' in config:
        dict_programs_labels = dict(config['DICT_PROGRAMS'])

    # Carica i filtri da [FILTERS]
    filters = {}
    if 'FILTERS' in config:
        for key in config['FILTERS']:
            if key.endswith('_pattern'):
                filter_name = key[:-8]  # togli '_pattern'
                pattern = config['FILTERS'][key]
                replace = config['FILTERS'].get(f'{filter_name}_replace', '')
                filters[filter_name] = (re.compile(pattern), replace)

    actions = []
    for key in config['LINKS']:
        if key.startswith('regex'):
            num = key.replace('regex', '')
            pattern_raw = config['LINKS'][key]
            pattern = substitute_label(pattern_raw, dict_regexs_labels)

            # Leggi programN e sostituisci eventuali label
            prog_raw = config['LINKS'].get(f'program{num}', '')
            program = substitute_label(prog_raw, dict_programs_labels)

            # Leggi labelN (testo pulsante), fallback a nome programma o 'Azione'
            label_raw = config['LINKS'].get(f'label{num}', '')
            label = label_raw if label_raw else (program.split()[0] if program else 'Azione')

            filter_name = config['LINKS'].get(f'filter{num}', None)
            run_in_shell = config['LINKS'].getboolean(f'run_in_shell{num}', fallback=False)
            autorun = config['LINKS'].getboolean(f'autorun{num}', fallback=False)

            actions.append(LinkAction(pattern, program, label, filter_name, filters, run_in_shell, autorun))

    return actions

def substitute_label(value, labels):
    """
    Se value inizia con una label definita in labels, sostituisci la parte label_XXX
    con il valore corrispondente, mantenendo il resto della stringa.
    Esempio:
        value = "label_yt {url}"
        labels['label_yt'] = "C:\\path\\yt-dlp.exe"
        ritorna "C:\\path\\yt-dlp.exe {url}"
    """
    for label_key, label_val in labels.items():
        if value.startswith(label_key):
            return value.replace(label_key, label_val, 1)
    return value
