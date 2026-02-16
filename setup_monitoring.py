#!/usr/bin/env python3
import subprocess
import time
import sys
import os
import base64

# ==========================================
# ⚙️ CONFIGURACIÓN
# ==========================================
# Reutilizamos tu dominio y certificado
BASE_DOMAIN = "your-domain.com"
GRAFANA_DOMAIN = f"grafana.{BASE_DOMAIN}"
# Pega aquí TU ARN de certificado (el mismo de setup_sdk.py)
CERT_ARN = "arn:aws:acm:us-east-1:AWS_ACCOUNT_ID:certificate/7d3e39ec-99b3-45f4-b8cb-7681e3462a70"

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

def run_command(command, check=True):
    print(f"   > {command}")
    try:
        subprocess.run(command, shell=True, check=check)
    except subprocess.CalledProcessError:
        print(f"{Colors.RED}   ❌ El comando falló.{Colors.END}")
        if check:
            sys.exit(1)

def install_prometheus_stack():
    print(f"\n{Colors.GREEN}[1/3] Instalando Kube-Prometheus-Stack (Helm)...{Colors.END}")
    
    # 1. Agregar repositorio
    run_command("helm repo add prometheus-community https://prometheus-community.github.io/helm-charts")
    run_command("helm repo update")
    
    # 2. Crear namespace
    run_command("kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -")
    
    # 3. Instalar
    # Desactivamos la creación de Ingress por defecto del chart porque crearemos uno personalizado para AWS ALB
    cmd = """helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
      --namespace monitoring \
      --set grafana.adminPassword='admin' \
      --wait"""
    run_command(cmd)

def create_grafana_ingress():
    print(f"\n{Colors.GREEN}[2/3] Exponiendo Grafana con HTTPS (Ingress ALB)...{Colors.END}")
    
    # El servicio de Grafana suele llamarse "prometheus-grafana" en el puerto 80
    ingress_yaml = f"""
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  namespace: monitoring
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    external-dns.alpha.kubernetes.io/hostname: {GRAFANA_DOMAIN}
    alb.ingress.kubernetes.io/certificate-arn: {CERT_ARN}
    alb.ingress.kubernetes.io/listen-ports: '[{{"HTTP": 80}}, {{"HTTPS":443}}]'
    alb.ingress.kubernetes.io/actions.ssl-redirect: '{{"Type": "redirect", "RedirectConfig": {{ "Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}}}'
    # Importante para Grafana: Health Check
    alb.ingress.kubernetes.io/healthcheck-path: /login
    alb.ingress.kubernetes.io/success-codes: '200'
spec:
  rules:
    - host: {GRAFANA_DOMAIN}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: prometheus-grafana
                port:
                  number: 80
"""
    with open("grafana-ingress.yaml", "w") as f:
        f.write(ingress_yaml.strip())
        
    run_command("kubectl apply -f grafana-ingress.yaml")
    print(f"   📄 Ingress creado para: https://{GRAFANA_DOMAIN}")

def get_grafana_creds():
    print(f"\n{Colors.GREEN}[3/3] Obteniendo credenciales...{Colors.END}")
    # En este script forzamos la password a 'admin', pero es bueno saber cómo obtenerla si fuera aleatoria
    print(f"{Colors.YELLOW}   Usuario: admin{Colors.END}")
    print(f"{Colors.YELLOW}   Password: admin{Colors.END}")
    print("\n   ⚠️ Nota: Al entrar te pedirá cambiar la contraseña.")

def main():
    print(f"{Colors.BLUE}================================================={Colors.END}")
    print(f"{Colors.BLUE}   MONITORING SETUP (Prometheus & Grafana)       {Colors.END}")
    print(f"{Colors.BLUE}================================================={Colors.END}")
    
    install_prometheus_stack()
    create_grafana_ingress()
    get_grafana_creds()
    
    print(f"\n{Colors.BLUE}================================================={Colors.END}")
    print(f"{Colors.BLUE}   ✅ MONITORING ACTIVADO                        {Colors.END}")
    print(f"{Colors.BLUE}================================================={Colors.END}")
    print(f"Tu Dashboard estará listo en unos minutos en:")
    print(f"👉 https://{GRAFANA_DOMAIN}")
    print(f"\nUsa 'kubectl get ingress -n monitoring' para ver el estado del balanceador.")

if __name__ == "__main__":
    main()