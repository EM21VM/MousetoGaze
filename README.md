# MousetoGaze

Dieses Tool kombiniert Tastatur-Hotkeys mit Eyetracking-Technologien. Es ermöglicht Benutzern, vordefinierte Tasten oder Tastenkombinationen zu drücken, um Aktionen auszulösen – wie beispielsweise den Mauszeiger dorthin zu bewegen, wo der Benutzer gerade auf den Bildschirm schaut. Das System unterstützt mehrere Eyetracking-Bibliotheken (`eyetrax`, `gazetracking`, `l2csnet`) und bietet umfangreiche Testwerkzeuge.

## Funktionen

* **Dynamische Hotkeys:** Konfiguriere beliebige Tastenkombinationen, um Aktionen oder Mausbewegungen zu steuern.
* **Eyetracking-Integration:** Steuere deine Maus mit den Augen (unterstützt 9-Punkt-Kalibrierung je nach verwendeter Bibliothek).
* **CLI-Steuerung:** Verwalte Kameras, Bibliotheken und Hotkeys direkt über die Kommandozeile.
* **Live-Reload:** Änderungen an der Konfiguration (`config.json`) werden zur Laufzeit erkannt und automatisch übernommen.
* **Test-Suite:** Integrierte Leistungs- und Präzisionstests (Logik-Tests, statische/dynamische Gaze-Tests) mit Ressourcenüberwachung (CPU/RAM).

---

## Die config.json Konfiguration

Beim ersten Start des Programms (durch Ausführen von `MousetoGaze.exe` im Terminal oder per Doppelklick) sucht das Tool im selben Verzeichnis nach einer `config.json`. **Wird keine gefunden, erstellt das Tool automatisch eine Standardkonfiguration.** Diese Datei speichert deine aktiven Hotkeys, die ausgewählte Kamera und die verwendete Eyetracking-Bibliothek. Du kannst diese Datei auf zwei Arten anpassen:

1.  **Manuell:** Öffne die `config.json` in einem Texteditor und bearbeite die Werte. Das Programm lädt Änderungen im laufenden Betrieb automatisch neu.
2.  **Über die CLI:** Nutze die unten beschriebenen Befehle (z. B. `--add`, `--delete`, `--set-camera`), um das Tool die Datei sicher und fehlerfrei überschreiben zu lassen.

### Beispiel für die Struktur der config.json

> **Hinweis:** Beachte, dass der Key für die Hotkeys im JSON-Format explizit `"hotkeys:"` (inklusive Doppelpunkt im Namen) heißt, da dies von der internen Logik so erwartet wird.

```json
{
    "cameraIndex": 0,
    "library": "eyetrax",
    "forceRecalibration": false,
    "hotkeys:": [
        {
            "name": "Eyetracking Hotkey",
            "keys": ["ctrl_l","g"],
            "function": "moveMouseToGaze",
            "args": [["time",30]],
            "protected": true
        },
        {
            "name": "Quit Program",
            "keys": ["esc","ctrl_l"],
            "function": "quitProgramm",
            "args": [],
            "protected": true
        }
    ]
}
````
## Kommandozeilen-Nutzung (CLI)

Das Programm bringt ein umfangreiches CLI-Interface (Command Line Interface) mit. Wenn du die `MousetoGaze.exe` ohne Argumente startest, geht es direkt in den "Worker-Modus" (Hintergrundüberwachung). Öffne ein Terminal (z. B. CMD oder PowerShell) in dem Ordner, in dem die `.exe` liegt, und nutze die folgenden Argumente, um das Tool zu konfigurieren:

### Allgemeine Befehle
* `MousetoGaze.exe --debug`
    Startet das Programm mit detaillierteren Konsolenausgaben (hilfreich zur Fehlersuche).
* `MousetoGaze.exe --test`
    Öffnet das interaktive Testmenü für automatisierte Logiktests und Eyetracking-Präzisionstests.

### Hardware & Bibliotheken verwalten
* `MousetoGaze.exe --list-cameras`
    Listet alle am System erkannten Kameras mit ihrer ID auf.
* `MousetoGaze.exe --set-camera <CameraID>`
    Setzt die zu verwendende Kamera (z.B. `MousetoGaze.exe --set-camera 1`). *Erzwingt bei Neustart eine Rekalibrierung.*
* `MousetoGaze.exe --set-library <Library>`
    Wechselt die Eyetracking-Engine. Erlaubt sind `eyetrax`, `gazetracking` oder `l2csnet`.

### Hotkeys verwalten
* `MousetoGaze.exe --list-functions`
    Zeigt alle verfügbaren internen Python-Funktionen an, die einem Hotkey zugewiesen werden können (z.B. `moveMouseToGaze`, `pyautogui.click`).
* `MousetoGaze.exe --list-hotkeys`
    Zeigt eine Liste aller aktuell registrierten Hotkeys an.
* `MousetoGaze.exe --add <Name> <Keys> <Function> <Args> <Protected>`
    Fügt einen neuen Hotkey hinzu. Die Argumente für Tasten und Parameter müssen oft im JSON-Format übergeben werden.
    *Beispiel:* `MousetoGaze.exe --add "Klicker" '["c"]' "pyautogui.click" '[]' False`
* `MousetoGaze.exe --update <Name> <Key1> <Key2> ...`
    Aktualisiert die Tastenbelegung eines existierenden Hotkeys.
    *Beispiel:* `MousetoGaze.exe --update "Eyetracking Hotkey" "h" "Key.shift"`
* `MousetoGaze.exe --delete <Name_oder_Index>`
    Löscht einen Hotkey aus der Konfiguration. (Geschützte Hotkeys können nicht gelöscht werden).
    *Beispiel:* `MousetoGaze.exe --delete 2`

---

## Tests durchführen

Dieses Tool bringt eine eigene Test-Umgebung mit, die über `MousetoGaze.exe --test` aufgerufen wird.

Das interaktive Testmenü bietet:
1.  **Automated Logic Tests:** Prüft, ob die Hotkey-Konfigurationen, Aktualisierungen und das Laden der JSON-Datei korrekt funktionieren.
2.  **Interactive Precision Tests:** Startet eine Vollbild-UI, bei der der Nutzer verschiedene Punkte auf dem Bildschirm fixieren muss. Es misst Latenz, Abweichung in Pixeln (Error), CPU- sowie RAM-Auslastung und speichert die Ergebnisse automatisch in einer Datei namens `EvaluationResults.json`.
