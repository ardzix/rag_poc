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

        stage('Join Swarm + Deploy Service') {
          when {
            expression { return env.DEPLOY?.toBoolean() ?: false }
          }
          steps {
            withCredentials([
              sshUserPrivateKey(credentialsId: 'stag-arnatech-sa-01', keyFileVariable: 'SSH_KEY_FILE'),
              string(credentialsId: 'swarm-manager-addr', variable: 'SWARM_MANAGER_ADDR'),
              string(credentialsId: 'swarm-worker-join-token', variable: 'SWARM_WORKER_JOIN_TOKEN'),
              string(credentialsId: 'swarm-manager-join-token', variable: 'SWARM_MANAGER_JOIN_TOKEN')
            ]) {
              sh '''
                echo "[INFO] Preparing VPS deployment..."
                ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no root@${VPS_HOST} "mkdir -p /root/${STACK_NAME}"
        
                echo "[INFO] Copying .env and supervisord config to VPS..."
                scp -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no .env root@${VPS_HOST}:/root/${STACK_NAME}/.env
                scp -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no supervisord.conf root@${VPS_HOST}:/root/${STACK_NAME}/supervisord.conf
        
                echo "[INFO] Join swarm if needed + deploy (manager only)..."
                ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no root@${VPS_HOST} bash -s <<'REMOTE'
                set -euo pipefail
        
                STACK_NAME="${STACK_NAME}"
                REPLICAS="${REPLICAS}"
                NETWORK_NAME="${NETWORK_NAME}"
                DOCKER_IMAGE="${DOCKER_IMAGE}"
                SWARM_JOIN_AS="${SWARM_JOIN_AS:-worker}"
        
                SWARM_MANAGER_ADDR="${SWARM_MANAGER_ADDR}"
                SWARM_WORKER_JOIN_TOKEN="${SWARM_WORKER_JOIN_TOKEN}"
                SWARM_MANAGER_JOIN_TOKEN="${SWARM_MANAGER_JOIN_TOKEN}"
        
                echo "[INFO] Swarm local state: $(docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || echo 'unknown')"
        
                # 1) Join swarm if not active
                if [ "$(docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || echo 'inactive')" != "active" ]; then
                  echo "[INFO] Node not in swarm -> joining as ${SWARM_JOIN_AS} to ${SWARM_MANAGER_ADDR} ..."
        
                  if [ "$SWARM_JOIN_AS" = "manager" ]; then
                    if [ -z "$SWARM_MANAGER_JOIN_TOKEN" ]; then
                      echo "[ERROR] Missing SWARM_MANAGER_JOIN_TOKEN"
                      exit 1
                    fi
                    docker swarm join --token "$SWARM_MANAGER_JOIN_TOKEN" "$SWARM_MANAGER_ADDR"
                  else
                    if [ -z "$SWARM_WORKER_JOIN_TOKEN" ]; then
                      echo "[ERROR] Missing SWARM_WORKER_JOIN_TOKEN"
                      exit 1
                    fi
                    docker swarm join --token "$SWARM_WORKER_JOIN_TOKEN" "$SWARM_MANAGER_ADDR"
                  fi
                else
                  echo "[INFO] Node already part of a swarm. Skipping join."
                fi
        
                # 2) Deploy service ONLY if this node is a manager
                IS_MANAGER="$(docker info --format '{{.Swarm.ControlAvailable}}' 2>/dev/null || echo 'false')"
                echo "[INFO] Manager capability: ${IS_MANAGER}"
        
                if [ "$IS_MANAGER" != "true" ]; then
                  echo "[ERROR] This node is not a swarm manager. You cannot create/update services here."
                  echo "[HINT] Run the deploy stage against the swarm MANAGER node, or promote this node to manager."
                  exit 1
                fi
        
                # 3) Ensure overlay network exists (no create, only verify)
                if ! docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1; then
                  echo "[ERROR] Swarm network '${NETWORK_NAME}' not found on this manager."
                  echo "[HINT] Create it on the manager first: docker network create --driver overlay --attachable ${NETWORK_NAME}"
                  exit 1
                fi
        
                DRIVER="$(docker network inspect "${NETWORK_NAME}" --format '{{.Driver}}' || true)"
                SCOPE="$(docker network inspect "${NETWORK_NAME}" --format '{{.Scope}}' || true)"
                if [ "$DRIVER" != "overlay" ] || [ "$SCOPE" != "swarm" ]; then
                  echo "[ERROR] Network '${NETWORK_NAME}' exists but is not swarm overlay (driver=$DRIVER scope=$SCOPE)."
                  exit 1
                fi
        
                # 4) Recreate service (or you can update with service update)
                docker service inspect "${STACK_NAME}" >/dev/null 2>&1 && docker service rm "${STACK_NAME}" || true
        
                docker service create --name "${STACK_NAME}" \
                  --replicas "${REPLICAS}" \
                  --network "${NETWORK_NAME}" \
                  --env-file "/root/${STACK_NAME}/.env" \
                  --mount type=bind,src="/root/${STACK_NAME}/supervisord.conf",dst=/etc/supervisor/conf.d/supervisord.conf,ro=true \
                  "${DOCKER_IMAGE}:latest"
        
                echo "[INFO] Deploy done."
        REMOTE
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

