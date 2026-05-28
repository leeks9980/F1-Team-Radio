import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

class TyrePredictor:
    def __init__(self, learning_laps=3, target_future_laps=3):
        self.learning_laps = learning_laps
        self.target_future_laps = target_future_laps
        
        # 이전처럼 1바퀴당 1개가 아닌, 10초 주기의 모든 스냅샷을 연속으로 보관
        self.history = []

    def update_lap_data(self, lap_num, w_fl, w_fr, w_rl, w_rr, t_fl, t_fr, t_rl, t_rr, speed, brake, steer, g_lat, g_lon, g_vert):
        self.history.append({
            'lap_num': lap_num,
            'w_fl': w_fl, 'w_fr': w_fr, 'w_rl': w_rl, 'w_rr': w_rr,
            't_fl': t_fl, 't_fr': t_fr, 't_rl': t_rl, 't_rr': t_rr,
            'speed': speed, 'brake': brake, 'steer': steer,
            'g_lat': g_lat, 'g_lon': g_lon, 'g_vert': g_vert
        })

        # 메모리 최적화 (가장 최근 300개의 데이터 스냅샷만 유지, 약 50분 분량)
        if len(self.history) > 300:
            self.history.pop(0)

    def predict(self, current_lap):
        df = pd.DataFrame(self.history)
        if df.empty:
            return None

        # 기록된 고유 랩 수 확인 (학습 조건 만족 여부)
        completed_laps = df['lap_num'].nunique()
        if completed_laps < self.learning_laps or len(df) < 5:
            return None

        wheels = ['fl', 'fr', 'rl', 'rr']
        features_base = ['speed', 'brake', 'steer', 'g_lat', 'g_lon', 'g_vert']
        predictions = {}
        target_lap = current_lap + self.target_future_laps

        for w in wheels:
            target_col = f'w_{w}'
            wheel_features = features_base + [f't_{w}']
            
            # 노트북 로직 적용: 이전 스냅샷 대비 마모 변화량(delta_w) 산출
            df['delta_w'] = df[target_col].diff().fillna(0)
            
            train_df = df.dropna(subset=wheel_features + ['delta_w'])
            if len(train_df) < 2:
                continue

            X = train_df[wheel_features]
            y = train_df['delta_w']

            model = LinearRegression()
            try:
                model.fit(X, y)
            except Exception:
                continue

            # 1개 스냅샷(약 10초) 동안 일어날 마모량 예측
            mean_features = train_df[wheel_features].mean().to_frame().T
            pred_delta_per_snapshot = max(0, model.predict(mean_features)[0])

            # 1바퀴당 평균 스냅샷 개수를 구해 1랩당 마모량 추산
            snapshots_per_lap = len(train_df) / completed_laps
            estimated_wear_per_lap = pred_delta_per_snapshot * snapshots_per_lap

            current_actual_wear = train_df[target_col].iloc[-1]
            predicted_wear = current_actual_wear + (estimated_wear_per_lap * self.target_future_laps)
            predicted_wear = min(100.0, max(current_actual_wear, predicted_wear))

            # 노트북 로직에 맞춘 태깅 (60 초과 위험, 30 초과 주의)
            status = "위험 (Danger)" if predicted_wear > 60 else "주의 (Warning)" if predicted_wear > 30 else "양호 (Good)"

            predictions[f'w_{w}'] = {
                "predicted_target_lap": target_lap,
                "predicted_wear_percent": round(predicted_wear, 2),
                "status": status
            }

        return predictions if predictions else None