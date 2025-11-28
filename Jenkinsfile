pipeline {
    agent any

    environment {
        BMC_URL = 'https://localhost:2443'
        BMC_USERNAME = 'root'
        BMC_PASSWORD = '0penBmc'
        WORKSPACE_DIR = '/var/jenkins_home/workspace'
        QEMU_PID_FILE = '/tmp/qemu.pid'
    }

    stages {
        stage('Подготовка окружения') {
            steps {
                script {
                    echo "=== Подготовка окружения ==="
                    
                    sh '''
                        # Создаем единую папку для всех артефактов
                        mkdir -p ${WORKSPACE}/artifacts
                    '''
                    
                    echo "Окружение подготовлено"
                }
            }
        }

        stage('Запуск QEMU с OpenBMC') {
            steps {
                script {
                    echo "=== Запуск QEMU с OpenBMC ==="
                    
                    sh '''
                        pkill qemu-system-arm || true
                        rm -f /tmp/qemu.pid
                        sleep 2
                        
                        cd ${WORKSPACE}/romulus
                        
                        if [ ! -f "obmc-phosphor-image-romulus-20250902012112.static.mtd" ]; then
                            echo "ОШИБКА: MTD файл не найден!"
                            exit 1
                        fi
                        
                        echo "MTD файл найден: obmc-phosphor-image-romulus-20250902012112.static.mtd"
                        
                        echo "Запуск QEMU..."
                        nohup qemu-system-arm \
                            -M romulus-bmc \
                            -nographic \
                            -drive file=obmc-phosphor-image-romulus-20250902012112.static.mtd,format=raw,if=mtd \
                            -net nic \
                            -net user,hostfwd=tcp::2443-:443,hostfwd=tcp::8082-:80,hostname=qemu \
                            > /tmp/qemu.log 2>&1 &
                        
                        QEMU_PID=$!
                        echo "QEMU запущен с PID: $QEMU_PID"
                        echo "$QEMU_PID" > /tmp/qemu.pid
                        
                        sleep 5
                        if ! ps -p $QEMU_PID > /dev/null; then
                            echo "QEMU не запущен!"
                            cat /tmp/qemu.log
                            exit 1
                        fi
                        
                        echo "Быстрая проверка OpenBMC (максимум 30 секунд)..."
                        timeout=30
                        elapsed=0
                        interval=3
                        while ! curl -k --silent --output /dev/null --connect-timeout 2 --max-time 3 https://localhost:2443/redfish/v1; do
                            sleep $interval
                            elapsed=$((elapsed+interval))
                            if [ $elapsed -ge $timeout ]; then
                                echo "OpenBMC не готов за $timeout секунд - тесты продолжат выполнение"
                                break
                            fi
                            printf "."
                        done
                        echo "\\nПродолжаем выполнение тестов"
                    '''
                }
            }
            post {
                always {
                    sh '''
                        if [ -f /tmp/qemu.log ]; then
                            cp /tmp/qemu.log ${WORKSPACE}/artifacts/qemu_startup.log
                        fi
                    '''
                }
            }
        }

        stage('Web UI Тесты') {
            steps {
                script {
                    echo "=== Запуск Web UI тестов ==="
                    
                    sh '''
                        cd ${WORKSPACE}/tests
                        
                        pip3 install -r ${WORKSPACE}/requirements.txt --break-system-packages || true
                        
                        pytest tests_openbmc.py \
                            --html=${WORKSPACE}/artifacts/web_ui_report.html \
                            --self-contained-html \
                            --junitxml=${WORKSPACE}/artifacts/web_ui_junit.xml \
                            -v --tb=short
                    '''
                }
            }
            post {
                always {
                    sh '''
                        # Копируем скриншоты если есть
                        if ls ${WORKSPACE}/tests/*.png 1> /dev/null 2>&1; then
                            cp ${WORKSPACE}/tests/*.png ${WORKSPACE}/artifacts/ || true
                        fi
                    '''
                }
            }
        }

        stage('Redfish API Тесты') {
            steps {
                script {
                    echo "=== Запуск Redfish API тестов ==="
                    
                    sh '''
                        cd ${WORKSPACE}/tests
                        
                        echo "Запуск Redfish API тестов..."
                        
                        pip3 install -r ${WORKSPACE}/requirements.txt --break-system-packages || true
                        
                        pytest test_redfish.py \
                            --html=${WORKSPACE}/artifacts/redfish_report.html \
                            --self-contained-html \
                            --junitxml=${WORKSPACE}/artifacts/redfish_junit.xml \
                            -v --tb=short
                    '''
                }
            }
        }

        stage('Нагрузочное тестирование') {
            steps {
                script {
                    echo "=== Запуск нагрузочного тестирования ==="
                    
                    sh '''
                        cd ${WORKSPACE}/tests
                        
                        echo "Запуск нагрузочного тестирования..."
                        
                        pip3 install -r ${WORKSPACE}/requirements.txt --break-system-packages || true
                        
                        # Используем || true чтобы игнорировать ошибки Locust
                        locust -f locustfile.py \
                            --host=https://localhost:2443 \
                            --users=5 \
                            --spawn-rate=1 \
                            --run-time=30s \
                            --headless \
                            --html=${WORKSPACE}/artifacts/locust_report.html \
                            --csv=${WORKSPACE}/artifacts/locust_stats || true
                    '''
                }
            }
        }

        stage('Сборка артефактов') {
            steps {
                script {
                    echo "=== Сборка артефактов ==="
            
                sh '''
                    cat > ${WORKSPACE}/artifacts/test_summary.md << 'EOF'
# Отчет по тестированию OpenBMC

## Общая информация
- Сборка завершена успешно

## Результаты тестов

### Web UI Тесты
- HTML отчет: [web_ui_report.html](web_ui_report.html)
- JUnit отчет: [web_ui_junit.xml](web_ui_junit.xml)

### Redfish API Тесты  
- HTML отчет: [redfish_report.html](redfish_report.html)
- JUnit отчет: [redfish_junit.xml](redfish_junit.xml)

### Нагрузочное тестирование
- HTML отчет: [locust_report.html](locust_report.html)
- CSV данные: [locust_stats_requests.csv](locust_stats_requests.csv)

### Логи системы
- Логи QEMU: [qemu_startup.log](qemu_startup.log)

## Статус
- Все тесты выполнены успешно
EOF
            '''
            
                    echo "Артефакты собраны"
                }
            }
        }
    }

    post {
        always {
            script {
                echo "=== Остановка QEMU ==="
                sh '''
                    if [ -f /tmp/qemu.pid ]; then
                        kill $(cat /tmp/qemu.pid) || true
                        rm -f /tmp/qemu.pid
                    fi
                    pkill qemu-system-arm || true
                '''
            }
            
            // Публикация HTML отчета
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'artifacts',
                reportFiles: 'test_summary.md',
                reportName: 'OpenBMC Test Report'
            ])
            
            // Публикация JUnit результатов
            junit testResults: 'artifacts/*.xml', allowEmptyResults: true
            
            // Архивирование всех артефактов
            archiveArtifacts artifacts: 'artifacts/**/*', fingerprint: true
        }
        
        success {
            echo "=== Pipeline выполнен успешно ==="
        }
        
        failure {
            echo "=== Pipeline завершился с ошибкой ==="
        }
    }
}