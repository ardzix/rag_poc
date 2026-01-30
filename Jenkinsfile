pipeline {
    agent any

    /*
      Jenkins CI/CD (Docker build + push + deploy to Docker Swarm)

      Notes:
      - This pipeline intentionally mirrors the working pattern from the reference project.
      - Update GIT_REPO, DOCKER_IMAGE, STACK_NAME, and VPS_HOST to match the actual repo and infra.
      - Required Jenkins credentials (suggested IDs; adjust to your Jenkins):
        - github-ardzix: Username/Password for GitHub clone
        - ard-dockerhub: DockerHub registry credentials
        - noc_rag-env: File credential for .env
        - sso_public_pem: File credential for public.pem
        - stag-arnatech-sa-01: SSH private key to VPS (root)
    */

    environment {
        DEPLOY = 'true'

        // Repo + image naming (edit as needed)
        GIT_REPO = 'github.com/ardzix/rag_poc.git'
        DOCKER_IMAGE = 'ardzix/noc_rag'
        DOCKER_REGISTRY_CREDENTIALS = 'ard-dockerhub'

        // Swarm deploy params
        STACK_NAME = 'noc_rag'
        REPLICAS = '1'
        NETWORK_NAME = 'development'

        // VPS target (edit as needed)
        VPS_HOST = '172.105.124.43'
    }

    stages {
        stage('Clean Workspace') {
            steps {
                sh '''
                    find . -mindepth 1 -maxdepth 1 ! -name 'Jenkinsfile' -exec rm -rf {} +
                '''
            }
        }

        stage('Checkout Code') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'github-ardzix', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_TOKEN')]) {
                    sh '''
                        mv Jenkinsfile ../Jenkinsfile.tmp
                        rm -rf ./*
                        rm -rf ./.??* || true
                        git clone https://${GIT_USER}:${GIT_TOKEN}@${GIT_REPO} .
                        mv ../Jenkinsfile.tmp Jenkinsfile
                    '''
                }
            }
        }

        stage('Inject Environment Variables and PEM Files') {
            steps {
                withCredentials([
                    file(credentialsId: 'noc_rag-env', variable: 'ENV_FILE'),
                    file(credentialsId: 'sso_public_pem', variable: 'PUBLIC_PEM_FILE')
                ]) {
                    sh """
                        cp \"${ENV_FILE}\" .env
                        cp \"${PUBLIC_PEM_FILE}\" public.pem
                    """
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("${DOCKER_IMAGE}:latest", ".")
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', DOCKER_REGISTRY_CREDENTIALS) {
                        docker.image("${DOCKER_IMAGE}:latest").push()
                    }
                }
            }
        }

        stage('Deploy to Swarm (VPS - uWSGI Only)') {
            when {
                expression { return env.DEPLOY?.toBoolean() ?: false }
            }
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: 'stag-arnatech-sa-01', keyFileVariable: 'SSH_KEY_FILE')
                ]) {
                    sh '''
                        echo "[INFO] Preparing VPS deployment..."
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no root@${VPS_HOST} "mkdir -p /root/${STACK_NAME}"

                        echo "[INFO] Copying .env and supervisord config to VPS..."
                        scp -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no .env root@${VPS_HOST}:/root/${STACK_NAME}/.env
                        scp -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no supervisord.conf root@${VPS_HOST}:/root/${STACK_NAME}/supervisord.conf

                        echo "[INFO] Deploying Docker service to Swarm..."
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no root@${VPS_HOST} bash -c '
                            docker swarm init || true
                            docker network create --driver overlay ${NETWORK_NAME} || true
                            docker service rm ${STACK_NAME} || true

                            docker service create --name ${STACK_NAME} \
                                --replicas ${REPLICAS} \
                                --network ${NETWORK_NAME} \
                                --env-file /root/${STACK_NAME}/.env \
                                --mount type=bind,src=/root/${STACK_NAME}/supervisord.conf,dst=/etc/supervisor/conf.d/supervisord.conf,ro=true \
                                ${DOCKER_IMAGE}:latest
                        '
                    '''
                }
            }
        }
    }

    post {
        always {
            echo 'Pipeline finished!'
        }
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
}

