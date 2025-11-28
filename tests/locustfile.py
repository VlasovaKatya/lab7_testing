from locust import HttpUser, task, between
import urllib3
urllib3.disable_warnings() 

class OpenBMCUser(HttpUser):
    host = "https://localhost:2443"
    wait_time = between(2, 5)

    def on_start(self):
            auth_response = self.client.post(
                "/redfish/v1/SessionService/Sessions",
                json={"UserName": "root", "Password": "0penBmc"},
                verify=False,
            )
            if auth_response.status_code in [200, 201]:
                self.client.headers["X-Auth-Token"]  = auth_response.headers.get("X-Auth-Token")
            else:
                print(f"Ошибка аутентификации: {auth_response.status_code}")

    @task(3)
    def viewing_system_info(self):
        with self.client.get(
                "/redfish/v1/Systems/system",
                verify=False,
                catch_response=True,
                name="Get System Info"
        ) as response:
            if response.status_code == 200:
                    system_data = response.json()
                    if "Id" in system_data and "Status" in system_data:
                        response.success()
                    else:
                        response.failure("Ошибка")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def power_state(self):
        with self.client.get(
                "/redfish/v1/Chassis/chassis",
                verify=False,
                catch_response=True,
                name="Get PowerState"
        ) as response:
            if response.status_code == 200:
                    chassis_data = response.json()
                    if "PowerState" in chassis_data:
                        response.success()
                    else:
                        response.failure("Ошибка")
            else:
                response.failure(f"HTTP {response.status_code}")

