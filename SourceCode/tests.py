import unittest
import os
import json
import math 
import time 
import random
import threading
from datetime import datetime
import tkinter as tk
import pyautogui
from pynput import keyboard
import psutil  

import main 
from main import getHotkeyIndex, parseKeys, ensureConfig, updateHotkeys, addHotkey, deleteHotkey, Hotkey, onPress

ResultFiles = "EvaluationResults.json"
pyautogui.FAILSAFE = False  
# ==========================================
# TEIL 1: AUTOMATISIERTE LOGIK-TESTS
# ==========================================
class TestHotkeyLogic(unittest.TestCase):
    def setUp(self):
        self.testConfigPath = "test_config_temp.json"
        main.ConfigFile = self.testConfigPath 
        
        self.defaultConfig = {
            "hotkeys:": [
                {
                    "name": "Protected Hotkey",
                    "keys": ["esc"],
                    "function": "quitProgramm",
                    "args": [],
                    "protected": True
                },
                {
                    "name": "Normal Hotkey",
                    "keys": ["w"],
                    "function": "pyautogui.moveTo",
                    "args": [["x", 100], ["y", 100], ["duration", 0.1]],
                    "protected": False
                }
            ]
        }
        with open(self.testConfigPath, 'w') as f:
            json.dump(self.defaultConfig, f)
    
    def tearDown(self):
        if os.path.exists(self.testConfigPath):
            os.remove(self.testConfigPath)
            
    def test01_ConfigCreation(self):
        os.remove(self.testConfigPath)
        config = ensureConfig()
        self.assertTrue(os.path.exists(self.testConfigPath), "Config file should be created if missing.")
        self.assertIn("hotkeys:", config)

    def test02_HotkeyCreation(self):
        addHotkey("New Test Hotkey", ["ctrl", "t"], "pyautogui.click", [], protected=False)
        config = ensureConfig()
        hotkeys = config.get("hotkeys:", [])
        index = getHotkeyIndex(hotkeys, "New Test Hotkey")
        self.assertNotEqual(index, -1, "The new hotkey should exist in the config.")
        self.assertEqual(hotkeys[index]["keys"], ["ctrl", "t"])

    def test03_HotkeyUpdate(self):
        updateHotkeys("Normal Hotkey", ["shift", "x"])
        config = ensureConfig()
        hotkeys = config.get("hotkeys:", [])
        index = getHotkeyIndex(hotkeys, "Normal Hotkey")
        self.assertEqual(hotkeys[index]["keys"], ["shift", "x"], "Keys should be updated to ['shift', 'x'].")

    def test04_HotkeyDeletion_Normal(self):
        deleteHotkey("Normal Hotkey")
        config = ensureConfig()
        index = getHotkeyIndex(config.get("hotkeys:", []), "Normal Hotkey")
        self.assertEqual(index, -1, "Normal Hotkey should be deleted.")

    def test05_HotkeyDeletion_Protected(self):
        deleteHotkey("Protected Hotkey")
        config = ensureConfig()
        index = getHotkeyIndex(config.get("hotkeys:", []), "Protected Hotkey")
        self.assertNotEqual(index, -1, "Protected Hotkey MUST NOT be deleted.")

    def test06_MouseMovementCenter(self):
        sw, sh = pyautogui.size()
        center_x, center_y = sw // 2, sh // 2
        pyautogui.moveTo(10, 10)
        pyautogui.moveTo(center_x, center_y)
        current_x, current_y = pyautogui.position()
        self.assertEqual(current_x, center_x)
        self.assertEqual(current_y, center_y)

    def test07_SimulateKeyPressTrigger(self):
        Hotkey.clearRegistry()
        mock_function_called = []
        def mock_func():
            mock_function_called.append(True)
            
        test_hk = Hotkey([keyboard.Key.ctrl, 'a'], mock_func, [], False, "Test Mock")
        fake_current_keys = {keyboard.Key.ctrl, 'a'}
        is_triggered = test_hk.isPressed(fake_current_keys)
        self.assertTrue(is_triggered, "Hotkey should trigger when simulated keys match.")


def runLogicTests():
    print("\n" + "="*50)
    print("Running automated logic tests...")
    print("="*50)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHotkeyLogic)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("\nAll logic tests passed successfully!")
    else:
        print("\nSome logic tests failed. Please review the test results.")


# ==========================================
# TEIL 2: INTERAKTIVE PRÄZISIONS- UND PERFORMANCE-TESTS
# ==========================================
class GazeEvaluation:
    def __init__(self, tester_name="Tester", library="eyetrax", test_mode="static"):
        self.tester_name = tester_name
        self.library = library.lower()
        self.test_mode = test_mode.lower()
        
        self.session_id = f"SESSION_{self.test_mode.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.timestamp = datetime.now().isoformat()
        self.screen_width, self.screen_height = pyautogui.size()
        
        from eyetracking import Eyetracking
        print(f"Initializing eyetracker with library: {self.library} in mode: {self.test_mode}...")
        self.eyetracker = Eyetracking(library=self.library, Savespace="", cameraIndex=0)
        self.eyetracker.calibrate(forceRecal=False)
        
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg='black')
        self.canvas = tk.Canvas(self.root, width=self.screen_width, height=self.screen_height, bg='black', highlightthickness=0)
        self.canvas.pack()
        
        margin_x, margin_y = int(self.screen_width * 0.1), int(self.screen_height * 0.1)
        mid_x, mid_y = self.screen_width // 2, self.screen_height // 2
        self.target_positions = {
            1: (margin_x, margin_y), 2: (mid_x, margin_y), 3: (self.screen_width - margin_x, margin_y),
            4: (margin_x, mid_y), 5: (mid_x, mid_y), 6: (self.screen_width - margin_x, mid_y),
            7: (margin_x, self.screen_height - margin_y), 8: (mid_x, self.screen_height - margin_y), 9: (self.screen_width - margin_x, self.screen_height - margin_y)
        }
        self.pointResults = []
        
    def _draw_instruction(self, text, duration=1.5):
        text_id = self.canvas.create_text(
            self.screen_width // 2, self.screen_height // 2, 
            text=text, fill="white", font=("Arial", 24)
        )
        self.root.update()
        time.sleep(duration)
        self.canvas.delete(text_id)

    def _monitor_resources(self, stop_event, results_dict):
        """Hintergrund-Thread: Misst CPU und RAM des aktuellen Prozesses."""
        process = psutil.Process(os.getpid())
        process.cpu_percent(interval=None) 
        while not stop_event.is_set():
            try:
                results_dict["cpu"].append(process.cpu_percent(interval=0.1))
                results_dict["ram"].append(process.memory_info().rss / (1024 * 1024))
            except:
                pass

    def run_static_point(self, target_x, target_y, pointID, instruction_text):
        self.canvas.delete("all")
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        self.root.lift()
        
        radius = 20
        oval_id = self.canvas.create_oval(target_x - radius, target_y - radius, target_x + radius, target_y + radius, fill="red", outline="red")
        self._draw_instruction(instruction_text)
        
        arc_radius = 45
        arc_id = self.canvas.create_arc(
            target_x - arc_radius, target_y - arc_radius, target_x + arc_radius, target_y + arc_radius, 
            start=90, extent=0, outline="red", width=4, style=tk.ARC
        )
        
        steps = 40
        for i in range(steps + 1):
            self.canvas.itemconfig(arc_id, extent=-(360 / steps) * i)
            self.root.update()
            time.sleep(1.5 / steps)
            
        self.canvas.itemconfig(oval_id, fill="#00FF00", outline="#00FF00")
        self.canvas.itemconfig(arc_id, outline="#00FF00", extent=0) 
        self.root.update()
        
        frames_to_track = 20
        tracking_result = [0.0, 0.0]
        
        stop_monitor = threading.Event()
        perf_data = {"cpu": [], "ram": []}
        monitor_thread = threading.Thread(target=self._monitor_resources, args=(stop_monitor, perf_data))
        
        def run_tracker():
            tracking_result[0], tracking_result[1] = self.eyetracker.startTracking(time=frames_to_track, silent=True)
            
        tracker_thread = threading.Thread(target=run_tracker)

        monitor_thread.start()
        start_time = time.time()
        tracker_thread.start()
        
        while tracker_thread.is_alive():
            elapsed = time.time() - start_time
            extent = -min(360, (elapsed / 1.0) * 360)
            self.canvas.itemconfig(arc_id, extent=extent)
            self.root.update()
            time.sleep(0.02)
            
        tracker_thread.join()
        end_time = time.time()
        
        stop_monitor.set()
        monitor_thread.join()
        
        self.canvas.itemconfig(arc_id, extent=-360)
        self.root.update()
        time.sleep(0.3)
        pyautogui.moveTo(tracking_result[0], tracking_result[1])
        
        tracking_duration = end_time - start_time
        latency_per_frame_ms = (tracking_duration / frames_to_track) * 1000
        avg_cpu = sum(perf_data["cpu"]) / len(perf_data["cpu"]) if perf_data["cpu"] else 0.0
        max_ram = max(perf_data["ram"]) if perf_data["ram"] else 0.0
        
        return tracking_result[0], tracking_result[1], latency_per_frame_ms, avg_cpu, max_ram

    def run_dynamic_point(self):
        self.canvas.delete("all")
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        self.root.lift()
        
        start_x, start_y = int(self.screen_width * 0.2), self.screen_height // 2
        end_x = int(self.screen_width * 0.8)
        
        radius = 20
        oval_id = self.canvas.create_oval(start_x - radius, start_y - radius, start_x + radius, start_y + radius, fill="#00FF00", outline="#00FF00")
        self._draw_instruction("Folge dem grünen Punkt mit den Augen", duration=2.5)
        
        frames_to_track = 30
        tracking_result = [0.0, 0.0]

        stop_monitor = threading.Event()
        perf_data = {"cpu": [], "ram": []}
        monitor_thread = threading.Thread(target=self._monitor_resources, args=(stop_monitor, perf_data))
        
        def run_tracker():
            tracking_result[0], tracking_result[1] = self.eyetracker.startTracking(time=frames_to_track, silent=True)
            
        tracker_thread = threading.Thread(target=run_tracker)
        
        monitor_thread.start()
        start_time = time.time()
        tracker_thread.start()
        
        move_duration = 1.5 
        while tracker_thread.is_alive():
            elapsed = time.time() - start_time
            progress = min(1.0, elapsed / move_duration)
            current_x = start_x + (end_x - start_x) * progress
            self.canvas.coords(oval_id, current_x - radius, start_y - radius, current_x + radius, start_y + radius)
            self.root.update()
            time.sleep(0.01)
            
        tracker_thread.join()
        end_time = time.time()
        
        stop_monitor.set()
        monitor_thread.join()
        
        time.sleep(0.3)
        pyautogui.moveTo(tracking_result[0], tracking_result[1])
        
        target_avg_x = (start_x + end_x) / 2
        target_avg_y = start_y
        
        tracking_duration = end_time - start_time
        latency_per_frame_ms = (tracking_duration / frames_to_track) * 1000
        avg_cpu = sum(perf_data["cpu"]) / len(perf_data["cpu"]) if perf_data["cpu"] else 0.0
        max_ram = max(perf_data["ram"]) if perf_data["ram"] else 0.0
        
        return tracking_result[0], tracking_result[1], target_avg_x, target_avg_y, latency_per_frame_ms, avg_cpu, max_ram

    def runTest(self):
        print(f"Starting {self.test_mode} evaluation for: {self.tester_name} using: {self.library}")
        
        if self.test_mode == "static":
            selectedPointIDs = random.sample(list(self.target_positions.keys()), 3)
            for step, pointID in enumerate(selectedPointIDs):
                target_x, target_y = self.target_positions[pointID]
                gaze_x, gaze_y, lat, cpu, ram = self.run_static_point(target_x, target_y, pointID, f"Fixiere Punkt {pointID}")
                self._record_result(step+1, f"Grid Point {pointID}", target_x, target_y, gaze_x, gaze_y, lat, cpu, ram)

        elif self.test_mode == "edges":
            selectedPointIDs = [1, 3, 7, 9]
            for step, pointID in enumerate(selectedPointIDs):
                target_x, target_y = self.target_positions[pointID]
                gaze_x, gaze_y, lat, cpu, ram = self.run_static_point(target_x, target_y, pointID, "Fixiere die Ecke")
                self._record_result(step+1, f"Corner {pointID}", target_x, target_y, gaze_x, gaze_y, lat, cpu, ram)

        elif self.test_mode == "random_fullscreen":
            margin = 100
            for step in range(3):
                target_x = random.randint(margin, self.screen_width - margin)
                target_y = random.randint(margin, self.screen_height - margin)
                gaze_x, gaze_y, lat, cpu, ram = self.run_static_point(target_x, target_y, "Rand", "Fixiere den zufälligen Punkt")
                self._record_result(step+1, "Random Fullscreen", target_x, target_y, gaze_x, gaze_y, lat, cpu, ram)

        elif self.test_mode == "dynamic":
            gaze_x, gaze_y, target_x, target_y, lat, cpu, ram = self.run_dynamic_point()
            self._record_result(1, "Moving Target", target_x, target_y, gaze_x, gaze_y, lat, cpu, ram)
            
        self.root.destroy()
        self.saveResults()
        
    def _record_result(self, step, condition, tx, ty, gx, gy, latency, cpu, ram):
        error = math.sqrt((gx - tx) ** 2 + (gy - ty) ** 2)
        self.pointResults.append({
            "step": step,
            "condition": condition,
            "target_x": tx, "target_y": ty,
            "gaze_x": gx, "gaze_y": gy,
            "error_px": error,
            "latency_ms_per_frame": latency,
            "cpu_percent": cpu,
            "ram_mb": ram
        })
        print(f"Step {step}: Error: {error:.1f} px | Latency: {latency:.1f} ms | CPU: {cpu:.1f}% | RAM: {ram:.1f} MB")

    def saveResults(self): 
        errors = [r["error_px"] for r in self.pointResults]
        latencies = [r["latency_ms_per_frame"] for r in self.pointResults]
        cpus = [r["cpu_percent"] for r in self.pointResults]
        rams = [r["ram_mb"] for r in self.pointResults]
        
        avgError = sum(errors) / len(errors) if errors else 0.0
        avgLatency = sum(latencies) / len(latencies) if latencies else 0.0
        avgCpu = sum(cpus) / len(cpus) if cpus else 0.0
        peakRam = max(rams) if rams else 0.0
        
        thresh_error = 50.0   
        thresh_latency = 100.0 
        thresh_cpu = 20.0      
        thresh_ram = 50.0     
        
        result_Data = {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "tester_name": self.tester_name,
            "library": self.library,
            "test_mode": self.test_mode,
            "metrics_summary": {
                "average_error_px": round(avgError, 2),
                "average_latency_ms": round(avgLatency, 2),
                "average_cpu_percent": round(avgCpu, 2),
                "peak_ram_mb": round(peakRam, 2)
            },
            "requirements_check":{
                "NFA2: Accuracy (<= 50px)": avgError <= thresh_error,
                "NFA5: Latency (<= 100ms)": avgLatency <= thresh_latency,
                "NFA7: CPU Usage (<= 20%)": avgCpu <= thresh_cpu,
                "NFA7: RAM Usage (<= 50MB)": peakRam <= thresh_ram
            },
            "detailed_points": self.pointResults,
        }
        
        all_results = []
        if os.path.exists(ResultFiles):
            try:
                with open(ResultFiles, 'r') as f:
                    all_results = json.load(f)
            except json.JSONDecodeError:
                pass
        all_results.append(result_Data)
        
        with open(ResultFiles, 'w') as f:
            json.dump(all_results, f, indent=4)
            
        print("\n" + "="*50)
        print(f"Evaluation completed: {self.session_id}")
        print(f"Mode: {self.test_mode.upper()} | Library: {self.library.upper()}")
        print("-" * 50)
        print(f"Avg Error:   {avgError:.1f} px   [{'PASS' if avgError <= thresh_error else 'FAIL'}]")
        print(f"Avg Latency: {avgLatency:.1f} ms   [{'PASS' if avgLatency <= thresh_latency else 'FAIL'}]")
        print(f"Avg CPU:     {avgCpu:.1f} %    [{'PASS' if avgCpu <= thresh_cpu else 'FAIL'}]")
        print(f"Peak RAM:    {peakRam:.1f} MB   [{'PASS' if peakRam <= thresh_ram else 'FAIL'}]")
        print("="*50 + "\n")
        
        self.eyetracker.cleanup()


def runPrecisionTest(test_mode="static", library=None, tester_name=None):
    if not tester_name:
        tester_name = input(f"\nBitte gib den Namen des Testers ein (Modus: {test_mode}): ")
    if not library:
        library = input("Enter eyetracking library to test (e.g., 'eyetrax'): ")
        
    evaluation = GazeEvaluation(tester_name=tester_name, library=library, test_mode=test_mode)
    evaluation.runTest()
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run gaze evaluation tests.")
    parser.add_argument('--test-logic', action='store_true', help="Run logic tests for main.py functions.")
    parser.add_argument('--run-precision-test', action='store_true', help="Run the gaze evaluation precision test.")
    parser.add_argument('--mode', type=str, choices=['static', 'edges', 'random_fullscreen', 'dynamic'], default='static', help="Test mode.")
    parser.add_argument("--library", type=str, default="eyetrax", help="Specify the eyetracking library.")
    args = parser.parse_args()
    
    if args.test_logic:
        runLogicTests()
    if args.run_precision_test:
        runPrecisionTest(test_mode=args.mode)
    elif not args.test_logic:
        print("No test specified. Use --test-logic or --run-precision-test")