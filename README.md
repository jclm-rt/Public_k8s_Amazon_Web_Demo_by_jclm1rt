🚀 EKS SRE Automation Demo: Amazon Web AppEste proyecto es una implementación integral de Site Reliability Engineering (SRE) para el despliegue de una aplicación web escalable en Amazon EKS. Automatiza desde el aprovisionamiento de infraestructura con Python hasta el monitoreo proactivo y el CI/CD con seguridad integrada.🏗️ Arquitectura del Sistema1. Workflow de Automatización (CI/CD)Este diagrama describe cómo el código viaja desde tu terminal hasta el clúster usando OIDC para una autenticación sin secretos.Fragmento de códigograph LR
    dev["👨‍💻 Desarrollador SRE"]
    slack["📢 Slack (Notificaciones)"]

    subgraph "Automatización & CI/CD"
        python_scripts["🐍 Python Scripts<br/>(setup_sdk.py / setup_monitoring.py)"]
        gh_actions["🚀 GitHub Actions<br/>(CI/CD Pipeline)"]
    end

    subgraph "AWS Identity & Access"
        iam["🔑 AWS IAM<br/>(OIDC & Roles)"]
        mapping["🏗️ Identity Mapping<br/>(RBAC Group: system:masters)"]
    end

    api_server["⚙️ K8s API Server"]

    dev -->|Ejecuta| python_scripts
    dev -->|Push Code| gh_actions
    python_scripts -->|Crea Clúster/Políticas| iam
    python_scripts -->|Instala Charts/App| api_server
    gh_actions -->|1. Auth OIDC| iam
    iam -->|2. Confía| mapping
    mapping -->|3. Permisos Admin| api_server
    gh_actions -->|4. kubectl apply| api_server
    gh_actions -->|5. Reporte| slack
2. Infraestructura en la NubeRepresentación de la alta disponibilidad mediante Pod Anti-Affinity distribuido en múltiples zonas de disponibilidad.Fragmento de códigograph TD
    user["🌐 Usuario Final"]
    route53["☁️ Route53 DNS<br/>(juliocesarlapaca.com)"]
    alb["⚖️ AWS Application<br/>Load Balancer"]
    acm["🔒 ACM (SSL Cert)"]

    subgraph "EKS Cluster Workload"
        ingress["🚪 Ingress ALB"]
        service["🔄 Service (NodePort)"]
        
        subgraph "Alta Disponibilidad (Anti-Affinity)"
            subgraph "Node A (AZ 1)"
                pod1["📦 Pod 1"]
                pod2["📦 Pod 2"]
                pod3["📦 Pod 3"]
            end
            subgraph "Node B (AZ 2)"
                pod4["📦 Pod 4"]
                pod5["📦 Pod 5"]
                pod6["📦 Pod 6"]
            end
        end
    end

    subgraph "Monitoring Stack"
        prom["📈 Prometheus"]
        grafana["📊 Grafana"]
    end

    user -->|HTTPS:443| route53
    route53 --> alb
    alb -- "Terminación SSL" --- acm
    alb --> ingress
    ingress --> service
    service -- "Balanceo HA" --> pod1 & pod2 & pod3 & pod4 & pod5 & pod6
    prom -. "Scrape Metrics" .-> pod1 & pod4
    grafana --> prom
🛠️ Tecnologías UtilizadasComponenteTecnologíaPropósitoCloud ProviderAWS (EKS v1.34)Orquestación de contenedores gestionada.Lenguaje ScriptingPython 3 (Boto3)Automatización de infraestructura y mapeo de identidades.IngressAWS Load Balancer ControllerCreación automática de ALB mediante anotaciones.DNSExternalDNSSincronización de dominios con Route53.MonitoreoPrometheus & GrafanaRecolección de métricas y visualización de salud.SeguridadKube-Linter & OIDCAnálisis estático y acceso seguro sin credenciales estáticas.🚀 Guía de Despliegue1. Preparación del ClústerEjecuta el script principal para crear el clúster, configurar las políticas IAM y habilitar el acceso para GitHub Actions:Bashpython3 setup_sdk.py
2. Configuración de MonitoreoInstala el stack de observabilidad y expón Grafana bajo un subdominio seguro:Bashpython3 setup_monitoring.py
3. Despliegue Continuo (CI/CD)Simplemente realiza un push a la rama main. El pipeline realizará las siguientes acciones:Seguridad: Ejecuta kube-linter sobre los manifiestos.Auth: Se autentica en AWS usando el GitHubActions-EKS-Role vía OIDC.Deploy: Aplica los cambios y espera el éxito del rollout.Notificar: Envía un reporte a Slack con los detalles de CPU/RAM consumidos.📊 Estrategia de SRE: Optimización y ResilienciaAnti-Affinity: Se implementó una regla de preferredDuringSchedulingIgnoredDuringExecution para asegurar que los 6 pods se distribuyan en diferentes nodos físicos, minimizando el radio de impacto ante fallos de hardware.Ajuste de Recursos (Fine-Tuning): Basado en análisis de métricas, se configuró un request de 50m CPU y 550Mi RAM. Esto maximiza la densidad del clúster sin comprometer la latencia de la aplicación.Seguridad No Bloqueante: El linter está configurado para permitir el avance del pipeline (continue-on-error: true) tras validar que la arquitectura de alta disponibilidad es correcta, ignorando advertencias menores de imágenes de terceros.📖 Glosario TécnicoOIDC (OpenID Connect): Protocolo para autenticación segura entre GitHub y AWS sin usar llaves secretas.IRSA: Asignación de permisos de AWS a niveles de Pod (Service Account).Identity Mapping: Mapeo del rol de IAM al grupo system:masters de Kubernetes para acceso administrativo.🔧 Comandos Útiles de SREBash# Verificar la distribución de Pods por Nodos (Validar Anti-Affinity)
kubectl get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName

# Ver logs de despliegue en tiempo real
kubectl rollout status deployment/amazon-deployment

# Revisar eventos del Balanceador (ALB)
kubectl describe ingress amazon-ingress-alb
