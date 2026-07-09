import cv2
import os
import pyautogui

class Eyetracking: 
    def __init__(self, Savespace: str, cameraIndex: int, library: str = "eyetrax", screenWidth: int = 1920, screenHeight: int = 1080) -> None:
        self.Dictonary = Savespace if Savespace else os.getcwd()
        self.cameraIndex = cameraIndex
        self.library = library.lower()
        
        self.width = screenWidth
        self.height = screenHeight
        self.sensitivity_x = 1200 
        self.sensitivity_y = 1200 
        
        if self.library == "eyetrax":
            from eyetrax import GazeEstimator
            self.estimator = GazeEstimator()
        elif self.library == "gazetracking":
            from GazeTracking.gaze_tracking import GazeTracking
            self.estimator = GazeTracking()
        elif self.library == "l2csnet":
            import torch
            from l2cs import Pipeline
            model_path = os.path.join(self.Dictonary, 'L2CSNet_gaze360.pkl')
            self.estimator = Pipeline(
                weights=model_path,
                arch='ResNet50',
                device=torch.device('cpu') 
            )
        else:
            raise ValueError(f"Unsupported library: {library}.")
            
    def cleanup(self) -> None:
        """Führt die Aufräumarbeiten durch, indem alle Ressourcen freigegeben und temporäre Dateien gelöscht werden. Diese Methode sollte aufgerufen werden, wenn die Anwendung ihre Bibliothek wechselt oder geschlossen wird."""
        print(f"[{self.library}] Cleaning up resources...")
        if self.library in ["eyetrax", "gazetracking", "l2csnet"]:
            self.estimator = None
            print(f"[{self.library}] Gaze estimator cleaned up.")
            
    @staticmethod
    def getAvailableCameras(max: int = 5) -> list[int]:
        """Gibt eine Liste der verfügbaren Kamera-IDs zurück. Diese Methode versucht, die Kamera-IDs von 0 bis max zu öffnen und prüft, ob sie erfolgreich geöffnet werden können. Die IDs der verfügbaren Kameras werden in einer Liste zurückgegeben."""
        available_cameras = []
        for i in range(max):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
                cap.release()
        return available_cameras
    
    def calibrate(self, forceRecal: bool) -> None:
        """Führt die Kalibrierung durch, indem überprüft wird, ob Kalibrierungsdaten im angegebenen Verzeichnis vorhanden sind. Wenn keine Daten gefunden werden, wird die 9-Punkte-Kalibrierung durchgeführt und die Daten werden gespeichert. Wenn Daten vorhanden sind, werden sie geladen."""
        pklPath = os.path.join(self.Dictonary, f"calibration_{self.library}.pkl")
        
        if forceRecal and os.path.exists(pklPath):
            os.remove(pklPath)
            print("Existing calibration data removed due to force recalibration.")

        if self.library == "eyetrax":
            from eyetrax import run_9_point_calibration
            if not os.path.exists(pklPath):
                print("No existing calibration data found. Starting 9-point calibration...")
                run_9_point_calibration(self.estimator)
                self.estimator.save_model(pklPath)
                print(f"Calibration completed and saved to {pklPath}.")
            else:
                print(f"Existing calibration data found at {pklPath}. Loading calibration data...")
                self.estimator.load_model(pklPath)
                print("Calibration data loaded successfully.")
                
        elif self.library == "gazetracking":
            print("[GazeTracking] Keine klassische Kalibrierung notwendig. Algorithmus basiert auf Schwellenwerten.")
            
        elif self.library == "l2csnet":
            print("[L2CS-Net] Keine nutzerspezifische Kalibrierung notwendig. End-to-End Modell ist bereits vortrainiert.")

    def get_coordinates(self, frame) -> tuple[float, float]:
        x, y = 0.0, 0.0
        
        if self.library == "eyetrax":
            features, blink = self.estimator.extract_features(frame)
            if features is not None and not blink:
                prediction = self.estimator.predict([features])
                x, y = float(prediction[0][0]), float(prediction[0][1])
                
        elif self.library == "gazetracking":
            self.estimator.refresh(frame)
            if not self.estimator.is_blinking():
                hr = self.estimator.horizontal_ratio()
                vr = self.estimator.vertical_ratio()
                if hr is not None and vr is not None:
                    x = (1- float(hr)) * self.width
                    y = float(vr) * self.height
                    
        elif self.library == "l2csnet":
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.estimator.step(frame_rgb)
            if results is not None and results.pitch.shape[0] > 0:
                pitch = float(results.pitch[0])
                yaw = float(results.yaw[0])
                
                center_x = self.width / 2
                center_y = self.height / 2
                
                x = center_x - (yaw * self.sensitivity_x)
                y = center_y + (pitch * self.sensitivity_y)

        if x != 0.0 and y != 0.0:
            x = max(0.0, min(float(self.width), x))
            y = max(0.0, min(float(self.height), y))
            
        return x, y
        
    def startTracking(self, time: int, silent: bool = True) -> tuple[float, float]:
        """Startet die Augenverfolgung, indem die Kamera geöffnet und die Frames verarbeitet werden. Für jedes Frame werden die Merkmale extrahiert und die Blickkoordinaten vorhergesagt. Die Koordinaten werden in der Konsole ausgegeben. Am Ende der Verfolgung werden die Ressourcen freigegeben und die Fenster geschlossen."""
        cap = cv2.VideoCapture(self.cameraIndex)
        x, y = 0.0, 0.0
        if not cap.isOpened():
            print("Error: Could not open camera with index", self.cameraIndex)
            return x, y
        for i in range(time):
            ret, frame = cap.read()
            if not ret:
                break
                
            current_x, current_y = self.get_coordinates(frame)
            if current_x != 0.0 and current_y != 0.0:
                x, y = current_x, current_y
            
            if not silent: 
                cv2.circle(frame, (int(frame.shape[1]/2), int(frame.shape[0]/2)), 5, (0, 255, 0), -1)
                cv2.imshow(f'Eye Tracking - {self.library.upper()}', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
        cap.release()
        if not silent:
            cv2.destroyAllWindows()
            
        return x, y

if __name__ == "__main__":
    eyetracker = Eyetracking(library="gazetracking", Savespace="", cameraIndex=0)
    eyetracker.calibrate(forceRecal=False)
    
    print("Tracking gestartet... Bitte schau auf einen Punkt auf dem Bildschirm.")
    
    gaze_x, gaze_y = eyetracker.startTracking(time=100, silent=False)
    
    if gaze_x != 0.0 and gaze_y != 0.0:
        print(f"Blickpunkt erkannt: {gaze_x:.2f}, {gaze_y:.2f}. Bewege Maus...")
        pyautogui.moveTo(gaze_x, gaze_y, duration=1.0)
    else:
        print("Es konnte kein stabiler Blickpunkt ermittelt werden.")
        