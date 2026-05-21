WEATHER_MAP = {0: "Clear (맑음)", 1: "Light Cloud (구름 조금)", 2: "Overcast (흐림)", 
               3: "Light Rain (가벼운 비)", 4: "Heavy Rain (폭우)", 5: "Storm (폭풍)"}
SC_MAP = {0: "None", 1: "Full SC", 2: "Virtual SC", 3: "Formation Lap"}
TYRE_MAP = {16: "Soft", 17: "Medium", 18: "Hard", 7: "Intermediate", 8: "Wet"}

def build_lm_context(snapshot):
    context = {
        "race_context": {
            "progress": {"current_lap": 0, "total_laps": 0, "safety_car": "None"},
            "car_status": {"tyre_compound": "Unknown", "pit_stops": 0, "ers_energy_joules": 0, "fuel_delta_laps": 0.0},
            "driver_warnings": {"track_limits_warnings": 0, "time_penalty_seconds": 0}
        },
        "gaps": {"position": 0, "delta_to_front": 0.0, "delta_to_behind": 0.0},
        "power_unit_status": {},
        "weather_forecast": {"current_condition": "Unknown", "rain_chance_percent": 0}
    }

    sess = snapshot.get("session", {})
    lap_info = snapshot.get("lap", {})
    dmg = snapshot.get("damage", {})
    stat = snapshot.get("status", {})

    if not all([sess, lap_info, dmg, stat]):
        return context

    my_lap = lap_info.get("my_data", {})
    all_cars = lap_info.get("all_cars", [])

    context["race_context"]["car_status"]["ers_energy_joules"] = stat.get('m_ersStoreEnergy', 0)
    context["race_context"]["car_status"]["fuel_delta_laps"] = round(stat.get('m_fuelRemainingLaps', 0), 2)
    context["race_context"]["car_status"]["tyre_compound"] = TYRE_MAP.get(stat.get('m_visualTyreCompound', 0), "Unknown")
    
    context["race_context"]["progress"]["current_lap"] = my_lap.get('m_currentLapNum', 0)
    context["race_context"]["car_status"]["pit_stops"] = my_lap.get('m_numPitStops', 0)
    context["race_context"]["driver_warnings"]["track_limits_warnings"] = my_lap.get('m_cornerCuttingWarnings', 0)
    context["race_context"]["driver_warnings"]["time_penalty_seconds"] = my_lap.get('m_penalties', 0)

    my_pos = my_lap.get('m_carPosition', 0)
    context["gaps"]["position"] = my_pos

    if my_pos > 1:
        mins = my_lap.get('m_deltaToCarInFrontMinutesPart', 0)
        ms = my_lap.get('m_deltaToCarInFrontMSPart', 0)
        context["gaps"]["delta_to_front"] = round((mins * 60) + (ms / 1000.0), 3)
    else:
        context["gaps"]["delta_to_front"] = "Leader"

    delta_behind = "Last"
    for car in all_cars:
        if car.get('m_carPosition') == my_pos + 1:
            b_mins = car.get('m_deltaToCarInFrontMinutesPart', 0)
            b_ms = car.get('m_deltaToCarInFrontMSPart', 0)
            delta_behind = round((b_mins * 60) + (b_ms / 1000.0), 3)
            break
    context["gaps"]["delta_to_behind"] = delta_behind

    context["race_context"]["progress"]["total_laps"] = sess.get('m_totalLaps', 0)
    context["race_context"]["progress"]["safety_car"] = SC_MAP.get(sess.get('m_safetyCarStatus', 0), "Unknown")
    context["weather_forecast"]["current_condition"] = WEATHER_MAP.get(sess.get('m_weather', 0), "Unknown")
    
    samples = sess.get('m_weatherForecastSamples', [])
    for sample in samples:
        if sample.get('m_timeOffset', 0) > 0:
            context["weather_forecast"]["rain_chance_percent"] = sample.get('m_rainPercentage', 0)
            break

    for comp, key in [('Gearbox', 'm_gearBoxDamage'), ('ICE', 'm_engineICEWear'), 
                      ('MGU-K', 'm_engineMGUKWear'), ('CE', 'm_engineCEWear')]:
        wear = dmg.get(key, 0)
        status_text = "위험 (70% 이상)" if wear >= 70 else "주의 (50% 이상)" if wear >= 50 else "양호"
        context["power_unit_status"][comp] = {"wear_percent": wear, "status": status_text}

    return context