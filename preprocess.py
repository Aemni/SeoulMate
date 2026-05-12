import pandas as pd
import re
from functools import reduce

# 파일 읽기
hospital = pd.read_csv("hospital.csv", encoding="cp949")
nosmoking = pd.read_csv("nosmoking.csv", encoding="cp949")
park = pd.read_csv("park.csv", encoding="cp949")
disease = pd.read_excel("disease.xlsx", header=3, usecols=[0,1,2,3])
air = pd.read_csv("air_data.csv")

# 병원 정제
hospital_clean = hospital[hospital['영업상태명'] == '영업/정상'][
    ['사업장명', '업태구분명', '영업상태명', '도로명주소', '좌표정보(X)', '좌표정보(Y)']
].reset_index(drop=True)

# 금연구역 정제
nosmoking_clean = nosmoking[
    ['시군구명', '금연구역명', '금연구역구분', '위도', '경도']
].reset_index(drop=True)

# 공원 정제
park_clean = park[
    ['공원명', '면적', '지역', 'X좌표(WGS84)', 'Y좌표(WGS84)']
].reset_index(drop=True)

# 질병 정제
disease.columns = ['질환명', '시도', '시군구', '환자수']
disease_clean = disease[
    (disease['시도'] == '서울') &
    (disease['시군구'] != '계') &
    (disease['시군구'].notna())
].reset_index(drop=True)

# 1. 병원 - 구별 병원 수 집계
# 병원 - 동 단위 집계
# 병원 - 동 단위 집계
hospital_clean['시군구'] = hospital_clean['도로명주소'].str.extract(r'서울특별시 (\S+구)')
hospital_clean['행정동'] = hospital_clean['도로명주소'].str.extract(r'\(([가-힣]+동)\)')
hospital_count = hospital_clean.groupby(['시군구', '행정동']).size().reset_index(name='병원수')

print(hospital_count.head(10))
print(f"총 {len(hospital_count)}개 동")

# 2. 금연구역 - 구별 금연구역 수 집계
nosmoking_count = nosmoking_clean.groupby('시군구명').size().reset_index(name='금연구역수')
nosmoking_count.columns = ['시군구', '금연구역수']

# 3. 공원 - 서울만 + 면적 숫자 추출 + 구별 합계
park_clean = park_clean[park_clean['지역'].str.contains('구', na=False)]
park_clean['면적_숫자'] = park_clean['면적'].str.extract(r'([\d.]+)').astype(float)
park_area = park_clean.groupby('지역')['면적_숫자'].sum().reset_index()
park_area.columns = ['시군구', '공원면적']

# 4. 대기오염 - 구별 평균
air['pm25Value'] = pd.to_numeric(air['pm25Value'], errors='coerce')
air['pm10Value'] = pd.to_numeric(air['pm10Value'], errors='coerce')
air['시군구'] = air['stationName'].str.extract(r'(\S+구)')
air_avg = air.groupby('시군구')[['pm25Value', 'pm10Value']].mean().reset_index()

# 5. 전체 합치기
dfs = [
    hospital_count,
    nosmoking_count,
    park_area,
    air_avg,
    disease_clean[['시군구', '환자수']]
]
merged = reduce(lambda l, r: pd.merge(l, r, on='시군구', how='outer'), dfs)

# 6. 이상한 행 제거 + NaN 0으로 채우기
def is_valid_gu(name):
    if pd.isna(name):
        return False
    name = str(name).strip()
    return bool(re.fullmatch(r'[가-힣]{1,4}구', name))

merged = merged[merged['시군구'].apply(is_valid_gu)].reset_index(drop=True)
merged = merged.fillna(0)

print(merged)
print(merged[merged['시군구'].str.contains('중', na=False)])
missing_ratio = (
    merged.isna().mean()
    .sort_values(ascending=False)
    .reset_index()
)

missing_ratio.columns = ["컬럼명", "결측률"]
missing_ratio["결측률(%)"] = (missing_ratio["결측률"] * 100).round(2)
print(missing_ratio)

air = pd.read_csv("air_data.csv")

missing_ratio_air = (
    air.isna().mean()
    .sort_values(ascending=False)
    .reset_index()
)

missing_ratio_air.columns = ["컬럼명", "결측률"]
missing_ratio_air["결측률(%)"] = (missing_ratio_air["결측률"] * 100).round(2)
print(missing_ratio_air)

import requests

url = "https://grpc-proxy-server-mkvo6j4wsq-du.a.run.app/v1/regcodes"
params = {
    "regcode_pattern": "11*00",
    "is_ignore_zero": "true"
}

response = requests.get(url, params=params)
data = response.json()

dong_list = []
for item in data['regcodes']:
    name = item['name']
    parts = name.split()
    if len(parts) == 3:
        gu = parts[1]
        dong = parts[2]
        dong_list.append({'시군구': gu, '행정동': dong})

dong_df = pd.DataFrame(dong_list)
# dong_df 중복 제거
dong_df = dong_df.drop_duplicates(subset=['시군구', '행정동']).reset_index(drop=True)
print(f"dong_df 총 {len(dong_df)}개 동")

# dong_df 기준으로 병원수 붙이기
merged_dong = pd.merge(dong_df, hospital_count, on=['시군구', '행정동'], how='left')
merged_dong['병원수'] = merged_dong['병원수'].fillna(0)

# 구 단위 데이터 붙이기
gu_data = merged[['시군구', '금연구역수', '공원면적', 'pm25Value', 'pm10Value', '환자수']]\
    .drop_duplicates(subset=['시군구']).reset_index(drop=True)
merged_dong = pd.merge(merged_dong, gu_data, on='시군구', how='left')

print(merged_dong.head(10))
print(f"\n총 {len(merged_dong)}개 동")

# 병원에는 있는데 dong_df에는 없는 동
hospital_dongs = set(hospital_count['행정동'].tolist())
dong_df_dongs = set(dong_df['행정동'].tolist())

merged_dong.to_csv("seoul_health_dong.csv", index=False, encoding="utf-8-sig")
print("저장 완료!")