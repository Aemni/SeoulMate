import pandas as pd
import numpy as np

df = pd.read_csv("seoul_health_dong.csv")

# 1. 각 피처 정규화 (0~100점으로)
from sklearn.preprocessing import MinMaxScaler

features = ['pm25Value', 'pm10Value', '환자수', '병원수', '금연구역수', '공원면적']
scaler = MinMaxScaler(feature_range=(0, 100))
df_scaled = df.copy()
df_scaled[features] = scaler.fit_transform(df[features])

# 2. 건강위험도 점수 계산 (가중치)
# 높을수록 위험 → pm25, pm10, 환자수
# 높을수록 안전 → 병원수, 금연구역수, 공원면적
df_scaled['위험점수'] = (
    df_scaled['pm25Value']            * 0.30 +
    df_scaled['pm10Value']            * 0.15 +
    df_scaled['환자수']               * 0.25 +
    (100 - df_scaled['병원수'])       * 0.20 +
    (100 - df_scaled['금연구역수'])   * 0.05 +
    (100 - df_scaled['공원면적'])     * 0.05
)

# 3. 점수 기준으로 등급 부여
# 분위수 기준으로 등급 부여
q1 = df_scaled['위험점수'].quantile(0.25)
q2 = df_scaled['위험점수'].quantile(0.50)
q3 = df_scaled['위험점수'].quantile(0.75)

print(f"Q1: {q1:.2f}, Q2: {q2:.2f}, Q3: {q3:.2f}")

def assign_grade(score):
    if score < q1:
        return 0  # 낮음
    elif score < q2:
        return 1  # 보통
    elif score < q3:
        return 2  # 위험
    else:
        return 3  # 매우위험

df_scaled['위험등급'] = df_scaled['위험점수'].apply(assign_grade)


print("\n등급 분포:")
print(df_scaled['위험등급'].value_counts().sort_index())

print(df_scaled[['시군구', '행정동', '위험점수', '위험등급']].tail(20))

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# 피처, 타겟 분리
X = df_scaled[features]
y = df_scaled['위험등급']

# 학습/테스트 분리 (80:20)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# RandomForest 학습
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# 평가
y_pred = rf_model.predict(X_test)
print("=== RandomForest 성능 ===")
print(classification_report(y_test, y_pred, 
    target_names=['낮음', '보통', '위험', '매우위험']))

# 피처 중요도
importances = pd.DataFrame({
    '피처': features,
    '중요도': rf_model.feature_importances_
}).sort_values('중요도', ascending=False)
print("\n=== 피처 중요도 ===")
print(importances)

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# 1. 피처 중요도 차트
importances_sorted = importances.sort_values('중요도')
colors = ['#E6F1FB', '#B5D4F4', '#85B7EB', '#378ADD', '#185FA5', '#0C447C']
axes[0].barh(importances_sorted['피처'], importances_sorted['중요도'], color=colors)
axes[0].set_title('피처 중요도', fontsize=14, fontweight='bold')
axes[0].set_xlabel('중요도')
for i, v in enumerate(importances_sorted['중요도']):
    axes[0].text(v + 0.002, i, f'{v:.3f}', va='center', fontsize=10)

# 2. 등급 분포 차트
grade_labels = ['낮음', '보통', '위험', '매우위험']
grade_counts = df_scaled['위험등급'].value_counts().sort_index()
colors2 = ['#1D9E75', '#378ADD', '#EF9F27', '#E24B4A']
bars = axes[1].bar(grade_labels, grade_counts.values, color=colors2, width=0.6)
axes[1].set_title('등급 분포', fontsize=14, fontweight='bold')
axes[1].set_ylabel('동 수')
for bar, count in zip(bars, grade_counts.values):
    axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                str(count), ha='center', fontsize=11, fontweight='bold')

# 3. 위험점수 분포 히스토그램
axes[2].hist(df_scaled['위험점수'], bins=30, color='#378ADD', alpha=0.7, edgecolor='white')
axes[2].axvline(df_scaled['위험점수'].mean(), color='#E24B4A', linestyle='--', linewidth=2, label=f'평균: {df_scaled["위험점수"].mean():.1f}')
axes[2].axvline(df_scaled['위험점수'].median(), color='#EF9F27', linestyle='--', linewidth=2, label=f'중앙값: {df_scaled["위험점수"].median():.1f}')
axes[2].set_title('위험점수 분포', fontsize=14, fontweight='bold')
axes[2].set_xlabel('위험점수')
axes[2].set_ylabel('빈도')
axes[2].legend()

plt.tight_layout()
plt.savefig('health_risk_visualization.png', dpi=150, bbox_inches='tight')
plt.show()
print("저장 완료! health_risk_visualization.png")