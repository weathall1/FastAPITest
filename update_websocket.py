from pydantic import BaseModel
import json
import websockets
import asyncio


# 定義資料模型，與 main.py 保持一致
class TrafficData(BaseModel):
    location: str
    event: str


# 更新 WebSocket 的函數
async def update_websocket():
    # 重新載入 JSON 檔案
    try:
        with open("traffic_data.json", "r", encoding="utf-8") as file:
            data = [TrafficData(**item) for item in json.load(file)]
    except FileNotFoundError:
        data = [
            TrafficData(location="台北市中正區", event="交通順暢"),
            TrafficData(location="新北市板橋區", event="輕微塞車")
        ]

    # 透過 WebSocket 推送第一筆記錄
    try:
        async with websockets.connect("ws://localhost:8000/ws/traffic") as websocket:
            if data:
                await websocket.send(json.dumps(data[0].dict()))
                # 等待短暫時間，確保伺服器處理訊息
                await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket connection error: {e}")