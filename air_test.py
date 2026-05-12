import requests
import pandas as pd

API_KEY = "6f536f934349d95301270cc9a20b1ed3fe8dd3ef29435b6c60a67cb8bc4587ec"

url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"

params = {
    "serviceKey": API_KEY,
    "returnType": "json",
    "numOfRows": 100,
    "pageNo": 1,
    "sidoName": "서울",
    "ver": "1.0"
}

response = requests.get(url, params=params)
data = response.json()

items = data['response']['body']['items']
df = pd.DataFrame(items)
print(df[['stationName', 'pm25Value', 'pm10Value', 'no2Value', 'o3Value']])
df.to_csv("air_data.csv", index=False, encoding="utf-8-sig")
print("저장 완료!")