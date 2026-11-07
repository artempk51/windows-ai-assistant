import tkinter as tk
import keyboard
import os
import webbrowser
import time
import threading
import datetime
import winsound
import subprocess
import urllib.request
import urllib.parse
import json
import mss
import google.generativeai as genai

# --- НАСТРОЙКА ИИ GOOGLE ---
API_KEY = "ТВОЙ_КЛЮЧ_ЗДЕСЬ"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-3.8-flash')

# --- СЛОВАРЬ ПЕРЕВОДА НАЗВАНИЙ ---
RU_TO_EN = {
    "стим": "steam",
    "дискорд": "discord",
    "телеграм": "telegram",
    "телега": "telegram",
    "хром": "chrome",
    "браузер": "chrome",
    "спотифай": "spotify",
    "код": "visual studio code",
    "вс код": "visual studio code",
    "обс": "obs",
    "эпик": "epic games",
    "роблокс": "roblox",
    "майнкрафт": "minecraft",
    "торрент": "torrent"
}

def index_apps():
    apps = {}
    paths = [
        os.path.join(os.environ.get('PROGRAMDATA', ''), r'Microsoft\Windows\Start Menu\Programs'),
        os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs'),
        os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop'),
        os.path.join(os.environ.get('PUBLIC', ''), 'Desktop')
    ]
    for base_path in paths:
        if os.path.exists(base_path):
            for root_dir, _, files in os.walk(base_path):
                for file in files:
                    if file.endswith(('.lnk', '.url')):
                        app_name = os.path.splitext(file)[0].lower()
                        apps[app_name] = os.path.join(root_dir, file)
    return apps

INSTALLED_APPS = index_apps()

# --- ВСПЛЫВАЮЩЕЕ ОКНО + АНГЛИЙСКИЙ ГОЛОС WINDOWS ---
def show_toast(text, duration=2500):
    """Показывает красивое мини-уведомление на экране"""
    toast = tk.Toplevel(root)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.configure(bg="#007ACC")

    lbl = tk.Label(toast, text=f"🤖 {text}", font=("Segoe UI", 14), bg="#1E1E1E", fg="white", padx=20, pady=10, wraplength=500)
    lbl.pack(padx=2, pady=2)

    toast.update_idletasks()
    w = toast.winfo_width()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 3) + 80
    toast.geometry(f"+{x}+{y}")

    toast.after(duration, toast.destroy)

def speak(ru_text, en_voice_text, duration=2500):
    """Показывает русский текст на экране и произносит английскую фразу голосом Windows"""
    root.after(0, lambda: show_toast(ru_text, duration))

    def run_speak():
        try:
            safe_text = en_voice_text.replace("'", "").replace('"', '')
            ps_script = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate = 1; $s.Speak('{safe_text}')"
            subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script], creationflags=0x08000000)
        except Exception as e:
            print("Ошибка голоса:", e)

    threading.Thread(target=run_speak, daemon=True).start()

# --- НОВЫЕ ФУНКЦИИ: СКРИНШОТ И ПЕРЕВОДЧИК ---
def take_screenshot():
    """Делает скриншот экрана и сохраняет в папку Скрины_ИИ на Рабочем столе"""
    desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
    folder = os.path.join(desktop, 'Скрины_ИИ')
    os.makedirs(folder, exist_ok=True)
    
    now = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    filepath = os.path.join(folder, f"Скрин_{now}.png")
    
    with mss.mss() as sct:
        sct.shot(output=filepath)

def quick_translate(text):
    """Определяет язык, переводит текст без браузера и копирует в буфер обмена"""
    has_cyrillic = any('а' <= char <= 'я' or char == 'ё' for char in text.lower())
    target_lang = 'en' if has_cyrillic else 'ru'
    
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            translated = "".join([part[0] for part in data[0]])
            
            # Копируем готовый перевод сразу в буфер обмена!
            root.clipboard_clear()
            root.clipboard_append(translated)
            root.update()
            
            speak(f"Перевод (скопирован!):\n{translated}", "Translation copied to clipboard", duration=4500)
    except Exception as e:
        print("Ошибка перевода:", e)
        speak("Не удалось перевести текст", "Translation failed")

def ask_google_ai(user_text):
    prompt = f"""
    Ты системный помощник Windows. Пользователь написал: "{user_text}".
    Переведи его желание в ОДНУ точную команду из списка ниже:
    - темная тема / светлая тема / настройки / экран
    - калькулятор / блокнот / диспетчер задач / очистить корзину / заблокировать пк
    - громче / тише / мут / пауза
    - ютуб / поиск [запрос]
    - таймер [число] [текст]
    - запиши [текст]
    - скрин (если просит сфоткать экран, сделать скриншот)
    - запись (если просит начать или остановить запись видео экрана)
    - переведи [текст] (если просит перевести фразу)
    - unknown (если вообще непонятно)
    
    Ответь ТОЛЬКО самой командой, без кавычек и лишних слов!
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip().lower().replace("ё", "е")
    except Exception:
        return "unknown"

def release_all_modifiers():
    for key in ['ctrl', 'alt', 'shift']:
        try:
            keyboard.release(key)
        except Exception:
            pass

def paste_text(text):
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()
    time.sleep(0.15)
    release_all_modifiers()
    keyboard.send('shift+insert')
    time.sleep(0.25)

def launch_app(query):
    search_term = RU_TO_EN.get(query, query)
    if search_term == "telegram":
        os.system("start tg://")
        return True
    if search_term in INSTALLED_APPS:
        os.startfile(INSTALLED_APPS[search_term])
        return True
    for app_name, app_path in INSTALLED_APPS.items():
        if search_term in app_name:
            if "uninstall" not in app_name and "удалить" not in app_name:
                os.startfile(app_path)
                return True
    return False

def send_tg_message(contact, message):
    release_all_modifiers()
    os.system("start tg://")
    time.sleep(2.0)
    keyboard.send('esc')
    time.sleep(0.2)
    keyboard.send('esc')
    time.sleep(0.2)
    keyboard.send('ctrl+f')
    time.sleep(0.4)
    paste_text(contact)
    time.sleep(1.0)
    keyboard.send('enter')
    time.sleep(0.5)
    paste_text(message)
    time.sleep(0.2)
    keyboard.send('enter')

def save_note(text):
    desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
    notes_file = os.path.join(desktop, 'Заметки_ИИ.txt')
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    with open(notes_file, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {text}\n")

def run_timer(minutes, message):
    time.sleep(minutes * 60)
    speak(f"Время вышло: {message}", "Time is up, boss! Check your reminder.")
    
    popup = tk.Toplevel(root)
    popup.title("Напоминание!")
    popup.geometry("400x200")
    popup.attributes("-topmost", True)
    popup.configure(bg="#1E1E1E")
    
    x = (popup.winfo_screenwidth() // 2) - 200
    y = (popup.winfo_screenheight() // 2) - 100
    popup.geometry(f"+{x}+{y}")
    
    lbl = tk.Label(popup, text=f"⏰ ВРЕМЯ ВЫШЛО!\n\n{message}", font=("Segoe UI", 16), bg="#1E1E1E", fg="white", wraplength=380)
    lbl.pack(expand=True, fill="both", pady=20)
    btn = tk.Button(popup, text="Понял", font=("Segoe UI", 14), bg="#007ACC", fg="white", relief="flat", command=popup.destroy)
    btn.pack(pady=10)

def hide_window(event=None):
    entry.delete(0, tk.END)
    root.withdraw()

def execute_action(command, raw_text=""):
    if command in ["выход", "стоп", "закройся"]:
        speak("Выключаюсь...", "Shutting down. Goodbye!")
        time.sleep(1.5)
        root.destroy()
        os._exit(0)

    # --- СКРИНШОТ ---
    elif command in ["скрин", "скриншот", "сфоткай"]:
        # Ждем 0.3 секунды, чтобы окно помощника полностью исчезло с кадра
        time.sleep(0.3)
        take_screenshot()
        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        speak("Скриншот сохранен в папку 'Скрины_ИИ'!", "Screenshot saved")
        return True

    # --- ЗАПИСЬ ВИДЕО ЭКРАНА ---
    elif command in ["запись", "видео", "стоп запись"]:
        # Вызывает встроенную запись экрана Windows (Win + Alt + R)
        keyboard.send("win+alt+r")
        speak("Переключаю запись экрана (Win+Alt+R)", "Toggling screen recording")
        return True

    # --- БЫСТРЫЙ ПЕРЕВОДЧИК В ОКНЕ ---
    elif command.startswith("переведи ") or command.startswith("перевод "):
        text_to_translate = raw_text.split(" ", 1)[1]
        threading.Thread(target=quick_translate, args=(text_to_translate,), daemon=True).start()
        return True

    elif command.startswith("запиши ") or command.startswith("заметка "):
        note_text = raw_text.split(" ", 1)[1]
        save_note(note_text)
        speak("Заметка сохранена на рабочий стол", "Note saved to your desktop")
        return True

    elif command.startswith("таймер "):
        parts = raw_text.split(" ", 2)
        if len(parts) >= 2:
            try:
                minutes = float(parts[1].replace(",", "."))
                msg = parts[2] if len(parts) > 2 else "Сработал таймер"
                threading.Thread(target=run_timer, args=(minutes, msg), daemon=True).start()
                speak(f"Таймер запущен на {parts[1]} мин.", "Timer started")
            except ValueError:
                speak("Укажи число минут для таймера", "Please specify the minutes for the timer")
        return True

    elif command.startswith("тг "):
        parts = raw_text.split(" ", 2)
        if len(parts) >= 3:
            speak(f"Отправляю сообщение для {parts[1]}", "Sending Telegram message")
            send_tg_message(parts[1], parts[2])
        return True

    elif command == "темная тема":
        speak("Включаю тёмную тему", "Switching to dark mode")
        os.system("reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize /v AppsUseLightTheme /t REG_DWORD /d 0 /f")
        os.system("reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize /v SystemUsesLightTheme /t REG_DWORD /d 0 /f")
    elif command == "светлая тема":
        speak("Включаю светлую тему", "Switching to light mode")
        os.system("reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize /v AppsUseLightTheme /t REG_DWORD /d 1 /f")
        os.system("reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize /v SystemUsesLightTheme /t REG_DWORD /d 1 /f")
    elif command == "настройки":
        speak("Открываю настройки", "Opening Windows settings")
        os.system("start ms-settings:")
    elif command == "экран":
        speak("Открываю параметры экрана", "Opening display settings")
        os.system("start ms-settings:display")

    elif command == "калькулятор":
        speak("Открываю калькулятор", "Opening calculator")
        os.system("start calc")
    elif command == "блокнот":
        speak("Открываю блокнот", "Opening notepad")
        os.system("start notepad")
    elif command == "диспетчер задач":
        speak("Открываю диспетчер задач", "Opening task manager")
        os.system("start taskmgr")
    elif command == "проводник":
        speak("Открываю проводник", "Opening file explorer")
        os.system("start explorer")

    elif command in ["музыка стоп", "пауза"]:
        speak("Пауза", "Media paused")
        keyboard.send("play/pause media")
    elif command in ["выключить звук", "мут"]:
        speak("Звук выключен", "Audio muted")
        keyboard.send("volume mute")
    elif command == "громче":
        speak("Делаю громче", "Volume up")
        for _ in range(5):
            keyboard.send("volume up")
    elif command == "тише":
        speak("Делаю тише", "Volume down")
        for _ in range(5):
            keyboard.send("volume down")

    elif command == "ютуб":
        speak("Открываю Ютуб", "Opening YouTube")
        webbrowser.open("https://www.youtube.com")
    elif command == "переводчик":
        speak("Открываю переводчик", "Opening Google Translate")
        webbrowser.open("https://translate.google.com")
    elif command.startswith("поиск "):
        speak("Ищу в Google", "Searching Google")
        search_query = command.replace("поиск ", "")
        webbrowser.open(f"https://www.google.com/search?q={search_query}")

    elif command == "очистить корзину":
        speak("Очищаю корзину", "Emptying recycle bin")
        os.system("powershell.exe Clear-RecycleBin -Force")
    elif command == "заблокировать пк":
        speak("Блокирую компьютер", "Locking workstation")
        os.system("rundll32.exe user32.dll,LockWorkStation")
    else:
        return False
    return True

def process_command(event):
    raw_text = entry.get().strip()
    command = raw_text.lower().replace("ё", "е")
    
    if not command:
        hide_window()
        return

    hide_window()
    time.sleep(0.5)
    release_all_modifiers()

    if execute_action(command, raw_text):
        return

    app_query = command.replace("открой ", "").replace("запусти ", "").strip()
    if launch_app(app_query):
        en_name = RU_TO_EN.get(app_query, "application")
        speak(f"Запускаю {app_query}", f"Launching {en_name}")
        return

    speak("Секунду, думаю...", "Thinking...")
    ai_command = ask_google_ai(raw_text)
    
    if not execute_action(ai_command, raw_text):
        speak("Я не понял команду", "Sorry, command not recognized")

def show_window():
    release_all_modifiers()
    root.deiconify()
    root.attributes("-topmost", True)
    entry.focus_set()

# --- Интерфейс ---
root = tk.Tk()
root.title("ИИ Помощник")

window_width = 550
window_height = 60
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width // 2) - (window_width // 2)
y = (screen_height // 3)

root.geometry(f"{window_width}x{window_height}+{x}+{y}")
root.overrideredirect(True) 

border_frame = tk.Frame(root, bg="#007ACC", bd=2)
border_frame.pack(expand=True, fill="both")

entry = tk.Entry(
    border_frame, 
    font=("Segoe UI", 18), 
    justify="center",
    bg="#1E1E1E",
    fg="#FFFFFF",
    insertbackground="white",
    relief="flat"
)
entry.pack(expand=True, fill="both", padx=2, pady=2)

entry.bind('<Return>', process_command)
entry.bind('<Escape>', hide_window)

root.withdraw() 
keyboard.add_hotkey('ctrl+alt+space', show_window)

root.mainloop()