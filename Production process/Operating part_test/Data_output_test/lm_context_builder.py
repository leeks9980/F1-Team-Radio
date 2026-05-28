# context.py

WEATHER_MAP = {
    0: "Clear (맑음)", 1: "Light Cloud (구름 조금)", 2: "Overcast (흐림)", 
    3: "Light Rain (가벼운 비)", 4: "Heavy Rain (폭우)", 5: "Storm (폭풍)"
}
SC_MAP = {0: "None", 1: "Full SC", 2: "Virtual SC", 3: "Formation Lap"}
TYRE_MAP = {16: "Soft", 17: "Medium", 18: "Hard", 7: "Intermediate", 8: "Wet"}

TRACK_MAP = {
    0: "Melbourne", 1: "Paul Ricard", 2: "Shanghai", 3: "Sakhir", 4: "Catalunya",
    5: "Monaco", 6: "Montreal", 7: "Silverstone", 8: "Hockenheim", 9: "Hungaroring",
    10: "Spa", 11: "Monza", 12: "Singapore", 13: "Suzuka", 14: "Austin",
    15: "Interlagos", 16: "Jeddah", 17: "Imola", 18: "Miami", 19: "Zandvoort",
    20: "Losail", 21: "Las Vegas", 22: "Spielberg", 23: "Baku", 24: "Mexico"
}

SESSION_MAP = {
    0: "Unknown", 1: "FP1", 2: "FP2", 3: "FP3", 4: "Short FP", 5: "Q1",
    6: "Q2", 7: "Q3", 8: "Short Q", 9: "OSQ", 10: "R", 11: "R2",
    12: "R3", 13: "Time Trial"
}

FLAG_MAP = {
    0: "None", 1: "Green", 2: "Blue", 3: "Yellow", 4: "Red"
}

def build_lm_context(snapshot):
    context = {
        "race_context": {
            "session_info": {
                "track_name": "Unknown",
                "session_type": "Unknown",
                "track_temp_celsius": 0,
                "air_temp_celsius": 0
            },
            "progress": {"current_lap": 0, "total_laps": 0, "safety_car": "None"},
            "car_status": {
                "tyre_compound": "Unknown", 
                "pit_stops": 0, 
                "ers_energy_joules": 0.0, 
                "fuel_delta_laps": 0.0,
                "drs_allowed": "False",
                "drs_engaged": "False"
            },
            # [추가] 에어로 파츠 파손 상태 구조체 신설
            "aero_damage": {
                "front_left_wing_wear_percent": 0,
                "front_right_wing_wear_percent": 0,
                "rear_wing_wear_percent": 0,
                "floor_wear_percent": 0,
                "diffuser_wear_percent": 0,
                "status": "정상"
            },
            "driver_warnings": {
                "track_limits_warnings": 0, 
                "time_penalty_seconds": 0,
                "fia_flag": "None"
            }
        },
        "gaps": {
            "position": 0, 
            "delta_to_front": 0.0, 
            "front_car_tyre": "Unknown",
            "delta_to_behind": 0.0,
            "behind_car_tyre": "Unknown"
        },
        "power_unit_status": {},
        "weather_forecast": {"current_condition": "Unknown", "rain_chance_percent": 0},
        "raw_tyres_wear": [0.0, 0.0, 0.0, 0.0],
        "raw_telemetry": {
            "tyre_surface_temp": [0, 0, 0, 0],
            "tyre_inner_temp": [0, 0, 0, 0],
            "brake_temp": [0, 0, 0, 0],
            "speed": 0,
            "throttle": 0.0,
            "brake": 0.0,
            "gear": 0,
            "steer": 0.0
        }
    }

    sess = snapshot.get("session", {})
    lap_info = snapshot.get("lap", {})
    dmg = snapshot.get("damage", {})
    stat = snapshot.get("status", {})
    telemetry = snapshot.get("telemetry", {})

    if not all([sess, lap_info, dmg, stat, telemetry]):
        return context

    my_lap = lap_info.get("my_data", {})
    all_cars = lap_info.get("all_cars", [])
    all_status = stat.get("all_status", [])

    # 1. 서킷 및 세션 정보
    context["race_context"]["session_info"]["track_name"] = TRACK_MAP.get(sess.get("m_trackId", -1), "Unknown")
    context["race_context"]["session_info"]["session_type"] = SESSION_MAP.get(sess.get("m_sessionType", 0), "Unknown")
    context["race_context"]["session_info"]["track_temp_celsius"] = sess.get("m_trackTemperature", 0)
    context["race_context"]["session_info"]["air_temp_celsius"] = sess.get("m_airTemperature", 0)

    # 2. 차량 기본 상태 및 DRS
    context["race_context"]["car_status"]["ers_energy_joules"] = stat.get('m_ersStoreEnergy', 0.0)
    context["race_context"]["car_status"]["fuel_delta_laps"] = round(stat.get('m_fuelRemainingLaps', 0.0), 2)
    context["race_context"]["car_status"]["tyre_compound"] = TYRE_MAP.get(stat.get('m_visualTyreCompound', 0), "Unknown")
    context["race_context"]["car_status"]["drs_allowed"] = "True" if stat.get('m_drsAllowed', 0) == 1 else "False"
    context["race_context"]["car_status"]["drs_engaged"] = "True" if telemetry.get('m_drs', 0) == 1 else "False"
    
    # 3. [핵심 수정] 에어로 파츠 파손 파싱 로직 주입
    fl_wing = dmg.get('m_frontLeftWingDamage', 0)
    fr_wing = dmg.get('m_frontRightWingDamage', 0)
    r_wing = dmg.get('m_rearWingDamage', 0)
    floor = dmg.get('m_floorDamage', 0)
    diffuser = dmg.get('m_diffuserDamage', 0)

    context["race_context"]["aero_damage"] = {
        "front_left_wing_wear_percent": fl_wing,
        "front_right_wing_wear_percent": fr_wing,
        "rear_wing_wear_percent": r_wing,
        "floor_wear_percent": floor,
        "diffuser_wear_percent": diffuser,
        "status": "파손 심각 (교체 필요)" if (fl_wing >= 50 or fr_wing >= 50 or r_wing >= 50) else "데미지 있음" if (fl_wing > 0 or fr_wing > 0 or r_wing > 0 or floor > 0 or diffuser > 0) else "양호"
    }

    # 4. 레이스 진행도 및 깃발/경고
    context["race_context"]["progress"]["current_lap"] = my_lap.get('m_currentLapNum', 0)
    context["race_context"]["progress"]["total_laps"] = sess.get('m_totalLaps', 0)
    context["race_context"]["progress"]["safety_car"] = SC_MAP.get(sess.get('m_safetyCarStatus', 0), "Unknown")
    context["race_context"]["driver_warnings"]["track_limits_warnings"] = my_lap.get('m_cornerCuttingWarnings', 0)
    context["race_context"]["driver_warnings"]["time_penalty_seconds"] = my_lap.get('m_penalties', 0)
    context["race_context"]["driver_warnings"]["fia_flag"] = FLAG_MAP.get(stat.get('m_vehicleFiaFlags', 0), "None")

    # 5. 순위 및 앞뒤 차량 정보
    my_pos = my_lap.get('m_carPosition', 0)
    context["gaps"]["position"] = my_pos

    if my_pos > 1:
        mins = my_lap.get('m_deltaToCarInFrontMinutesPart', 0)
        ms = my_lap.get('m_deltaToCarInFrontMSPart', 0)
        context["gaps"]["delta_to_front"] = round((mins * 60) + (ms / 1000.0), 3)
        
        for car in all_cars:
            if car.get('m_carPosition') == my_pos - 1:
                f_idx = car.get('car_index', -1)
                if 0 <= f_idx < len(all_status):
                    context["gaps"]["front_car_tyre"] = TYRE_MAP.get(all_status[f_idx].get('m_visualTyreCompound', 0), "Unknown")
                break
    else:
        context["gaps"]["delta_to_front"] = "Leader"
        context["gaps"]["front_car_tyre"] = "None"

    delta_behind = "Last"
    behind_car_tyre = "None"
    for car in all_cars:
        if car.get('m_carPosition') == my_pos + 1:
            b_mins = car.get('m_deltaToCarInFrontMinutesPart', 0)
            b_ms = car.get('m_deltaToCarInFrontMSPart', 0)
            delta_behind = round((b_mins * 60) + (b_ms / 1000.0), 3)
            
            b_idx = car.get('car_index', -1)
            if 0 <= b_idx < len(all_status):
                behind_car_tyre = TYRE_MAP.get(all_status[b_idx].get('m_visualTyreCompound', 0), "Unknown")
            break
    context["gaps"]["delta_to_behind"] = delta_behind
    context["gaps"]["behind_car_tyre"] = behind_car_tyre

    # 6. 날씨 정보
    context["weather_forecast"]["current_condition"] = WEATHER_MAP.get(sess.get('m_weather', 0), "Unknown")
    samples = sess.get('m_weatherForecastSamples', [])
    for sample in samples:
        if sample.get('m_timeOffset', 0) > 0:
            context["weather_forecast"]["rain_chance_percent"] = sample.get('m_rainPercentage', 0)
            break

    # 7. 파워 유닛 마모도
    for comp, key in [('Gearbox', 'm_gearBoxDamage'), ('ICE', 'm_engineICEWear'), 
                      ('MGU-K', 'm_engineMGUKWear'), ('CE', 'm_engineCEWear')]:
        wear = dmg.get(key, 0)
        status_text = "위험 (70% 이상)" if wear >= 70 else "주의 (50% 이상)" if wear >= 50 else "양호"
        context["power_unit_status"][comp] = {"wear_percent": wear, "status": status_text}

    # 8. 타이어 물리 데이터 상세화
    context["raw_tyres_wear"] = [
        dmg.get('m_tyresWear', [0,0,0,0])[0],
        dmg.get('m_tyresWear', [0,0,0,0])[1],
        dmg.get('m_tyresWear', [0,0,0,0])[2],
        dmg.get('m_tyresWear', [0,0,0,0])[3]
    ]
    
    context["raw_telemetry"]["tyre_surface_temp"] = list(telemetry.get('m_tyresSurfaceTemperature', [0,0,0,0]))
    context["raw_telemetry"]["tyre_inner_temp"] = list(telemetry.get('m_tyresInnerTemperature', [0,0,0,0]))
    context["raw_telemetry"]["brake_temp"] = list(telemetry.get('m_brakesTemperature', [0,0,0,0]))

    # 9. 드라이버 입력 제어 정보
    context["raw_telemetry"]["speed"] = telemetry.get('m_speed', 0)
    context["raw_telemetry"]["throttle"] = round(telemetry.get('m_throttle', 0.0), 2)
    context["raw_telemetry"]["brake"] = round(telemetry.get('m_brake', 0.0), 2)
    context["raw_telemetry"]["gear"] = telemetry.get('m_gear', 0)
    context["raw_telemetry"]["steer"] = round(telemetry.get('m_steer', 0.0), 4)

    return context