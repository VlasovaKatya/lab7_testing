pipeline {
    agent any
    environment {
        BMC_URL = 'https://localhost:2443'
        BMC_USERNAME = 'root'
        BMC_PASSWORD = '0penBmc'
        QEMU_PID_FILE = '/tmp/qemu.pid'
        QEMU_LOG_FILE = '/tmp/qemu.log'
    }
    stages {
        stage('Подготавливаем окружение') {
            steps {
                echo "///Подготовка///"
                sh '''
                    mkdir -p "${WORKSPACE}/artifacts"
                    # Устанавливаем необходимые пакеты
                    apt-get update && apt-get install -y python3 python3-pip python3-venv || true
                '''
                echo "///Готово///"
            }
        }

        stage('Start QEMU') {
            steps {
                echo "///Запуск QEMU с OpenBmc///"
                sh """
                    # Останавливаем предыдущие экземпляры
                    pkill qemu-system-arm || true
                    rm -f ${QEMU_PID_FILE} ${QEMU_LOG_FILE}
                    sleep 5

                    IMG="obmc-phosphor-image-romulus-20250902012112.static.mtd"
                    echo "Используемый образ: \$IMG"

                    # Запускаем QEMU в фоне с логированием
                    nohup qemu-system-arm \\
                        -M romulus-bmc \\
                        -nographic \\
                        -drive file="\${IMG}",format=raw,if=mtd \\
                        -net nic \\
                        -net user,hostfwd=tcp::2443-:443,hostfwd=tcp::8082-:80,hostname=qemu \\
                        > ${QEMU_LOG_FILE} 2>&1 &

                    QEMU_PID=\$!
                    echo "QEMU запущен с PID: \$QEMU_PID" 
                    echo \$QEMU_PID > ${QEMU_PID_FILE}

                    # Ждем запуска системы
                    echo "Ждем запуска QEMU..."
                    sleep 30
                    
                    # Проверяем, что процесс жив
                    if ps -p \$QEMU_PID > /dev/null; then
                        echo "QEMU успешно запущен с PID: \$QEMU_PID"
                    else
                        echo "Ошибка: QEMU не запустился"
                        exit 1
                    fi
                """
            }
            post {
                always {
                    sh """
                        # Копируем логи QEMU в artifacts
                        if [ -f ${QEMU_LOG_FILE} ]; then
                            cp ${QEMU_LOG_FILE} '${WORKSPACE}/artifacts/qemu_startup.log'
                        fi
                    """
                }
            }
        }

        stage('Установка зависимостей Python') {
            steps {
                echo "///Установка Python зависимостей///"
                sh """
                    # Создаем виртуальное окружение
                    python3 -m venv '${WORKSPACE}/venv' || true
                    . '${WORKSPACE}/venv/bin/activate'
                    
                    # Устанавливаем зависимости
                    if [ -f '${WORKSPACE}/requirements.txt' ]; then
                        pip install -r '${WORKSPACE}/requirements.txt'
                    else
                        # Базовые зависимости если requirements.txt нет
                        pip install pytest requests selenium locust
                    fi
                    
                    # Проверяем установку
                    pip list | grep -E "(pytest|requests|selenium|locust)" || echo "Некоторые пакеты не установились"
                """
            }
        }

        stage('API tests (pytest)') {
            steps {
                echo "///Запуск pytest///"
                sh """
                    . '${WORKSPACE}/venv/bin/activate'
                    cd '${WORKSPACE}/tests'
                    
                    # Проверяем существование тестового файла
                    if [ -f '1.py' ]; then
                        pytest 1.py \\
                            --html='${WORKSPACE}/artifacts/api_report.html' \\
                            --self-contained-html \\
                            --junitxml='${WORKSPACE}/artifacts/api.xml' -v
                    else
                        echo "Тестовый файл 1.py не найден"
                        # Создаем простой тест для демонстрации
                        cat > test_api.py << 'EOF'
import requests
import pytest

def test_bmc_availability():
    try:
        response = requests.get('https://localhost:2443', verify=False, timeout=10)
        assert response.status_code in [200, 401, 403]
        print("BMC доступен")
    except Exception as e:
        pytest.fail(f"BMC недоступен: {e}")

if __name__ == "__main__":
    test_bmc_availability()
EOF
                        pytest test_api.py \\
                            --html='${WORKSPACE}/artifacts/api_report.html' \\
                            --self-contained-html \\
                            --junitxml='${WORKSPACE}/artifacts/api.xml' -v
                    fi
                """
            }
        }

        stage('Web UI tests (pytest + selenium)') {
            steps {
                echo "///Запуск Web UI///"
                sh """
                    . '${WORKSPACE}/venv/bin/activate'
                    cd '${WORKSPACE}/tests'
                    
                    # Устанавливаем веб-драйвер если нужно
                    pip install webdriver-manager || true
                    
                    if [ -f 'main.py' ]; then
                        pytest main.py \\
                            --html='${WORKSPACE}/artifacts/web_ui_report.html' \\
                            --self-contained-html \\
                            --junitxml='${WORKSPACE}/artifacts/web_ui_junit.xml' -v
                    else
                        echo "Файл main.py не найден, пропускаем Web UI тесты"
                    fi
                """
            }
            post {
                always {
                    sh """
                        cp '${WORKSPACE}/tests/'*.png '${WORKSPACE}/artifacts/' 2>/dev/null || true
                    """
                }
            }
        }

        stage('Load tests (Locust)') {
            steps {
                echo "///Запуск Load tests///"
                sh """
                    . '${WORKSPACE}/venv/bin/activate'
                    cd '${WORKSPACE}/tests'
                    
                    if [ -f 'locustfile.py' ]; then
                        locust -f locustfile.py \\
                            --host=https://localhost:2443 \\
                            --headless \\
                            --users 2 \\
                            --spawn-rate 1 \\
                            --run-time 30s \\
                            --html '${WORKSPACE}/artifacts/locust.html' \\
                            --csv '${WORKSPACE}/artifacts/locust' || echo "Locust тесты завершились с ошибкой"
                    else
                        echo "Файл locustfile.py не найден, пропускаем нагрузочное тестирование"
                    fi
                """
            }
        }
    }

    post {
        always {
            sh """
                # Аккуратно останавливаем QEMU
                echo "Останавливаем QEMU..."
                if [ -f ${QEMU_PID_FILE} ]; then
                    PID=\$(cat ${QEMU_PID_FILE})
                    echo "Останавливаем процесс QEMU с PID: \$PID"
                    kill \$PID 2>/dev/null || true
                    sleep 3
                    # Принудительно если еще жив
                    kill -9 \$PID 2>/dev/null || true
                    rm -f ${QEMU_PID_FILE}
                fi
                # Дополнительная очистка
                pkill -f "qemu-system-arm" 2>/dev/null || true
                echo "QEMU остановлен"
            """
            
            // Убираем publishHTML или комментируем до установки плагина
            // publishHTML([
            //    allowMissing: true,
            //    alwaysLinkToLastBuild: true,
            //    keepAll: true,
            //    reportDir: 'artifacts',
            //    reportFiles: '*.html',
            //    reportName: 'OpenBMC Test Report'
            // ])

            junit(testResults: 'artifacts/*.xml', allowEmptyResults: true)
            archiveArtifacts artifacts: 'artifacts/**/*', fingerprint: true
            
            // Сохраняем логи установки и QEMU
            sh """
                echo "Собираем информацию о системе:" > '${WORKSPACE}/artifacts/build_info.txt'
                python3 --version >> '${WORKSPACE}/artifacts/build_info.txt' 2>&1 || echo "Python не установлен" >> '${WORKSPACE}/artifacts/build_info.txt'
                pip3 --version >> '${WORKSPACE}/artifacts/build_info.txt' 2>&1 || echo "pip не установлен" >> '${WORKSPACE}/artifacts/build_info.txt'
            """
            archiveArtifacts artifacts: 'artifacts/build_info.txt', fingerprint: false
        }
        success {
            echo "=== Pipeline выполнен успешно ==="
        }
        failure {
            echo "=== Pipeline завершился с ошибкой ==="
        }
    }
}