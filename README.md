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
