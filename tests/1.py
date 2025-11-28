import subprocess
import pytest
import requests
from requests.auth import HTTPBasicAuth
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BMC_IP = "localhost"
BASE_URL = f"https://{BMC_IP}:2443"
USERNAME = "root"
PASSWORD = "0penBmc"

requests.packages.urllib3.disable_warnings()

@pytest.fixture
def session():
    session = requests.Session()
    # session.auth = HTTPBasicAuth(USERNAME, PASSWORD)
    session.verify = False

    response = session.post(
        f"{BASE_URL}/redfish/v1/SessionService/Sessions",
        json={"UserName": USERNAME, "Password": PASSWORD}
    )
    
    session.headers["X-Auth-Token"] = response.headers["X-Auth-Token"]
    yield session

    # return session

def test_redfish_authentication(session):
    logger.info("Тест аутентификации Redfish")
    try:
        response = session.get(f"{BASE_URL}/redfish/v1/SessionService")
        assert response.status_code == 200
        
        sessions_url = f"{BASE_URL}/redfish/v1/SessionService/Sessions"
        auth_data = {"UserName": USERNAME, "Password": PASSWORD}
        response = session.post(sessions_url, json=auth_data)
        
        assert response.status_code in [200, 201]
        session_data = response.json()
        assert "Id" in session_data
        assert session_data["UserName"] == USERNAME
        logger.info("Аутентификация успешна")
        
    except Exception as e:
        logger.error(f"Ошибка аутентификации: {e}")
        raise

def test_system_info(session):
    logger.info("Тест информации о системе")
    try:
        response = session.get(f"{BASE_URL}/redfish/v1/Systems/system")
        assert response.status_code == 200
        
        system_info = response.json()
        assert "PowerState" in system_info
        assert "Status" in system_info
        logger.info(f"Состояние питания: {system_info.get('PowerState')}")
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о системе: {e}")
        raise

def test_power_control(session):
    logger.info("Тест управления питанием")
    try:
        power_url = f"{BASE_URL}/redfish/v1/Systems/system/Actions/ComputerSystem.Reset"
        power_data = {"ResetType": "On"}
        
        response = session.post(power_url, json=power_data)
        assert response.status_code in [200, 202, 204]
        logger.info(f"Команда питания отправлена, статус: {response.status_code}")

        time.sleep(5)
        response = session.get(f"{BASE_URL}/redfish/v1/Systems/system")
        power_state = response.json().get("PowerState")
        
        assert power_state in ["On", "Off", "PoweringOn", "PoweringOff"]
        logger.info(f"Текущее состояние питания: {power_state}")
        
    except Exception as e:
        logger.error(f"Ошибка управления питанием: {e}")
        raise

def test_thermal_subsystem_structure(session):
    logger.info("Тест thermal subsystem")
    try:
        response = session.get(f"{BASE_URL}/redfish/v1/Chassis/chassis/ThermalSubsystem")
        thermal_data = response.json()
        
        assert "Name" in thermal_data
        assert "Status" in thermal_data
        
        status = thermal_data["Status"]
        assert status.get("State") in ["Enabled", "Disabled", "StandbyOff"]
        
        has_fans = "Fans" in thermal_data and len(thermal_data["Fans"]) > 0
        has_temps = "Temperatures" in thermal_data and len(thermal_data["Temperatures"]) > 0
        
        assert has_fans or has_temps, "Должны быть данные о вентиляторах или температуре"
        logger.info(f"Thermal subsystem: fans={has_fans}, temps={has_temps}")
        
    except Exception as e:
        logger.error(f"Ошибка thermal subsystem: {e}")
        raise

def test_processors_summary(session):
    logger.info("Тест информации о процессорах")
    try:
        response = session.get(f"{BASE_URL}/redfish/v1/Systems/system")
        system_data = response.json()
        
        assert "ProcessorSummary" in system_data, "ProcessorSummary отсутствует"
        
        processor_summary = system_data["ProcessorSummary"]
        
        assert "Count" in processor_summary, "Count отсутствует в ProcessorSummary"
        
        count = processor_summary["Count"]
        assert count >= 0, f"Некорректное количество процессоров: {count}"
        logger.info(f"ProcessorSummary Count: {count}")

        response = session.get(f"{BASE_URL}/redfish/v1/Systems/system/Processors")
        processors_data = response.json()
        
        assert "Members@odata.count" in processors_data
        processors_count = processors_data["Members@odata.count"]
        
        assert count == processors_count, f"Несоответствие: ProcessorSummary.Count={count}, Processors.Members@odata.count={processors_count}"
        logger.info(f"Processors Members count: {processors_count}")
        
    except Exception as e:
        logger.error(f"Ошибка processors summary: {e}")
        raise
if __name__ == "__main__":
    logger.info("Запуск тестов Redfish API")
    pytest.main([__file__, "-v", "-s"])