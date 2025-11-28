import pytest
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

@pytest.fixture
def driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-certificate-errors')
    
    driver = webdriver.Chrome(service=Service('/usr/bin/chromedriver'), options=options)
    yield driver
    driver.quit()

def test_find_openbmc_web(driver):
    driver.get("https://localhost:2443")
    time.sleep(2)
    assert any(word in driver.page_source.lower() 
               for word in ['openbmc', 'username', 'password']), "OpenBMC не найден"

def test_successful_login(driver):
    driver.get("https://localhost:2443")
    time.sleep(1)
    driver.find_element(By.ID, "username").send_keys("root")
    driver.find_element(By.ID, "password").send_keys("0penBmc") 
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(2)

    assert "login" not in driver.current_url, "Авторизация не удалась"

def test_wrong_data(driver):
    driver.get("https://localhost:2443")
    time.sleep(1)
    driver.find_element(By.ID, "username").send_keys("kolya")
    driver.find_element(By.ID, "password").send_keys("Chaos chaos chaos chaos") 
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(3)
    assert "login" in driver.current_url, "Колян, ты что творишь?"

def test_account_block(driver):
    for i in range(3):
        driver.get("https://localhost:2443")
        driver.find_element(By.ID, "username").send_keys("testuser")
        driver.find_element(By.ID, "password").send_keys("i")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(10)
        assert "login" in driver.current_url

    driver.get("https://localhost:2443")
    driver.find_element(By.ID, "username").send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("TestKolya")
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(10)
    
    assert "login" in driver.current_url, "Аккаунт не заблокирован!"
    print("✅ Аккаунт заблокирован!")

def test_temperature_redfish(driver):
    driver.get("https://localhost:2443/redfish/v1/Chassis/chassis/Thermal")
    time.sleep(2)
    
    if "login" in driver.current_url:
        driver.find_element(By.ID, "username").send_keys("root")
        driver.find_element(By.ID, "password").send_keys("0penBmc") 
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(10)

        driver.get("https://localhost:2443/redfish/v1/Chassis/chassis/Thermal")
        time.sleep(10)
    
    page_text = driver.page_source.lower()
    assert "thermal" in page_text or "temperature" in page_text, "Thermal endpoint не доступен"

def test_power_control(driver):
    driver.get("https://localhost:2443")
    driver.find_element(By.ID, "username").send_keys("root")
    driver.find_element(By.ID, "password").send_keys("0penBmc") 
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(10)
    
    driver.get("https://localhost:2443/#/operations/server-power-operations")
    time.sleep(18)
    driver.find_element(By.XPATH, "//button[contains(text(), 'Power on')]").click()
    time.sleep(10)
    
    assert "on" in driver.page_source.lower(), "Питание не включилось"
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])