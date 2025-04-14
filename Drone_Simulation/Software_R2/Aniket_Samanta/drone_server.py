import asyncio
import websockets
import json
import random

class DroneSimulator:
    def __init__(self):
        self.altitude = 0
        self.position = (0, 0)
        self.battery = 100
        
    async def generate_sensor_data(self):
        """Simulate drone sensor data"""
        self.altitude += random.uniform(-0.5, 0.5)
        self.position = (
            self.position[0] + random.uniform(-0.2, 0.2),
            self.position[1] + random.uniform(-0.2, 0.2)
        )
        self.battery -= 0.1
        
        return {
            "altitude": max(0, self.altitude),
            "x_pos": self.position[0],
            "y_pos": self.position[1],
            "battery": max(0, self.battery),
            "status": "OK"
        }

async def handler(websocket):
    drone = DroneSimulator()
    print("Drone simulator ready")
    
    try:
        while True:
            # Send sensor data to client
            sensor_data = await drone.generate_sensor_data()
            await websocket.send(json.dumps(sensor_data))
            print(f"Sent: {sensor_data}")
            
            # Wait for commands from client
            commands = await websocket.recv()
            print(f"Received commands: {commands}")
            
            await asyncio.sleep(0.5)  # Simulate 2Hz update rate
            
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server started at ws://localhost:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())