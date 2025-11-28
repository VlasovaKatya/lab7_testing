from locust import HttpUser, task, between
import json


class OpenBMCUser(HttpUser):

    host = "https://localhost:2443"
    wait_time = between(2, 5)

    def on_start(self):

        auth_response = self.client.post(
            "/redfish/v1/SessionService/Sessions",
            json={"UserName": "root", "Password": "0penBmc"},
            verify=False
        )

        if auth_response.status_code in [200, 201]:
            token = auth_response.headers.get("X-Auth-Token")
            if token:
                self.client.headers["X-Auth-Token"] = token
                print(f"Успешная аутентификация, токен получен")
            else:
                print("Ошибка: токен не получен")
        else:
            print(f"Ошибка аутентификации: {auth_response.status_code}")

    @task(3)
    def get_system_info(self):
        with self.client.get(
                "/redfish/v1/Systems/system",
                verify=False,
                catch_response=True,
                name="Get System Info"
        ) as response:
            if response.status_code == 200:
                try:
                    system_data = response.json()
                    if "Id" in system_data and "Status" in system_data:
                        response.success()
                    else:
                        response.failure("Неполные данные в ответе")
                except ValueError:
                    response.failure("Невалидный JSON в ответе")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def get_power_state(self):
        with self.client.get(
                "/redfish/v1/Systems/system",
                verify=False,
                catch_response=True,
                name="Get Power State"
        ) as response:
            if response.status_code == 200:
                try:
                    system_data = response.json()
                    power_state = system_data.get("PowerState")
                    if power_state:
                        response.success()
                        print(f"PowerState: {power_state}")
                    else:
                        response.failure("PowerState отсутствует в ответе")
                except ValueError:
                    response.failure("Невалидный JSON в ответе")
            else:
                response.failure(f"HTTP {response.status_code}")


class JSONPlaceholderUser(HttpUser):

    host = "https://jsonplaceholder.typicode.com"
    wait_time = between(1, 3)

    @task(4)
    def get_all_posts(self):
        with self.client.get(
                "/posts",
                catch_response=True,
                name="Get All Posts"
        ) as response:
            if response.status_code == 200:
                try:
                    posts = response.json()
                    if len(posts) > 0:
                        response.success()
                    else:
                        response.failure("Пустой список постов")
                except ValueError:
                    response.failure("Невалидный JSON в ответе")
            else:
                response.failure(f"HTTP {response.status_code}")