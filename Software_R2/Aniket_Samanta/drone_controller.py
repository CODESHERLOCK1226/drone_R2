import asyncio
import websockets
import json
import math
from typing import Dict, Any
from datetime import datetime

class DroneController:
    def __init__(self):
        self.target_altitude = 20  # meters
        self.waypoints = [
            (10, 10), 
            (10, -10), 
            (-10, -10), 
            (-10, 10)
        ]
        self.current_wp = 0
        self.connection_timeout = 5  # seconds
        self.max_retries = 3
        self.retry_delay = 1  # second

    def _format_data(self, data_type: str, data: Dict[str, Any]) -> str:
        """Format sensor or command data for display"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        lines = [f"=== {data_type.upper()} @ {timestamp} ==="]
        for key, value in data.items():
            if isinstance(value, float):
                lines.append(f"{key:>15}: {value:8.3f}")
            else:
                lines.append(f"{key:>15}: {value:8}")
        return "\n".join(lines)

    def _validate_sensor_data(self, data: Dict[str, Any]) -> bool:
        """Validate received sensor data"""
        required_keys = {'altitude', 'x_pos', 'y_pos', 'battery'}
        return all(key in data for key in required_keys)

    def calculate_commands(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate safe control commands with validation"""
        try:
            if not self._validate_sensor_data(sensor_data):
                return {"emergency_land": True}

            dx = self.waypoints[self.current_wp][0] - sensor_data['x_pos']
            dy = self.waypoints[self.current_wp][1] - sensor_data['y_pos']
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance < 2:
                self.current_wp = (self.current_wp + 1) % len(self.waypoints)
                dx = self.waypoints[self.current_wp][0] - sensor_data['x_pos']
                dy = self.waypoints[self.current_wp][1] - sensor_data['y_pos']
                distance = max(0.1, math.sqrt(dx**2 + dy**2))
            
            throttle = 0.1 * (self.target_altitude - sensor_data['altitude'])
            roll = 0.2 * dx / distance
            pitch = 0.2 * dy / distance
            
            return {
                "throttle": max(-1.0, min(1.0, throttle)),
                "roll": max(-1.0, min(1.0, roll)),
                "pitch": max(-1.0, min(1.0, pitch)),
                "yaw": 0.0,
                "emergency_land": sensor_data['battery'] < 15
            }
            
        except (KeyError, TypeError) as e:
            print(f"Invalid sensor data: {e}")
            return {"emergency_land": True}

async def control_drone():
    uri = "ws://localhost:8765"
    controller = DroneController()
    retry_count = 0

    while retry_count < controller.max_retries:
        try:
            print(f"\nConnecting to {uri} (attempt {retry_count + 1}/{controller.max_retries})")
            
            async with websockets.connect(uri, ping_interval=None) as websocket:
                print("Connection established!")
                retry_count = 0
                
                while True:
                    try:
                        # Receive and display sensor data
                        sensor_data = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=controller.connection_timeout
                        )
                        data = json.loads(sensor_data)
                        print("\n" + controller._format_data("SENSOR DATA", data))
                        
                        # Calculate, send, and display commands
                        commands = controller.calculate_commands(data)
                        await websocket.send(json.dumps(commands))
                        print(controller._format_data("SENT COMMANDS", commands))
                        
                    except asyncio.TimeoutError:
                        print("\n Connection timeout - reconnecting...")
                        break
                    except json.JSONDecodeError:
                        print("\n  Invalid JSON data received")
                        continue
                        
        except (websockets.exceptions.ConnectionClosed, 
               websockets.exceptions.ConnectionClosedError) as e:
            print(f"\n⚠  Connection error: {e}")
            retry_count += 1
            await asyncio.sleep(controller.retry_delay)
        except Exception as e:
            print(f"\n  Unexpected error: {e}")
            retry_count += 1
            await asyncio.sleep(controller.retry_delay)

    print("\n Max connection attempts reached. Shutting down.")

if __name__ == "__main__":
    try:
        asyncio.run(control_drone())
    except KeyboardInterrupt:
        print("\n Controller stopped by user")
    except Exception as e:
        print(f"\n Fatal error: {e}")
