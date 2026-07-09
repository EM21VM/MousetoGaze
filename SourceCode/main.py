import json
import pyautogui
from pynput import keyboard
from hotkey import Hotkey
from eyetracking import Eyetracking
from threading import Thread
import argparse
import os
import sys
import time

debug = True
current = set()
running = True
eyetracker = None
screenWidth, screenHeight = pyautogui.size()
pyautogui.FAILSAFE = False  
def getBasePath():
    """Ermittelt den Pfad, in dem die .exe oder das .py-Skript sich befindet

    Returns:
        str: Der Basis-Pfad
    """
    if getattr(sys, 'frozen', False):
        # Wenn das Skript als .exe ausgeführt wird
        return os.path.dirname(sys.executable)
    else:
        # Wenn das Skript als .py ausgeführt wird
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path

BaseDir = getBasePath()
ConfigFile = os.path.join(BaseDir, "config.json")
defaultConfig = {
    "cameraIndex": 0,
    "library": "eyetrax",
    "forceRecalibration": False,
    "hotkeys:" : [
        {
            "name": "Eyetracking Hotkey",
            "keys": ["Key.ctrl_l", "g"],
            "function": "moveMouseToGaze",
            "args": [["time", 30]],
            "protected": True
        },
        {
            "name": "Quit Program",
            "keys": ["esc", "Key.ctrl_l"],
            "function": "quitProgramm",
            "args": [],
            "protected": True
        },
    ]
}
# Logik für das Laden der Konfiguration aus der config.json bzw. das Erstellen einer Standardkonfiguration, falls die Datei nicht existiert.
def ensureConfig():
    """Erstellt eine Standardkonfiguration, falls eine config.json nicht existiert, und lädt die Konfiguration in den Speicher.
    """
    if not os.path.exists(ConfigFile):
        print("No config file found. Creating default config.json...")
        try:
            with open(ConfigFile, 'w') as f:
                json.dump(defaultConfig, f, indent=4)
        except Exception as e:
            print(f"Error occurred while creating default config: {e}")
    else:
        
        for trys in range(5):
            try:
                with open(ConfigFile, 'r') as f:
                    config = json.load(f)
                return config
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from config file (attempt {trys+1}/5): {e}. Retrying...")
                time.sleep(0.2)
            except Exception as e:
                print(f"Error occurred while loading config (attempt {trys+1}/5): {e}. Retrying...")
                time.sleep(0.2)
        
        print("Config file found. Loading configuration...")
    with open(ConfigFile, 'r') as f:
        config = json.load(f)
    return config

def updateHotkeys(identifier, newKeys):
    """Aktualisiert die Tastenbelegung eines Hotkeys in der Konfiguration und im laufenden Programm.

    Args:
        identifier (str or int): Der Name oder der Index des zu aktualisierenden Hotkeys.
        newKeys (list): Die neuen Tasten, die für den Hotkey verwendet werden sollen.
    """
    config = ensureConfig()
    hotkeys = config.get("hotkeys:", [])
    
    index = getHotkeyIndex(hotkeys, identifier)
    
    if index == -1:
        print(f"Error: No hotkey found with identifier '{identifier}'.")
        return
    
    hotkeys[index]["keys"] = newKeys
    with open(ConfigFile, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Hotkey '{hotkeys[index]['name']}' updated with new keys: {newKeys}")
    

def moveMouseToGaze(time: int) -> None:
    """Bewegt die Maus zu den Koordinaten, auf die der Benutzer schaut.

    Args:
        time (int): Die Dauer in Sekunden, für die das Eyetracking durchgeführt werden soll.
    """
    if not eyetracker:
        print("Error: Eyetracker not initialized. Cannot move mouse to gaze coordinates.")
        return
    print("Starting eyetracking to move mouse to gaze coordinates...")
    x_gaze, y_gaze = eyetracker.startTracking(time=time)
    debug and print(f"Moving mouse to gaze coordinates: {x_gaze}, {y_gaze}")
    pyautogui.moveTo(x_gaze, y_gaze, duration=0.5)
    return

def quitProgramm():
    """Beendet das Programm, indem die globale Variable 'running' auf False gesetzt wird, was die Hauptschleife im Worker-Thread zum Beenden bringt."""
    global running
    print("Quitting program...")
    running = False

def parseKeys(keys):
    """Parst die Tasten aus der Konfiguration und gibt sie in einem Format zurück, das von der Hotkey-Klasse verwendet werden kann, also in Pynput-Key-Objekte.

    Args:
        keys (list): Die Liste der Tasten aus der Konfiguration.
    Returns:
        set: Ein Set der Tasten, das von der Hotkey-Klasse verwendet werden kann.
    """
    parsedKeys = []
    for k in keys:
        if hasattr(keyboard.Key, k):
            parsedKeys.append(getattr(keyboard.Key, k))
        else:
            parsedKeys.append(k)
    return parsedKeys

# --- Setup und Initialisierung der Hotkeys ---
def setupHotkeys(config):
    """Richtet die Hotkeys basierend auf der geladenen Konfiguration ein.

    Args:
        config (dict): Die geladene Konfiguration, die die Hotkey-Definitionen enthält.
    """
    Hotkey.clearRegistry()  # Alle bestehenden Hotkeys löschen, um Duplikate zu vermeiden
    for hk in config.get("hotkeys:", []):
        name = hk.get("name")
        keys = parseKeys(hk.get("keys", []))
        functionName = hk.get("function")
        function = getFunctionByName(functionName)
        args = hk.get("args", [])
        protected = hk.get("protected", False)
        if function:
            Hotkey(keys, function, args, protected, name)
            debug and print(f"Registered hotkey: {name} with keys: {keys} for function: {functionName}")
        else: 
            print(f"Error: Function '{functionName}' not found for hotkey '{name}'. Skipping this hotkey.")
    debug and print(f"Total registered: {len(Hotkey.getRegistry())} hotkeys.")
    
def getHotkeyIndex(hotkeyList, identifier):
    """Gibt den Index eines Hotkeys in der Liste der registrierten Hotkeys zurück, basierend auf einem Identifier, also den Namen des Hotkeys.

    Args:
        hotkeyList (list): Die Liste der registrierten Hotkeys (Dictionaries oder Hotkey-Objekte).
        identifier (str): Der Identifier, der entweder die Ziffer (Index+1) oder der Name des Hotkeys sein kann.
    """
    try: 
        index = int(identifier) - 1
        if 0 <= index < len(hotkeyList):
            return index
    except ValueError:
        pass # Identifier ist keine Zahl, weiter mit der Suche nach Name
        
    for i, hk in enumerate(hotkeyList):
        if isinstance(hk, dict):
            if hk.get("name") == identifier:
                return i
        else:
            if getattr(hk, "name", None) == identifier:
                return i
                
    return -1

def listHotkeys():
    """Gibt eine Liste aller registrierten Hotkeys mit ihren Namen und Tasten aus, um dem Benutzer eine Übersicht über die verfügbaren Hotkeys zu geben."""
    config = ensureConfig()
    hotkeys = config.get("hotkeys:", [])
    if not hotkeys:
        print("No hotkeys registered.")
        return
    print("Currently registered hotkeys:")
    print("-" * 50)
    for i, hk in enumerate(hotkeys):
        prot = "[PROTECTED]" if hk.get("protected") else ""
        print(f" {i+1}. {hk['name']}")
        print(f"    Keys:   {hk['keys']}")
        print(f"    Function: {hk['function']} {prot}")
    print("-" * 50)
    
def addHotkey(name, keys, functionName, args, protected=False):
    """Fügt einen neuen  Hotkey hinzu, indem der Benutzer die erforderlichen Informationen wie Name, Tasten, Funktion und Argumente eingibt. Diese Informationen werden dann in der Konfiguration gespeichert und der Hotkey wird im laufenden Programm registriert."""
    if functionName not in AvailabileFunctions:
        print(f"Error: Function '{functionName}' is not available. Use the 'listFunctions' command to see available functions.")
        return
    
    config = ensureConfig()
    newHotkey = {
        "name": name,
        "keys": keys,
        "function": functionName,
        "args": args,
        "protected": protected
    }
    config.setdefault("hotkeys:", []).append(newHotkey)
    
    with open(ConfigFile, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Hotkey '{name}' added successfully with keys: {keys} for function: {functionName}.")

def deleteHotkey(identifier):
    """Löscht einen bestehenden Hotkey basierend auf einem Identifier, also den Namen oder den Index des Hotkeys. Geschützte Hotkeys können nicht gelöscht werden."""
    config = ensureConfig()
    hotkeys = config.get("hotkeys:", [])
    index = getHotkeyIndex(hotkeys, identifier)
    if index == -1:
        print(f"Error: No hotkey found with identifier '{identifier}'.")
        return
    if hotkeys[index].get("protected", False):
        print(f"Error: Hotkey '{hotkeys[index]['name']}' is protected and cannot be deleted.")
        return
    deletedHotkey = hotkeys.pop(index)
    with open(ConfigFile, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Hotkey '{deletedHotkey['name']}' deleted successfully.")
    
# --- Mapping von Funktionsnamen zu tatsächlichen Funktionen ---
AvailabileFunctions = {
    "moveMouseToGaze": moveMouseToGaze,
    "pyautogui.moveTo": pyautogui.moveTo,
    "pyautogui.click": pyautogui.click,
    "quitProgramm": quitProgramm
}

def getFunctionByName(functionName):
    """Gibt die Funktion zurück, die einem Funktionsnamen entspricht.

    Args:
        functionName (str): Der Name der Funktion, die zurückgegeben werden soll.
    Returns:
        callable: Die Funktion, die dem übergebenen Namen entspricht.
    """
    return AvailabileFunctions.get(functionName)

def listFunctions():
    """Gibt eine Liste aller verfügbaren Funktionen mit ihren Namen aus, um dem Benutzer eine Übersicht über die Funktionen zu geben, die in der Konfiguration verwendet werden können."""
    print("Available functions:")
    print("-" * 50)
    for name in AvailabileFunctions.keys():
        print(f" - {name}")
    print("-" * 50)
    
    
def listCameras():
    """List all available cameras."""
    from eyetracking import Eyetracking 
    print("Scanning for available cameras...")
    cameras = Eyetracking.getAvailableCameras()
    
    config = ensureConfig()
    active_cam = config.get("camera_index", 0)
    
    print("\nAvailable cameras:")
    print("-" * 30)
    for cam_id in cameras:
        status = "[ACTIVE]" if cam_id == active_cam else ""
        print(f" Camera ID: {cam_id} {status}")
    print("-" * 30)
    print("Use '--set-camera <ID>', to switch the camera.")
    
def setCamera(ID):
    """Set the active camera by updating the configuration and force recalibrating the eyetracker on the next start.

    Args:
        camera_id (int): The ID of the camera to set as active.
    """
    try: 
        camera_id = int(ID)
    except ValueError:
        print(f"Error: Invalid camera ID '{camera_id}'. Please provide a valid integer.")
        return 
    config = ensureConfig()
    config["camera_index"] = camera_id
    config["forceRecalibration"] = True
    with open(ConfigFile, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Camera set to ID {camera_id}. The change will take effect after restarting the program.")

def setLibrary(lib_name):
    """Ändert die aktive Eyetracking-Bibliothek in der Konfiguration."""
    lib_name = lib_name.lower()
    valid_libs = ["eyetrax", "gazetracking", "l2csnet"]
    
    if lib_name not in valid_libs:
        print(f"Error: Invalid library '{lib_name}'. Available options are: {', '.join(valid_libs)}")
        return
        
    config = ensureConfig()
    config["library"] = lib_name
    config["forceRecalibration"] = True 
    
    with open(ConfigFile, "w") as f:
        json.dump(config, f, indent=4)
        
    print(f"Library successfully set to '{lib_name}'.")
    print("The change will take effect after restarting the program.")
    
def get_key_value(key):
    """Wandelt unsichtbare Ctrl-Zeichen (Steuerzeichen) wieder in normale Buchstaben um."""
    if hasattr(key, 'char') and key.char is not None:
        # Steuerzeichen haben einen ASCII-Wert unter 32
        if ord(key.char) < 32:
            return chr(ord(key.char) + 96) # Wandelt z.B. \x07 zurück in 'g'
        return key.char
    return key

def onPress(key):
    key_val = get_key_value(key)
    current.add(key_val)
    debug and print(f"Current keys pressed: {key_val}")
    for hotkey in Hotkey.getRegistry():
        if hotkey.isPressed(current):
            print(f"Hotkey matched: {hotkey.keys}. Executing associated function.")
            thread = Thread(target=hotkey.execute)
            thread.start()

def onRelease(key):
    key_val = get_key_value(key)
    current.discard(key_val)
    debug and print(f"Key released: {key_val}")
    
# --- Alle Menüs und Funktionen, die für die Durchführung der Tests notwendig sind ---  
def selectLibraryMenu():
    """Submenu for selecting the eyetracking library."""
    while True:
        print("\n" + "-" * 40)
        print("Choose the eyetracking library to test:")
        print("-" * 40)
        print("[1] EyeTrax")
        print("[2] L2CS-Net ")
        print("[3] GazeTracking")
        print("[4] Back to Main Menu")
        print("-" * 40)
        
        choice = input("Please choose (1-4): ").strip()
        if choice == "1": return "eyetrax"
        elif choice == "2": return "l2csnet"
        elif choice == "3": return "gazetracking"
        elif choice == "4": return None
        else: print("Invalid input. Please enter a number between 1 and 4.")

def selectTestModeMenu():
    """Submenu for selecting the interactive test mode."""
    while True:
        print("\n" + "-" * 55)
        print("Choose the interactive test mode:")
        print("-" * 55)
        print("[1] Static (Baseline - 3 random points)")
        print("[2] Edges")
        print("[3] Random Fullscreen (3 unpredictable points anywhere on the screen)")
        print("[4] Dynamic ")
        print("[5] ALL Interactive Tests")
        print("[6] Back to Main Menu")
        print("-" * 55)
        
        choice = input("Please choose (1-6): ").strip()
        if choice == "1": return "static"
        elif choice == "2": return "edges"
        elif choice == "3": return "random_fullscreen"
        elif choice == "4": return "dynamic"
        elif choice == "5": return "all"
        elif choice == "6": return None
        else: print("Invalid input. Please enter a number between 1 and 6.")

def TestMenu():
    """Opens the main test menu, where the user can choose to run automated logic tests, interactive precision tests for specific libraries and modes, or a full run of all tests. The menu will keep running until the user chooses to exit."""
    import tests 
    while True:
        print("\n" + "=" * 45)
        print(" MAIN TEST MENU")
        print("=" * 45)
        print("[1] Automated Logic Tests")
        print("[2] Interactive Precision Tests")
        print("[3] Full Run (Logic + ALL Precision Tests)")
        print("[4] Exit Test Menu")
        print("=" * 45)
        
        choice = input("Please choose an option (1-4): ").strip()
        
        if choice == "1":
            tests.runLogicTests()
            input("\nPress Enter to return to the main menu...")
            
        elif choice == "2":
            library = selectLibraryMenu()
            if not library: 
                continue
            mode = selectTestModeMenu()
            if not mode: 
                continue
                
            if mode == "all":
                tester_name = input("\nPlease enter the tester's name for all runs: ")
                for m in ["static", "edges", "random_fullscreen", "dynamic"]:
                    tests.runPrecisionTest(test_mode=m, library=library, tester_name=tester_name)
            else:
                tests.runPrecisionTest(test_mode=mode, library=library)
                
            input("\nPress Enter to return to the main menu...")
            
        elif choice == "3":
            library = selectLibraryMenu()
            if not library: 
                continue
                
            print("\n" + "*" * 45)
            print(" TEIL 1: LOGIC-TESTS")
            print("*" * 45)
            tests.runLogicTests()
            
            print("\n" + "*" * 45)
            print(" TEIL 2: ALL INTERACTIVE PRECISION TESTS")
            print("*" * 45)
            
            tester_name = input("\nPlease enter the tester's name: ")
            
            for m in ["static", "edges", "random_fullscreen", "dynamic"]:
                tests.runPrecisionTest(test_mode=m, library=library, tester_name=tester_name)
            
            input("\nFinished all tests. Press Enter to return to the main menu...")
            
        elif choice == "4":
            print("Exiting test menu...")
            break
            
        else:
            print("Error: Invalid choice. Please enter a number between 1 and 4.")


# --- Arbeiterlogik ---
def runWorker():
    global running, eyetracker
    print("Starting worker thread...")
    
    debug and print(f"Screensize: {screenWidth}x{screenHeight}")
    debug and print(f"Initial mouse position: {pyautogui.position()}")
    debug and print("Loading eyetracking module...")
    
    # Initial Config load
    config = ensureConfig()
    camIndex = config.get("camera_index", 0)
    selected_library = config.get("library", "eyetrax")
    
    eyetracker = Eyetracking(
        library=selected_library, 
        Savespace="", 
        cameraIndex=camIndex,
        screenWidth=screenWidth,
        screenHeight=screenHeight
    )
    
    forceRecal = config.get("forceRecalibration", False)
    eyetracker.calibrate(forceRecal=forceRecal)
    
    if forceRecal:
        config["forceRecalibration"] = False
        with open(ConfigFile, "w") as f:
            json.dump(config, f, indent=4)
        print("Force recalibration completed. Flag reset in config.")
    # Setup Hotkeys based on config
    setupHotkeys(config)
    lastModified = os.path.getmtime(ConfigFile) if os.path.exists(ConfigFile) else 0
    # Listener für die Hotkeys starten
    listener = keyboard.Listener(on_press=onPress, on_release=onRelease)
    listener.start()
    print ("Listening for keyboard events. The program will keep running until the 'Quit Program' hotkey is pressed or the process is terminated.")
    
    # Überwachung der Konfigurationsdatei auf Änderungen, um Hotkeys dynamisch zu aktualisieren
    while running:
        time.sleep(1)
        if os.path.exists(ConfigFile):
            currentModified = os.path.getmtime(ConfigFile)
            if currentModified > lastModified:
                print("Config file modified. Reloading...")
                try: 
                    time.sleep(0.2)
                    config = ensureConfig()
                    setupHotkeys(config)
                    lastModified = currentModified
                except Exception as e:
                    print(f"Error occurred while reloading config: {e}. Trying again...")

    listener.stop()
    print("Worker thread exiting...")
    
# --- Hauptprogramm ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eyetracking Hotkey Controller", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--list-functions", action="store_true", help="List all available functions that can be used in the configuration.")
    parser.add_argument("--list-hotkeys", action="store_true", help="List all currently registered hotkeys with their names and keys.")
    parser.add_argument("--add", nargs=5, metavar=('Name', 'Keys', 'Function', 'Args', 'Protected'), help="Add a new hotkey. Usage: --add <Name> <Keys> <Function> <Args> <Protected>\nExample: --add 'New Hotkey' 'h' 'moveMouseToGaze' '[\"time\", 30]' False")
    parser.add_argument("--delete", metavar='Identifier', help="Delete an existing hotkey by name or index. Usage: --delete <HotkeyNameOrIndex>\nExample: --delete 'Eyetracking Hotkey' or --delete 1")
    parser.add_argument("--update", nargs= "+", help="Update the keys for a specific hotkey. Usage: --update <HotkeyName> <NewKey1> <NewKey2> ...")
    parser.add_argument("--list-cameras", action="store_true", help="List all available cameras connected to the system.")
    parser.add_argument("--set-camera", metavar='CameraID', help="Set the active camera by its ID and forces a recalibration. Usage: --set-camera <CameraID>\nExample: --set-camera 0")
    parser.add_argument("--set-library", choices=['eyetrax', 'gazetracking', 'l2csnet'], help="Set the active eyetracking library (eyetrax, gazetracking, l2csnet).")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for more verbose output.")
    parser.add_argument("--test", action="store_true", help="Open the test menu to run logic and precision tests for the functions.")
    
    args = parser.parse_args()
    
    if args.debug:
        debug = True
        print("Debug mode enabled.")
    
    if args.list_functions:
        listFunctions()
        
    elif args.list_hotkeys:
        listHotkeys()
        
    elif args.add:
        name = args.add[0]
        keys = json.loads(args.add[1]) if args.add[1].startswith('[') else [args.add[1]]
        functionName = args.add[2]
        argsList = json.loads(args.add[3]) if args.add[3].startswith('[') else []
        protected = args.add[4].lower() == 'true'
        addHotkey(name, keys, functionName, argsList, protected)
        
    elif args.delete:
        deleteHotkey(args.delete)
        
    elif args.update:
        hotkeyName = args.update[0]
        newKeys = args.update[1:]
        updateHotkeys(hotkeyName, newKeys)
        
    elif args.list_cameras:
        listCameras()
        
    elif args.set_camera:
        setCamera(args.set_camera)
        
    elif args.set_library:
        setLibrary(args.set_library)
        
    elif args.test:
        TestMenu()
        
    else:
        runWorker()