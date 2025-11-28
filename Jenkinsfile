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

        stage('Подготавливаем окружение') {
            steps {
                echo "///Подготовка///"
                sh 'mkdir -p ${WORKSPACE}/artifacts'
                echo "///Готово///"
            }
        }

        stage('Start QEMU') {
            steps {
                echo "///Запуск QEMU с 0penBmc///"
                sh '''
                    pkill qemu-system-arm || true
                    rm -f /tmp/qemu.pid
                    sleep 5

                    IMG="obmc-phosphor-image-romulus-20250902012112.static.mtd"
                    echo "Используемый образ: $IMG"

                    nohup qemu-system-arm \
                        -M romulus-bmc \
                        -nographic \
                        -drive file="$IMG",format=raw,if=mtd \
                        -net nic \
                        -net user,hostfwd=tcp::2443-:443,hostfwd=tcp::8082-:80,hostname=qemu \
                        > /tmp/qemu.log 2>&1 &

                    QEMU_PID=$!
                    echo "QEMU запущен с PID: $QEMU_PID" && echo $QEMU_PID > /tmp/qemu.pid

                    sleep 10
                '''
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

        stage('API tests (pytest)') {
            steps {
                echo "///Запуск pytest///"
                sh '''
                    cd ${WORKSPACE}/tests
                    pip3 install -r ${WORKSPACE}/requirements.txt --break-system-packages || true
                    pytest 1.py \
                        --html=artifacts/api_report.html \
                        --self-contained-html \
                        --junitxml=artifacts/api.xml -v
                '''
            }
        }

        stage('Web UI tests (pytest + selenium)') {
            steps {
                echo "///Запуск Web UI///"
                sh '''
                    cd ${WORKSPACE}/tests
                    pip3 install -r ${WORKSPACE}/requirements.txt --break-system-packages || true
                    pytest main.py \
                        --html=${WORKSPACE}/artifacts/web_ui_report.html \
                        --self-contained-html \
                        --junitxml=${WORKSPACE}/artifacts/web_ui_junit.xml -v
                '''
            }
            post {
                always {
                    sh 'cp ${WORKSPACE}/tests/*.png ${WORKSPACE}/artifacts/ || true'
                }
            }
        }

        stage('Load tests (Locust)') {
            steps {
                sh '''
                    cd ${WORKSPACE}/tests
                    pip3 install -r ${WORKSPACE}/requirements.txt --break-system-packages || true
                    locust -f locustfile.py \
                        --host=https://localhost:2443 \
                        --headless \
                        --users 5 \
                        --spawn-rate 1 \
                        --run-time 30s \
                        --html artifacts/locust.html \
                        --csv artifacts/locust || true
                '''
            }
        }
    }

    post {
        always {
            sh '''
                if [ -f /tmp/qemu.pid ]; then
                    kill $(cat /tmp/qemu.pid) || true
                fi
                pkill qemu-system-arm || true
            '''
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'artifacts',
                reportFiles: 'test_summary.md',
                reportName: 'OpenBMC Test Report'
            ])

            junit 'artifacts/*.xml', allowEmptyResults: true
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