from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import json

app = FastAPI()

# 定義資料模型
class TrafficData(BaseModel):
    location: str
    event: str

# 全域變數，儲存交通資料
traffic_db = []

# 讀取 JSON 檔案
def load_traffic_data():
    global traffic_db
    try:
        with open("traffic_data.json", "r", encoding="utf-8") as file:
            traffic_db = [TrafficData(**item) for item in json.load(file)]
    except FileNotFoundError:
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
            const data = JSON.parse(event.data);
            const updateDiv = document.getElementById('realtime-update');
            updateDiv.innerHTML = `
                <strong>最新更新</strong><br>
                地點: ${data.location}<br>
                事件: ${data.event}
            `;
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
    return traffic_db

# WebSocket 端點：連線時推送一次預設記錄
@app.websocket("/ws/traffic")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # 推送第一筆記錄
        if traffic_db:
            await websocket.send_json(traffic_db[0].dict())
        # 保持連線，等待外部觸發（如 update_websocket.py）
        while True:
            await websocket.receive_text()  # 等待訊息，避免連線斷開
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# 提供前端頁面
@app.get("/")
async def get():
    return HTMLResponse(html)