# 🚀 AWS EKS Automation Demo

Este proyecto automatiza el despliegue de una aplicación de E-Commerce en AWS EKS utilizando **Python (Boto3)**. Implementa infraestructura como código para gestionar clústers, balanceadores de carga, DNS y certificados SSL.

## 🛠️ Tecnologías
* **Lenguaje:** Python 3 (Boto3 SDK)
* **Cloud:** AWS (EKS, IAM, Route53, ACM, ALB)
* **Kubernetes:** Helm, Ingress, Deployments, Services
* **Observabilidad:** Prometheus & Grafana

## 📂 Estructura del Proyecto
* `setup_sdk.py`: Script idempotente que levanta toda la infraestructura (Clúster, Políticas IAM, Helm Charts y App).
* `cleanup_sdk_all.py`: Script de "Cierre Ordenado" que elimina recursos lógicos y físicos para evitar costos.
* `setup_monitoring.py`: Despliegue automatizado del stack de monitoreo (Kube-Prometheus-Stack).

## ⚡ Quick Start
1. Configurar credenciales de AWS CLI.
2. Ejecutar instalación:
   ```bash
   python3 setup_sdk.py

## 📊 Arquitectura
El proyecto implementa Ingress Controllers para crear automáticamente Balanceadores de Carga (ALB) y registros DNS en Route53.
