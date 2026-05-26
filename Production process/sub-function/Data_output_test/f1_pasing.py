import ctypes
import json
# =============================================================================
# 1. 상수 정의 [cite: 2, 3, 4, 43, 44, 45, 406]
# =============================================================================
MAX_CARS = 22
MAX_PARTICIPANT_NAME_LEN = 32
MAX_TYRE_STINTS = 8
MAX_TYRE_SETS = 20
MAX_MARSHAL_ZONES = 21
MAX_WEATHER_SAMPLES = 64
MAX_SESSIONS_IN_WEEKEND = 12
MAX_LAPS_IN_HISTORY = 100
MAX_LAPS_IN_POSITIONS = 50

# =============================================================================
# 2. 공통 헤더 (29 Bytes) [cite: 10, 11, 22]
# =============================================================================
class PacketHeader(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_packetFormat", ctypes.c_uint16),            # 2025
        ("m_gameYear", ctypes.c_uint8),                 # 25
        ("m_gameMajorVersion", ctypes.c_uint8),
        ("m_gameMinorVersion", ctypes.c_uint8),
        ("m_packetVersion", ctypes.c_uint8),
        ("m_packetId", ctypes.c_uint8),                 # 패킷 ID (0~15)
        ("m_sessionUID", ctypes.c_uint64),
        ("m_sessionTime", ctypes.c_float),
        ("m_frameIdentifier", ctypes.c_uint32),
        ("m_overallFrameIdentifier", ctypes.c_uint32),
        ("m_playerCarIndex", ctypes.c_uint8),
        ("m_secondaryPlayerCarIndex", ctypes.c_uint8),
    ]

# =============================================================================
# [ID 0] Motion Packet [cite: 23, 42]
# =============================================================================
class CarMotionData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_worldPositionX", ctypes.c_float), ("m_worldPositionY", ctypes.c_float), ("m_worldPositionZ", ctypes.c_float),
        ("m_worldVelocityX", ctypes.c_float), ("m_worldVelocityY", ctypes.c_float), ("m_worldVelocityZ", ctypes.c_float),
        ("m_worldForwardDirX", ctypes.c_int16), ("m_worldForwardDirY", ctypes.c_int16), ("m_worldForwardDirZ", ctypes.c_int16),
        ("m_worldRightDirX", ctypes.c_int16), ("m_worldRightDirY", ctypes.c_int16), ("m_worldRightDirZ", ctypes.c_int16),
        ("m_gForceLateral", ctypes.c_float), ("m_gForceLongitudinal", ctypes.c_float), ("m_gForceVertical", ctypes.c_float),
        ("m_yaw", ctypes.c_float), ("m_pitch", ctypes.c_float), ("m_roll", ctypes.c_float),
    ]

class PacketMotionData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_header", PacketHeader), ("m_carMotionData", CarMotionData * MAX_CARS)]

# =============================================================================
# [ID 1] Session Packet [cite: 43, 56, 134]
# =============================================================================
class MarshalZone(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_zoneStart", ctypes.c_float), ("m_zoneFlag", ctypes.c_int8)]

class WeatherForecastSample(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_sessionType", ctypes.c_uint8), ("m_timeOffset", ctypes.c_uint8), ("m_weather", ctypes.c_uint8),
        ("m_trackTemperature", ctypes.c_int8), ("m_trackTemperatureChange", ctypes.c_int8),
        ("m_airTemperature", ctypes.c_int8), ("m_airTemperatureChange", ctypes.c_int8),
        ("m_rainPercentage", ctypes.c_uint8),
    ]

class PacketSessionData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader),
        ("m_weather", ctypes.c_uint8), ("m_trackTemperature", ctypes.c_int8), ("m_airTemperature", ctypes.c_int8),
        ("m_totalLaps", ctypes.c_uint8), ("m_trackLength", ctypes.c_uint16), ("m_sessionType", ctypes.c_uint8),
        ("m_trackId", ctypes.c_int8), ("m_formula", ctypes.c_uint8), ("m_sessionTimeLeft", ctypes.c_uint16),
        ("m_sessionDuration", ctypes.c_uint16), ("m_pitSpeedLimit", ctypes.c_uint8), ("m_gamePaused", ctypes.c_uint8),
        ("m_isSpectating", ctypes.c_uint8), ("m_spectatorCarIndex", ctypes.c_uint8), ("m_sliProNativeSupport", ctypes.c_uint8),
        ("m_numMarshalZones", ctypes.c_uint8), ("m_marshalZones", MarshalZone * MAX_MARSHAL_ZONES),
        ("m_safetyCarStatus", ctypes.c_uint8), ("m_networkGame", ctypes.c_uint8),
        ("m_numWeatherForecastSamples", ctypes.c_uint8), ("m_weatherForecastSamples", WeatherForecastSample * MAX_WEATHER_SAMPLES),
        ("m_forecastAccuracy", ctypes.c_uint8), ("m_aiDifficulty", ctypes.c_uint8),
        ("m_seasonLinkIdentifier", ctypes.c_uint32), ("m_weekendLinkIdentifier", ctypes.c_uint32), ("m_sessionLinkIdentifier", ctypes.c_uint32),
        ("m_pitStopWindowIdealLap", ctypes.c_uint8), ("m_pitStopWindowLatestLap", ctypes.c_uint8), ("m_pitStopRejoinPosition", ctypes.c_uint8),
        ("m_steeringAssist", ctypes.c_uint8), ("m_brakingAssist", ctypes.c_uint8), ("m_gearboxAssist", ctypes.c_uint8),
        ("m_pitAssist", ctypes.c_uint8), ("m_pitReleaseAssist", ctypes.c_uint8), ("m_ERSAssist", ctypes.c_uint8),
        ("m_DRSAssist", ctypes.c_uint8), ("m_dynamicRacingLine", ctypes.c_uint8), ("m_dynamicRacingLineType", ctypes.c_uint8),
        ("m_gameMode", ctypes.c_uint8), ("m_ruleSet", ctypes.c_uint8), ("m_timeOfDay", ctypes.c_uint32),
        ("m_sessionLength", ctypes.c_uint8), ("m_speedUnitsLeadPlayer", ctypes.c_uint8), ("m_temperatureUnitsLeadPlayer", ctypes.c_uint8),
        ("m_speedUnitsSecondaryPlayer", ctypes.c_uint8), ("m_temperatureUnitsSecondaryPlayer", ctypes.c_uint8),
        ("m_numSafetyCarPeriods", ctypes.c_uint8), ("m_numVirtualSafetyCarPeriods", ctypes.c_uint8), ("m_numRedFlagPeriods", ctypes.c_uint8),
        ("m_equalCarPerformance", ctypes.c_uint8), ("m_recoveryMode", ctypes.c_uint8), ("m_flashbackLimit", ctypes.c_uint8),
        ("m_surfaceType", ctypes.c_uint8), ("m_lowFuelMode", ctypes.c_uint8), ("m_raceStarts", ctypes.c_uint8),
        ("m_tyreTemperature", ctypes.c_uint8), ("m_pitLaneTyreSim", ctypes.c_uint8), ("m_carDamage", ctypes.c_uint8),
        ("m_carDamageRate", ctypes.c_uint8), ("m_collisions", ctypes.c_uint8), ("m_collisionsOffForFirstLapOnly", ctypes.c_uint8),
        ("m_mpUnsafePitRelease", ctypes.c_uint8), ("m_mpOffForGriefing", ctypes.c_uint8), ("m_cornerCuttingStringency", ctypes.c_uint8),
        ("m_parcFermeRules", ctypes.c_uint8), ("m_pitStopExperience", ctypes.c_uint8), ("m_safetyCar", ctypes.c_uint8),
        ("m_safetyCarExperience", ctypes.c_uint8), ("m_formationLap", ctypes.c_uint8), ("m_formationLapExperience", ctypes.c_uint8),
        ("m_redFlags", ctypes.c_uint8), ("m_affectsLicenceLevelSolo", ctypes.c_uint8), ("m_affectsLicenceLevelMP", ctypes.c_uint8),
        ("m_numSessionsInWeekend", ctypes.c_uint8), ("m_weekendStructure", ctypes.c_uint8 * MAX_SESSIONS_IN_WEEKEND),
        ("m_sector2LapDistanceStart", ctypes.c_float), ("m_sector3LapDistanceStart", ctypes.c_float),
    ]

# =============================================================================
# [ID 2] Lap Data Packet [cite: 135, 173]
# =============================================================================
class LapData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_lastLapTimeInMS", ctypes.c_uint32), ("m_currentLapTimeInMS", ctypes.c_uint32),
        ("m_sector1TimeMSPart", ctypes.c_uint16), ("m_sector1TimeMinutesPart", ctypes.c_uint8),
        ("m_sector2TimeMSPart", ctypes.c_uint16), ("m_sector2TimeMinutesPart", ctypes.c_uint8),
        ("m_deltaToCarInFrontMSPart", ctypes.c_uint16), ("m_deltaToCarInFrontMinutesPart", ctypes.c_uint8),
        ("m_deltaToRaceLeaderMSPart", ctypes.c_uint16), ("m_deltaToRaceLeaderMinutesPart", ctypes.c_uint8),
        ("m_lapDistance", ctypes.c_float), ("m_totalDistance", ctypes.c_float), ("m_safetyCarDelta", ctypes.c_float),
        ("m_carPosition", ctypes.c_uint8), ("m_currentLapNum", ctypes.c_uint8), ("m_pitStatus", ctypes.c_uint8),
        ("m_numPitStops", ctypes.c_uint8), ("m_sector", ctypes.c_uint8), ("m_currentLapInvalid", ctypes.c_uint8),
        ("m_penalties", ctypes.c_uint8), ("m_totalWarnings", ctypes.c_uint8), ("m_cornerCuttingWarnings", ctypes.c_uint8),
        ("m_numUnservedDriveThroughPens", ctypes.c_uint8), ("m_numUnservedStopGoPens", ctypes.c_uint8),
        ("m_gridPosition", ctypes.c_uint8), ("m_driverStatus", ctypes.c_uint8), ("m_resultStatus", ctypes.c_uint8),
        ("m_pitLaneTimerActive", ctypes.c_uint8), ("m_pitLaneTimeInLaneInMS", ctypes.c_uint16),
        ("m_pitStopTimerInMS", ctypes.c_uint16), ("m_pitStopShouldServePen", ctypes.c_uint8),
        ("m_speedTrapFastestSpeed", ctypes.c_float), ("m_speedTrapFastestLap", ctypes.c_uint8),
    ]

class PacketLapData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader), ("m_lapData", LapData * MAX_CARS),
        ("m_timeTrialPBCarIdx", ctypes.c_uint8), ("m_timeTrialRivalCarIdx", ctypes.c_uint8),
    ]

# =============================================================================
# [ID 3] Event Packet [cite: 174, 248]
# =============================================================================
# 이벤트 내부의 C++ Union 구조체를 파이썬 Union으로 매핑합니다.
class FastestLap(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("vehicleIdx", ctypes.c_uint8), ("lapTime", ctypes.c_float)]
class Retirement(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("vehicleIdx", ctypes.c_uint8), ("reason", ctypes.c_uint8)]
class DRSDisabled(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("reason", ctypes.c_uint8)] # 문서 오타(NEuint8) 보정
class TeamMateInPits(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("vehicleIdx", ctypes.c_uint8)]
class RaceWinner(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("vehicleIdx", ctypes.c_uint8)]
class Penalty(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("penaltyType", ctypes.c_uint8), ("infringementType", ctypes.c_uint8), ("vehicleIdx", ctypes.c_uint8), ("otherVehicleIdx", ctypes.c_uint8), ("time", ctypes.c_uint8), ("lapNum", ctypes.c_uint8), ("placesGained", ctypes.c_uint8)]
class SpeedTrap(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("vehicleIdx", ctypes.c_uint8), ("speed", ctypes.c_float), ("isOverallFastestInSession", ctypes.c_uint8), ("isDriverFastestInSession", ctypes.c_uint8), ("fastestVehicleIdxInSession", ctypes.c_uint8), ("fastestSpeedInSession", ctypes.c_float)]
class StartLights(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("numLights", ctypes.c_uint8)]
class DriveThroughPenaltyServed(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("vehicleIdx", ctypes.c_uint8)]
class StopGoPenaltyServed(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("vehicleIdx", ctypes.c_uint8), ("stopTime", ctypes.c_float)]
class Flashback(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("flashbackFrameIdentifier", ctypes.c_uint32), ("flashbackSessionTime", ctypes.c_float)]
class Buttons(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("buttonStatus", ctypes.c_uint32)]
class Overtake(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("overtakingVehicleIdx", ctypes.c_uint8), ("beingOvertakenVehicleIdx", ctypes.c_uint8)]
class SafetyCar(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("safetyCarType", ctypes.c_uint8), ("eventType", ctypes.c_uint8)]
class Collision(ctypes.LittleEndianStructure): _pack_ = 1; _fields_ = [("vehicle1Idx", ctypes.c_uint8), ("vehicle2Idx", ctypes.c_uint8)]

class EventDataDetails(ctypes.Union):
    _pack_ = 1
    _fields_ = [
        ("FastestLap", FastestLap), ("Retirement", Retirement), ("DRSDisabled", DRSDisabled),
        ("TeamMateInPits", TeamMateInPits), ("RaceWinner", RaceWinner), ("Penalty", Penalty),
        ("SpeedTrap", SpeedTrap), ("StartLights", StartLights), ("DriveThroughPenaltyServed", DriveThroughPenaltyServed),
        ("StopGoPenaltyServed", StopGoPenaltyServed), ("Flashback", Flashback), ("Buttons", Buttons),
        ("Overtake", Overtake), ("SafetyCar", SafetyCar), ("Collision", Collision)
    ]

class PacketEventData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader),
        ("m_eventStringCode", ctypes.c_char * 4),
        ("m_eventDetails", EventDataDetails)
    ]

# =============================================================================
# [ID 4] Participants Packet [cite: 249, 268]
# =============================================================================
class LiveryColour(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("red", ctypes.c_uint8), ("green", ctypes.c_uint8), ("blue", ctypes.c_uint8)]

class ParticipantData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_aiControlled", ctypes.c_uint8), ("m_driverId", ctypes.c_uint8), ("m_networkId", ctypes.c_uint8),
        ("m_teamId", ctypes.c_uint8), ("m_myTeam", ctypes.c_uint8), ("m_raceNumber", ctypes.c_uint8),
        ("m_nationality", ctypes.c_uint8), ("m_name", ctypes.c_char * MAX_PARTICIPANT_NAME_LEN),
        ("m_yourTelemetry", ctypes.c_uint8), ("m_showOnlineNames", ctypes.c_uint8),
        ("m_techLevel", ctypes.c_uint16), ("m_platform", ctypes.c_uint8), ("m_numColours", ctypes.c_uint8),
        ("m_liveryColours", LiveryColour * 4),
    ]

class PacketParticipantsData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_header", PacketHeader), ("m_numActiveCars", ctypes.c_uint8), ("m_participants", ParticipantData * MAX_CARS)]

# =============================================================================
# [ID 5] Car Setups Packet [cite: 269, 294]
# =============================================================================
class CarSetupData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_frontWing", ctypes.c_uint8), ("m_rearWing", ctypes.c_uint8), ("m_onThrottle", ctypes.c_uint8), ("m_offThrottle", ctypes.c_uint8),
        ("m_frontCamber", ctypes.c_float), ("m_rearCamber", ctypes.c_float), ("m_frontToe", ctypes.c_float), ("m_rearToe", ctypes.c_float),
        ("m_frontSuspension", ctypes.c_uint8), ("m_rearSuspension", ctypes.c_uint8), ("m_frontAntiRollBar", ctypes.c_uint8), ("m_rearAntiRollBar", ctypes.c_uint8),
        ("m_frontSuspensionHeight", ctypes.c_uint8), ("m_rearSuspensionHeight", ctypes.c_uint8), ("m_brakePressure", ctypes.c_uint8), ("m_brakeBias", ctypes.c_uint8),
        ("m_engineBraking", ctypes.c_uint8), ("m_rearLeftTyrePressure", ctypes.c_float), ("m_rearRightTyrePressure", ctypes.c_float),
        ("m_frontLeftTyrePressure", ctypes.c_float), ("m_frontRightTyrePressure", ctypes.c_float), ("m_ballast", ctypes.c_uint8), ("m_fuelLoad", ctypes.c_float),
    ]

class PacketCarSetupData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_header", PacketHeader), ("m_carSetupData", CarSetupData * MAX_CARS), ("m_nextFrontWingValue", ctypes.c_float)]

# =============================================================================
# [ID 6] Car Telemetry Packet [cite: 295, 318]
# =============================================================================
class CarTelemetryData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_speed", ctypes.c_uint16), ("m_throttle", ctypes.c_float), ("m_steer", ctypes.c_float),
        ("m_brake", ctypes.c_float), ("m_clutch", ctypes.c_uint8), ("m_gear", ctypes.c_int8),
        ("m_engineRPM", ctypes.c_uint16), ("m_drs", ctypes.c_uint8), ("m_revLightsPercent", ctypes.c_uint8),
        ("m_revLightsBitValue", ctypes.c_uint16), ("m_brakesTemperature", ctypes.c_uint16 * 4),
        ("m_tyresSurfaceTemperature", ctypes.c_uint8 * 4), ("m_tyresInnerTemperature", ctypes.c_uint8 * 4),
        ("m_engineTemperature", ctypes.c_uint16), ("m_tyresPressure", ctypes.c_float * 4), ("m_surfaceType", ctypes.c_uint8 * 4),
    ]

class PacketCarTelemetryData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader), ("m_carTelemetryData", CarTelemetryData * MAX_CARS),
        ("m_mfdPanelIndex", ctypes.c_uint8), ("m_mfdPanelIndexSecondaryPlayer", ctypes.c_uint8), ("m_suggestedGear", ctypes.c_int8),
    ]

# =============================================================================
# [ID 7] Car Status Packet [cite: 319, 349]
# =============================================================================
class CarStatusData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_tractionControl", ctypes.c_uint8), ("m_antiLockBrakes", ctypes.c_uint8), ("m_fuelMix", ctypes.c_uint8),
        ("m_frontBrakeBias", ctypes.c_uint8), ("m_pitLimiterStatus", ctypes.c_uint8), ("m_fuelInTank", ctypes.c_float),
        ("m_fuelCapacity", ctypes.c_float), ("m_fuelRemainingLaps", ctypes.c_float), ("m_maxRPM", ctypes.c_uint16),
        ("m_idleRPM", ctypes.c_uint16), ("m_maxGears", ctypes.c_uint8), ("m_drsAllowed", ctypes.c_uint8),
        ("m_drsActivationDistance", ctypes.c_uint16), ("m_actualTyreCompound", ctypes.c_uint8),
        ("m_visualTyreCompound", ctypes.c_uint8), ("m_tyresAgeLaps", ctypes.c_uint8), ("m_vehicleFIAFlags", ctypes.c_int8),
        ("m_enginePowerICE", ctypes.c_float), ("m_enginePowerMGUK", ctypes.c_float), ("m_ersStoreEnergy", ctypes.c_float),
        ("m_ersDeployMode", ctypes.c_uint8), ("m_ersHarvestedThisLapMGUK", ctypes.c_float), ("m_ersHarvestedThisLapMGUH", ctypes.c_float),
        ("m_ersDeployedThisLap", ctypes.c_float), ("m_networkPaused", ctypes.c_uint8),
    ]

class PacketCarStatusData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_header", PacketHeader), ("m_carStatusData", CarStatusData * MAX_CARS)]

# =============================================================================
# [ID 8] Final Classification Packet [cite: 350, 367]
# =============================================================================
class FinalClassificationData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_position", ctypes.c_uint8), ("m_numLaps", ctypes.c_uint8), ("m_gridPosition", ctypes.c_uint8),
        ("m_points", ctypes.c_uint8), ("m_numPitStops", ctypes.c_uint8), ("m_resultStatus", ctypes.c_uint8),
        ("m_resultReason", ctypes.c_uint8), ("m_bestLapTimeInMS", ctypes.c_uint32), ("m_totalRaceTime", ctypes.c_double),
        ("m_penaltiesTime", ctypes.c_uint8), ("m_numPenalties", ctypes.c_uint8), ("m_numTyreStints", ctypes.c_uint8),
        ("m_tyreStintsActual", ctypes.c_uint8 * MAX_TYRE_STINTS), ("m_tyreStintsVisual", ctypes.c_uint8 * MAX_TYRE_STINTS),
        ("m_tyreStintsEndLaps", ctypes.c_uint8 * MAX_TYRE_STINTS),
    ]

class PacketFinalClassificationData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_header", PacketHeader), ("m_numCars", ctypes.c_uint8), ("m_classificationData", FinalClassificationData * MAX_CARS)]

# =============================================================================
# [ID 9] Lobby Info Packet [cite: 368, 381]
# =============================================================================
class LobbyInfoData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_aiControlled", ctypes.c_uint8), ("m_teamId", ctypes.c_uint8), ("m_nationality", ctypes.c_uint8),
        ("m_platform", ctypes.c_uint8), ("m_name", ctypes.c_char * MAX_PARTICIPANT_NAME_LEN), ("m_carNumber", ctypes.c_uint8),
        ("m_yourTelemetry", ctypes.c_uint8), ("m_showOnlineNames", ctypes.c_uint8),
        ("m_techLevel", ctypes.c_uint16), ("m_readyStatus", ctypes.c_uint8),
    ]

class PacketLobbyInfoData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_header", PacketHeader), ("m_numPlayers", ctypes.c_uint8), ("m_lobbyPlayers", LobbyInfoData * MAX_CARS)]

# =============================================================================
# [ID 10] Car Damage Packet [cite: 382, 406]
# =============================================================================
class CarDamageData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_tyresWear", ctypes.c_float * 4), ("m_tyresDamage", ctypes.c_uint8 * 4),
        ("m_brakesDamage", ctypes.c_uint8 * 4), ("m_tyreBlisters", ctypes.c_uint8 * 4),
        ("m_frontLeftWingDamage", ctypes.c_uint8), ("m_frontRightWingDamage", ctypes.c_uint8),
        ("m_rearWingDamage", ctypes.c_uint8), ("m_floorDamage", ctypes.c_uint8),
        ("m_diffuserDamage", ctypes.c_uint8), ("m_sidepodDamage", ctypes.c_uint8),
        ("m_drsFault", ctypes.c_uint8), ("m_ersFault", ctypes.c_uint8), ("m_gearBoxDamage", ctypes.c_uint8),
        ("m_engineDamage", ctypes.c_uint8), ("m_engineMGUHWear", ctypes.c_uint8), ("m_engineESWear", ctypes.c_uint8),
        ("m_engineCEWear", ctypes.c_uint8), ("m_engineICEWear", ctypes.c_uint8), ("m_engineMGUKWear", ctypes.c_uint8),
        ("m_engineTCWear", ctypes.c_uint8), ("m_engineBlown", ctypes.c_uint8), ("m_engineSeized", ctypes.c_uint8),
    ]

class PacketCarDamageData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_header", PacketHeader), ("m_carDamageData", CarDamageData * MAX_CARS)]

# =============================================================================
# [ID 11] Session History Packet [cite: 407, 428]
# =============================================================================
class LapHistoryData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_lapTimeInMS", ctypes.c_uint32), ("m_sector1TimeMSPart", ctypes.c_uint16), ("m_sector1TimeMinutesPart", ctypes.c_uint8),
        ("m_sector2TimeMSPart", ctypes.c_uint16), ("m_sector2TimeMinutesPart", ctypes.c_uint8),
        ("m_sector3TimeMSPart", ctypes.c_uint16), ("m_sector3TimeMinutesPart", ctypes.c_uint8), ("m_lapValidBitFlags", ctypes.c_uint8),
    ]

class TyreStintHistoryData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_endLap", ctypes.c_uint8), ("m_tyreActualCompound", ctypes.c_uint8), ("m_tyreVisualCompound", ctypes.c_uint8)]

class PacketSessionHistoryData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader), ("m_carIdx", ctypes.c_uint8), ("m_numLaps", ctypes.c_uint8), ("m_numTyreStints", ctypes.c_uint8),
        ("m_bestLapTimeLapNum", ctypes.c_uint8), ("m_bestSector1LapNum", ctypes.c_uint8), ("m_bestSector2LapNum", ctypes.c_uint8), ("m_bestSector3LapNum", ctypes.c_uint8),
        ("m_lapHistoryData", LapHistoryData * MAX_LAPS_IN_HISTORY), ("m_tyreStintsHistoryData", TyreStintHistoryData * MAX_TYRE_STINTS),
    ]

# =============================================================================
# [ID 12] Tyre Sets Packet [cite: 429, 442]
# =============================================================================
class TyreSetData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_actualTyreCompound", ctypes.c_uint8), ("m_visualTyreCompound", ctypes.c_uint8), ("m_wear", ctypes.c_uint8),
        ("m_available", ctypes.c_uint8), ("m_recommendedSession", ctypes.c_uint8), ("m_lifeSpan", ctypes.c_uint8),
        ("m_usableLife", ctypes.c_uint8), ("m_lapDeltaTime", ctypes.c_int16), ("m_fitted", ctypes.c_uint8),
    ]

class PacketTyreSetsData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_header", PacketHeader), ("m_carIdx", ctypes.c_uint8), ("m_tyreSetData", TyreSetData * MAX_TYRE_SETS), ("m_fittedIdx", ctypes.c_uint8)]

# =============================================================================
# [ID 13] Motion Ex Packet [cite: 443, 471]
# =============================================================================
class PacketMotionExData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader),
        ("m_suspensionPosition", ctypes.c_float * 4), ("m_suspensionVelocity", ctypes.c_float * 4), ("m_suspensionAcceleration", ctypes.c_float * 4),
        ("m_wheelSpeed", ctypes.c_float * 4), ("m_wheelSlipRatio", ctypes.c_float * 4), ("m_wheelSlipAngle", ctypes.c_float * 4),
        ("m_wheelLatForce", ctypes.c_float * 4), ("m_wheelLongForce", ctypes.c_float * 4),
        ("m_heightOfCOGAboveGround", ctypes.c_float),
        ("m_localVelocityX", ctypes.c_float), ("m_localVelocityY", ctypes.c_float), ("m_localVelocityZ", ctypes.c_float),
        ("m_angularVelocityX", ctypes.c_float), ("m_angularVelocityY", ctypes.c_float), ("m_angularVelocityZ", ctypes.c_float),
        ("m_angularAccelerationX", ctypes.c_float), ("m_angularAccelerationY", ctypes.c_float), ("m_angularAccelerationZ", ctypes.c_float),
        ("m_frontWheelsAngle", ctypes.c_float), ("m_wheelVertForce", ctypes.c_float * 4),
        ("m_frontAeroHeight", ctypes.c_float), ("m_rearAeroHeight", ctypes.c_float),
        ("m_frontRollAngle", ctypes.c_float), ("m_rearRollAngle", ctypes.c_float),
        ("m_chassisYaw", ctypes.c_float), ("m_chassisPitch", ctypes.c_float),
        ("m_wheelCamber", ctypes.c_float * 4), ("m_wheelCamberGain", ctypes.c_float * 4),
    ]

# =============================================================================
# [ID 14] Time Trial Packet [cite: 472, 487]
# =============================================================================
class TimeTrialDataSet(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_carIdx", ctypes.c_uint8), ("m_teamId", ctypes.c_uint8), ("m_lapTimeInMS", ctypes.c_uint32),
        ("m_sector1TimeInMS", ctypes.c_uint32), ("m_sector2TimeInMS", ctypes.c_uint32), ("m_sector3TimeInMS", ctypes.c_uint32),
        ("m_tractionControl", ctypes.c_uint8), ("m_gearboxAssist", ctypes.c_uint8), ("m_antiLockBrakes", ctypes.c_uint8),
        ("m_equalCarPerformance", ctypes.c_uint8), ("m_customSetup", ctypes.c_uint8), ("m_valid", ctypes.c_uint8),
    ]

class PacketTimeTrialData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("m_header", PacketHeader), ("m_playerSessionBestDataSet", TimeTrialDataSet), ("m_personalBestDataSet", TimeTrialDataSet), ("m_rivalDataSet", TimeTrialDataSet)]

# =============================================================================
# [ID 15] Lap Positions Packet [cite: 488, 494]
# =============================================================================
class PacketLapPositionsData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader),
        ("m_numLaps", ctypes.c_uint8),
        ("m_lapStart", ctypes.c_uint8),
        ("m_positionForVehicleIdx", (ctypes.c_uint8 * MAX_CARS) * MAX_LAPS_IN_POSITIONS),
    ]