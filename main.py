from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Set
import json
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 定義資料模型
class TrafficData(BaseModel):
    location: str
    event: str

# 全域變數，儲存交通資料和活躍的 WebSocket 連線
traffic_db: List[TrafficData] = []
active_connections: Set[WebSocket] = set()

# 讀取 JSON 檔案
def load_traffic_data():
    global traffic_db
    try:
        with open("traffic_data.json", "r", encoding="utf-8") as file:
            traffic_db = [TrafficData(**item) for item in json.load(file)]
        logger.info("Successfully loaded traffic_data.json")
    except FileNotFoundError:
        traffic_db = [
            TrafficData(location="台北市中正區", event="交通順暢"),
            TrafficData(location="新北市板橋區", event="輕微塞車")
        ]
        logger.warning("traffic_data.json not found, using default data")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        traffic_db = [
            TrafficData(location="台北市中正區", event="交通順暢"),
            TrafficData(location="新北市板橋區", event="輕微塞車")
        ]

# 初始載入資料
load_traffic_data()

# HTML 前端
html = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>交通監控測試</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }
        h1 {
            text-align: center;
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background-color: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        #realtime-update {
            margin-top: 20px;
            padding: 15px;
            background-color: #e0f7fa;
            border-radius: 5px;
            font-size: 1.1em;
        }
    </style>
</head>
<body>
    <h1>交通監控實時更新</h1>
    <h2>所有交通資料</h2>
    <table id="traffic-table">
        <thead>
            <tr>
                <th>地點</th>
                <th>事件</th>
            </tr>
        </thead>
        <tbody id="traffic-data"></tbody>
    </table>
    <h2>實時更新</h2>
    <div id="realtime-update">等待 WebSocket 更新...</div>

    <script>
        // 獲取初始資料（REST API）
        async function fetchTrafficData() {
            try {
                const response = await fetch('http://localhost:8000/traffic');
                if (!response.ok) throw new Error('Failed to fetch traffic data');
                const data = await response.json();
                const tableBody = document.getElementById('traffic-data');
                tableBody.innerHTML = '';
                data.forEach(item => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${item.location}</td>
                        <td>${item.event}</td>
                    `;
                    tableBody.appendChild(row);
                });
            } catch (error) {
                console.error('Error fetching traffic data:', error);
            }
        }

        // WebSocket 連線
        const ws = new WebSocket('ws://localhost:8000/ws/traffic');
        ws.onopen = () => {
            console.log('WebSocket connected');
        };
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const updateDiv = document.getElementById('realtime-update');
                updateDiv.innerHTML = `
                    <strong>最新更新</strong><br>
                    地點: ${data.location}<br>
                    事件: ${data.event}
                `;
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        ws.onclose = () => {
            console.log('WebSocket disconnected');
        };
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        // 頁面載入時獲取初始資料
        window.onload = fetchTrafficData;
    </script>
</body>
</html>
"""

# REST API 端點：返回所有交通資料
@app.get("/traffic", response_model=List[TrafficData])
async def get_traffic():
    logger.info("Fetching traffic data via /traffic")
    return traffic_db

# WebSocket 端點：連線時推送一次預設記錄，並廣播接收到的訊息
@app.websocket("/ws/traffic")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    logger.info("New WebSocket connection established")
    try:
        # 推送第一筆記錄
        if traffic_db:
            await websocket.send_json(traffic_db[0].dict())
            logger.info(f"Sent initial record: {traffic_db[0].dict()}")
        # 等待並廣播訊息
        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"Received message: {data}")
                # 將接收到的訊息廣播給所有連線的客戶端
                for connection in active_connections.copy():
                    try:
                        await connection.send_json(data)
                        logger.info(f"Broadcasted message to connection: {data}")
                    except Exception as e:
                        logger.error(f"Error sending to connection: {e}")
                        active_connections.remove(connection)
            except Exception as e:
                logger.error(f"WebSocket receive error: {e}")
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)
        try:
            await websocket.close()
            logger.info("WebSocket connection closed")
        except RuntimeError as e:
            logger.warning(f"Ignoring RuntimeError on close: {e}")

# 提供前端頁面
@app.get("/")
async def get_root():
    logger.info("Serving HTML page at /")
    return HTMLResponse(html)