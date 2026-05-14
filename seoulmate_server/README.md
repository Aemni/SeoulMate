# 🏙️ SeoulMate Server

> 서울시 426개 행정동의 생활환경 데이터를 분석하여 히트맵 기반 동네 비교 및 최적 주거지를 추천하는 서비스의 백엔드 서버입니다.

---

## 📌 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 서비스명 | SeoulMate - 서울시 살기 좋은 동네 추천 앱 |
| 서버 주소 | https://www.seoulmate.cloud |
| 분석 범위 | 서울시 426개 행정동 |
| 데이터 기간 | 2025년 1월 ~ 2026년 4월 |
| 팀 구성 | 5인 (서버/모델 2명, 프론트 1명, 기타 2명) |

---

## 🗂️ 폴더 구조

```
seoulmate_server/
│  requirements.txt
│
├─app/
│  │  config.py           # 환경변수 설정
│  │  main.py             # FastAPI 앱 진입점
│  │  schemas.py          # Pydantic 응답 스키마
│  │
│  ├─data/                # 모델 산출 데이터 (CSV)
│  │      monthly_risk.csv     # 건강안전도 점수 (6,639행)
│  │      comfort.csv          # 쾌적도 점수
│  │      safety_model.csv     # 치안 점수
│  │      expenses_model.csv   # 생활비용 점수
│  │
│  ├─models/              # AI 예측 모델
│  │      stress_model.pkl     # 소음스트레스 LightGBM 모델
│  │      hvac_model.pkl       # 냉난방수요 LightGBM 모델
│  │
│  ├─preprocess/          # 전처리 스크립트
│  │      append_raw.py
│  │      append_hvac_raw.py
│  │      build_stress_history_standard.py
│  │      build_hvac_history_standard.py
│  │      convert_april_sensor_to_korean.py
│  │      normalize_new_sensor_regions.py
│  │
│  ├─routers/             # API 엔드포인트
│  │      heatmap.py           # GET /v1/heatmap
│  │      overview.py          # GET /v1/overview/{code}
│  │
│  └─services/            # 레이어별 비즈니스 로직
│         health_service.py
│         comfort_service.py
│         safety_service.py
│         stress_service.py
│         hvac_service.py
│         expenses_service.py
│         registry.py          # 레이어 서비스 라우팅
│         score_utils.py       # 공통 점수 유틸
│
└─predictions/
       hvac_2026_04.json       # hvac 예측 결과
```

---

## 🧠 AI 모델 구성

서울시 생활환경을 6개 레이어로 분석하여 각 행정동의 점수(0~100)와 등급(1~5)을 산출합니다.

| 레이어 | 필드명 | 방식 | 데이터 |
|--------|--------|------|--------|
| 건강안전도 | `health` | Rule-based | S-DoT IoT 센서 + 에어코리아 API |
| 쾌적도 | `comfort` | Rule-based | S-DoT IoT 센서 |
| 치안 | `safety` | Rule-based | 공공데이터포털 |
| 소음스트레스 | `stress` | LightGBM | S-DoT IoT 센서 |
| 냉난방수요 | `hvac` | LightGBM | S-DoT IoT 센서 |
| 생활비용 | `expenses` | Rule-based | 공공데이터포털 |

### 건강안전도 점수 산출 파이프라인

```
① 시간별 위험노출점수 계산 (calc_risk_exposure)
        ↓
② 행정동·연도·월별 평균 집계
        ↓
③ MinMaxScaler 정규화
   - 역방향 (낮을수록 위험): 병원수, 공원면적, 금연구역수
   - 정방향 (높을수록 위험): 위험노출시간, 환자수_인구보정
        ↓
④ 가중치 합산
   pm2.5 × 0.20 | 열지수 × 0.18 | 병원수 × 0.10
   pm10 × 0.10  | 공원면적 × 0.08 | 소음 × 0.09 ...
        ↓
⑤ 0~100 재정규화 + 지수변환 (** 0.7)
        ↓
⑥ 분위수 기반 5단계 등급 분류 (1=최상 ~ 5=최하)
        ↓
⑦ 건강안전도 = 100 - 건강위험도 (높을수록 좋음)
```

### 논문 근거 가중치

| 피처 | 가중치 | 논문 |
|------|--------|------|
| PM2.5 | 0.20 | 최종규 (2020), PMC11080206 |
| 열지수 | 0.18 | 임연희·김호 (2011) |
| PM10 | 0.10 | 최종규 (2020) |
| 소음 | 0.09 | 김정만 (2007), Münzel (2025) |
| 병원수 | 0.10 | 안은선 (2024) β=0.057 |
| 공원면적 | 0.08 | 안은선 (2024) β=0.143 |
| 저온 | 0.08 | 임연희·김호 (2011) — 1℃↓ 시 사망률 2%↑ |
| 습도 | 0.08 | Davis (2016) |
| 환자수_인구보정 | 0.07 | HIRA 호흡기질환 통계 |
| 금연구역수 | 0.05 | — (보강 예정) |

---

## 🔌 API 명세

### 공통

| 항목 | 내용 |
|------|------|
| Base URL | `https://www.seoulmate.cloud` |
| 인증 | `x-api-key` Header 필수 |
| 응답 형식 | JSON |

### `GET /v1/heatmap`

메인 화면 히트맵용 — 전체 행정동 레이어 점수 목록 반환

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| x-api-key | string (Header) | ✅ | API 인증 키 |
| layer | string | ✅ | `overall` / `health` / `comfort` / `safety` / `stress` / `hvac` / `expenses` |
| year | int | ✅ | 조회 연도 (2025, 2026) |
| month | int | ✅ | 조회 월 (1~12) |

**응답 예시**
```json
{
  "status": 200,
  "data": [
    {
      "code": "1132069000",
      "dong": "청구동",
      "gu": "중구",
      "score": 73,
      "grade": 2
    }
  ]
}
```

---

### `GET /v1/overview/{code}`

상세보기 — 특정 행정동의 전체 레이어 점수 및 추세 반환

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| x-api-key | string (Header) | ✅ | API 인증 키 |
| code | string (Path) | ✅ | 행정동 코드 (10자리, 예: `1132069000`) |
| year | int (Query) | ✅ | 조회 연도 |
| month | int (Query) | ✅ | 조회 월 |

**응답 예시**
```json
{
  "status": 200,
  "code": "1132069000",
  "dong": "청구동",
  "gu": "중구",
  "score": 68,
  "health": 72,
  "comfort": 65,
  "safety": 80,
  "stress": 55,
  "hvac": 60,
  "expenses": 70,
  "average_score": 67,
  "score_last_year": [61, 63, 65, 68, 70, 72, 69, 67, 65, 63, 60, 58, 61, 64, 66, 68, 68],
  "recent_trend": 1
}
```

**`recent_trend` 값**

| 값 | 의미 |
|----|------|
| 0 | 유지 |
| 1 | 상승 |
| 2 | 하강 |

**`score_last_year` 범위**

전년 1월 ~ 현재 월 (예: 2026년 5월 조회 시 → 2025년 1월 ~ 2026년 5월, 총 17개월)

---

## ⚙️ 로컬 실행

### 환경 요구사항

- Python 3.10 (Anaconda `tm` 환경 사용 — Python 3.14에서 pydantic-core 빌드 오류 발생)
- 패키지 설치:

```bash
conda activate tm
pip install -r requirements.txt
```

### 실행

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📊 데이터 주의사항

| 항목 | 내용 |
|------|------|
| `monthly_risk.csv` | 6,639행, 삭제 금지 |
| `disease.xlsx` | 읽을 때 반드시 `header=3` 설정 |
| 에어코리아 결측치 | 관악구 4~5월, 금천구 12월 → `interpolate` 보간 처리 |
| PM2.5 / PM10 | 구별 월별 고정값 (동별 세분화 불가) |
| 상일동 분리 | 상일제1동 → `1174052500`, 상일제2동 → `1174052600` |
| 전농3동 | 원본 데이터 오류로 제거 |
| 신사동 중복 | 강남구 `11680510`, 은평구 `11380631`, 관악구 `11620685` 구분 필요 |
| 행정동 코드 | 10자리 기준 (8자리 + `00`) |
| 2026년 에어코리아 | API 404 → 2025년 1~4월 평균값으로 대체 |

---

## 🚨 .gitignore 필수 항목

```
# 대용량 원본 데이터
sensor_preprocessed.csv   # 1.1GB
sensor_merged.csv         # 1.5GB
2025airkorea/             # 400MB

# 환경변수
.env

# 캐시
__pycache__/
*.pyc
```

---

## 🗓️ 개발 이력

| 날짜 | 작업 내용 |
|------|-----------|
| 2026-04-29 | 프로젝트 방향 확정, S-DoT IoT 센서 273개 CSV 병합 |
| 2026-04-30 | 전처리 완료 (열지수·위험노출 피처 생성), `sensor_preprocessed.csv` 저장 |
| 2026-05-04 | 에어코리아 대기질 병합, `monthly_risk.csv` 집계 완료 |
| 2026-05-06 | LightGBM → Rule-based 전환 확정, EDA 완료, 최종 점수 산출 |
| 2026-05-11 | 행정동 코드 매핑, 상일동 분리, 지수변환 적용, FastAPI 설계, 인수인계서 v2 작성 |
| 2026-05-13 | comfort/safety DB 적재 완료, FastAPI `/heatmap` `/overview` 구현, GitHub push, 인수인계서 v3 작성 |

---

## 📎 데이터 출처

| 데이터 | 출처 |
|--------|------|
| IoT 센서 (온도·습도·소음 등) | 서울시 S-DoT 스마트도시 데이터 |
| 대기질 (PM2.5 / PM10) | 한국환경공단 에어코리아 API |
| 병원 데이터 | 공공데이터포털 (건강보험심사평가원) |
| 금연구역 | 공공데이터포털 |
| 공원면적 | 공공데이터포털 |
| 호흡기질환 환자수 | 건강보험심사평가원 (HIRA) |
| 인구수 | 행정안전부 주민등록 인구통계 |
| 행정동 코드 | 행정안전부 |
