# 🚀 EKS SRE Automation Demo: Amazon Web App

Este proyecto es una implementación profesional de **Site Reliability Engineering (SRE)** diseñada para desplegar una aplicación web escalable y de alta disponibilidad en **Amazon EKS**. Automatiza todo el ciclo de vida: desde el aprovisionamiento de infraestructura con Python hasta el monitoreo proactivo y el CI/CD con seguridad integrada.

---

## 🏗️ Arquitectura del Sistema

### 1. Workflow de Automatización (CI/CD)
Este flujo describe cómo el código viaja desde el desarrollo hasta el clúster usando **OIDC** para una autenticación segura sin necesidad de llaves de acceso estáticas.

```mermaid
graph LR
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
    gh_actions -- "1. Auth OIDC" --> iam
    iam -- "2. Confía" --> mapping
    mapping -- "3. Permisos Admin" --> api_server
    gh_actions -- "4. kubectl apply" --> api_server
    gh_actions -- "5. Reporte" --> slack
```

### 2. Infraestructura de Alta Disponibilidad
Muestra la distribución de la carga de trabajo. Se implementó Pod Anti-Affinity para forzar la distribución de las 6 réplicas entre diferentes nodos físicos, evitando puntos únicos de fallo.

```mermaid
graph TD
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

    user -- "HTTPS:443" --> route53
    route53 --> alb
    alb -- "Terminación SSL" --- acm
    alb --> ingress
    ingress --> service
    service -- "Balanceo HA" --> pod1 & pod2 & pod3 & pod4 & pod5 & pod6
    prom -. "Scrape Metrics" .-> pod1 & pod4
    grafana --> prom
```
### 3. Diagrama de arquitectura EKS

![Diagrama de Arquitectura EKS](diagrama_eks_amazon_web_demo.png)

---

## 🛠️ Tecnologías y Herramientas

| Componente | Tecnología | Propósito |
| --- | --- | --- |
| **Nube** | Amazon EKS (K8s v1.34) | Orquestación de contenedores |
| **IaC** | Python 3 + Boto3 | Automatización de infraestructura y permisos IAM |
| **Ingress** | AWS Load Balancer Controller | Gestión dinámica de ALBs en AWS |
| **DNS** | ExternalDNS | Sincronización automática con Route53 |
| **Monitoreo** | Prometheus & Grafana | Observabilidad y Dashboards de métricas |
| **CI/CD** | GitHub Actions | Pipeline con seguridad OIDC y Linting |

---

## 🚀 Guía de Inicio Rápido
### 1. Despliegue de Infraestructura Base
Ejecuta el script principal para crear el clúster, las políticas IAM y el identity mapping RBAC necesario para el pipeline:
   ```bash
   python3 setup_sdk.py
   ```
### 2. Configuración del Stack de Monitoreo
Instala Prometheus y expón Grafana bajo un subdominio seguro (HTTPS):
   ```bash
   python3 setup_monitoring.py
   ```
### 3. Automatización de Despliegue (CI/CD)
Cada push a main activa el pipeline que valida el manifiesto amazon-generated.yaml, extrae los límites de recursos y realiza el despliegue informando a Slack.


---

## 📊 Estrategia de Ingeniería de Fiabilidad (SRE)
* **Resiliencia con Anti-Affinity:** Se configuró una regla de podAntiAffinity para asegurar que las réplicas no compartan el mismo nodo, protegiendo la aplicación ante la caída de un servidor físico.

* **Fine-Tuning de Recursos:** Tras analizar el consumo real (~515Mi RAM y <1m CPU), se definieron reservas estables de 50m CPU y 550Mi RAM para optimizar el coste sin sacrificar estabilidad.

* **Seguridad y Acceso:** Se eliminó el uso de credenciales de larga duración mediante OIDC y se habilitó un escaneo de seguridad (Linting) no bloqueante para auditoría continua.

---

## 📖 Glosario Técnico
* **OIDC (OpenID Connect):** Protocolo para que GitHub Actions asuma roles de AWS de forma temporal y segura.

* **IRSA:** Asignación de permisos de AWS (IAM) directamente a cuentas de servicio de Kubernetes.

* **Identity Mapping:** Configuración en EKS para otorgar permisos administrativos al rol de GitHub Actions.

* **Pod Anti-Affinity:** Regla que distribuye pods en diferentes nodos para alta disponibilidad.

---
 
## 🔧 Comandos de Operación SRE
```bash
# Validar distribución de pods entre nodos (Anti-Affinity Check)
kubectl get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName

# Monitorear logs de despliegue
kubectl rollout status deployment/amazon-deployment

# Verificar estado de registros DNS automáticos
kubectl logs -f deployment/external-dns
```


