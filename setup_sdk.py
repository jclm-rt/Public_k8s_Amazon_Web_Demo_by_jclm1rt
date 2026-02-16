#!/usr/bin/env python3
import boto3
import subprocess
import time
import sys
import json
import os

# ==========================================
# ⚙️ CONFIGURACIÓN DEL PROYECTO
# ==========================================
CLUSTER_NAME = "cluster-sre-demo"
REGION = "us-east-1"
DOMAIN_NAME = "amazon-web-demo.your-domain.com" # Tu dominio
# Pega aquí tu ARN del certificado
CERT_ARN = "arn:aws:acm:us-east-1:AWS_ACCOUNT_ID:certificate/7d3e39ec-99b3-45f4-b8cb-7681e3462a70"

# Versiones
K8S_VERSION = "1.34"
LBC_VERSION = "v2.7.2" # Versión base para descargar la política

# Clientes Boto3
eks_client = boto3.client('eks', region_name=REGION)
iam_client = boto3.client('iam', region_name=REGION)
sts_client = boto3.client('sts', region_name=REGION)

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

def get_account_id():
    return sts_client.get_caller_identity()['Account']

def get_vpc_id():
    """Obtiene la VPC ID del clúster creado para configurar el Load Balancer."""
    try:
        response = eks_client.describe_cluster(name=CLUSTER_NAME)
        return response['cluster']['resourcesVpcConfig']['vpcId']
    except Exception as e:
        print(f"{Colors.RED}Error obteniendo VPC ID: {e}{Colors.END}")
        sys.exit(1)

def create_external_dns_policy(account_id):
    """Crea la política IAM para ExternalDNS dinámicamente."""
    policy_name = "AllowExternalDNSUpdates"
    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
    
    # Definición JSON de la política
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["route53:ChangeResourceRecordSets"],
                "Resource": "arn:aws:route53:::hostedzone/*"
            },
            {
                "Effect": "Allow",
                "Action": ["route53:ListHostedZones", "route53:ListResourceRecordSets"],
                "Resource": "*"
            }
        ]
    }
    
    print(f"   🔍 Verificando política {policy_name}...")
    try:
        iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_doc)
        )
        print(f"   ✅ Política creada: {policy_name}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"   ⚠️ La política ya existe. Usando la existente.")
    return policy_arn

def create_alb_policy():
    """Descarga y crea la política para AWS Load Balancer Controller."""
    policy_name = "AWSLoadBalancerControllerIAMPolicy"
    url = "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json"
    
    print(f"   📥 Descargando política oficial IAM para ALB...")
    run_command(f"curl -o iam_policy.json {url}")
    
    print(f"   🔍 Creando/Actualizando política {policy_name} en AWS...")
    # Usamos subprocess aquí para facilitar el uso del archivo descargado
    cmd = f"aws iam create-policy --policy-name {policy_name} --policy-document file://iam_policy.json"
    run_command(cmd, check=False) # Si falla porque existe, no importa
    
    # Limpieza
    if os.path.exists("iam_policy.json"):
        os.remove("iam_policy.json")
    
    account_id = get_account_id()
    return f"arn:aws:iam::{account_id}:policy/{policy_name}"

def generate_app_yaml():
    """Genera el archivo YAML de la aplicación con las variables correctas."""
    yaml_content = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: amazon-deployment
spec:
  replicas: 4
    matchLabels:
      app: amazon-app
  template:
    metadata:
      labels:
        app: amazon-app
    spec:
      # --- ESTO SOLUCIONA EL ERROR DE ANTIAFFINITY DEL LINTER---
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - amazon-app
              topologyKey: "kubernetes.io/hostname"
      # -------------------------------
      containers:
        - name: amazon-container
          image: ooghenekaro/amazon:3
          ports:
            - containerPort: 3000
          # --- OPTIMIZACIÓN SRE ---
          resources:
            requests:
              # Memoria: Basado en tu evidencia de Grafana (~515Mi)
              memory: "550Mi"
              # CPU: Bajamos de 250m a 50m porque tu consumo real es ~0.4m
              # 50m es suficiente para arrancar y estar en reposo sin desperdiciar el nodo.
              cpu: "50m"
            limits:
              # Si hay un memory leak, lo matamos antes de que afecte al nodo
              memory: "750Mi"
              # Damos espacio (burst) de hasta 1/4 de núcleo para cargas rápidas
              cpu: "250m"
          # -------------------------
---
apiVersion: v1
kind: Service
metadata:
  name: amazon-service-alb
spec:
  type: NodePort
  ports:
    - port: 80
      targetPort: 3000
  selector:
    app: amazon-app
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: amazon-ingress-alb
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: instance
    external-dns.alpha.kubernetes.io/hostname: {DOMAIN_NAME}
    alb.ingress.kubernetes.io/certificate-arn: {CERT_ARN}
    alb.ingress.kubernetes.io/listen-ports: '[{{"HTTP": 80}}, {{"HTTPS":443}}]'
    alb.ingress.kubernetes.io/actions.ssl-redirect: '{{"Type": "redirect", "RedirectConfig": {{ "Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}}}'
spec:
  rules:
    - host: {DOMAIN_NAME}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: amazon-service-alb
                port:
                  number: 80
"""
    with open("amazon-generated.yaml", "w") as f:
        f.write(yaml_content.strip())
    print(f"   📄 Archivo 'amazon-generated.yaml' creado con éxito y regenerado con RECURSOS OPTIMIZADOS (CPU Eficiente).")

def main():
    print(f"{Colors.BLUE}================================================={Colors.END}")
    print(f"{Colors.BLUE}   SETUP SCRIPT (AWS EKS AUTOMATION)             {Colors.END}")
    print(f"{Colors.BLUE}================================================={Colors.END}")
    
    account_id = get_account_id()
    print(f"🆔 Cuenta AWS: {account_id}")
    print(f"🌎 Región: {REGION}")
    
    # ---------------------------------------------------------
    # PASO 1: Crear Clúster
    # ---------------------------------------------------------
    print(f"\n{Colors.GREEN}[1/5] Creando Clúster EKS (Esto tardará ~15 mins)...{Colors.END}")
    # Verificamos si ya existe para ahorrar tiempo
    try:
        eks_client.describe_cluster(name=CLUSTER_NAME)
        print(f"   ⚠️ El clúster {CLUSTER_NAME} ya existe. Saltando creación.")
    except:
        cmd_cluster = f"""eksctl create cluster \
        --name {CLUSTER_NAME} \
        --region {REGION} \
        --version {K8S_VERSION} \
        --nodegroup-name standard-nodes \
        --node-type t3.medium \
        --nodes 2 \
        --with-oidc"""
        run_command(cmd_cluster)

    vpc_id = get_vpc_id()
    print(f"   🌐 VPC ID detectada: {vpc_id}")

    # ---------------------------------------------------------
    # PASO 2: Políticas IAM
    # ---------------------------------------------------------
    print(f"\n{Colors.GREEN}[2/5] Configurando Políticas IAM...{Colors.END}")
    dns_policy_arn = create_external_dns_policy(account_id)
    alb_policy_arn = create_alb_policy()

    # ---------------------------------------------------------
    # PASO 3: Service Accounts (IRSA)
    # ---------------------------------------------------------
    print(f"\n{Colors.GREEN}[3/5] Creando Service Accounts (IRSA)...{Colors.END}")
    
    # ExternalDNS SA
    cmd_sa_dns = f"""eksctl create iamserviceaccount \
      --name external-dns \
      --namespace default \
      --cluster {CLUSTER_NAME} \
      --attach-policy-arn {dns_policy_arn} \
      --approve --override-existing-serviceaccounts"""
    run_command(cmd_sa_dns)

    # ALB Controller SA
    cmd_sa_alb = f"""eksctl create iamserviceaccount \
      --name aws-load-balancer-controller \
      --namespace kube-system \
      --cluster {CLUSTER_NAME} \
      --attach-policy-arn {alb_policy_arn} \
      --approve --override-existing-serviceaccounts"""
    run_command(cmd_sa_alb)

    # ---------------------------------------------------------
    # PASO 4: Instalación Helm Charts
    # ---------------------------------------------------------
    print(f"\n{Colors.GREEN}[4/5] Instalando Controladores (Helm)...{Colors.END}")
    
    # Repositorios
    run_command("helm repo add eks https://aws.github.io/eks-charts")
    run_command("helm repo add bitnami https://charts.bitnami.com/bitnami")
    run_command("helm repo update")

    # ExternalDNS
    print("   ➤ Instalando ExternalDNS...")
    # Nota: Usamos registro ECR público para evitar rate limits
    cmd_helm_dns = f"""helm upgrade --install external-dns oci://registry-1.docker.io/bitnamicharts/external-dns \
      --set provider=aws \
      --set aws.zoneType=public \
      --set txtOwnerId={CLUSTER_NAME} \
      --set domainFilters[0]=your-domain.com \
      --set serviceAccount.create=false \
      --set serviceAccount.name=external-dns \
      --set image.registry=public.ecr.aws \
      --set image.repository=bitnami/external-dns \
      --set image.tag=latest \
      --set global.security.allowInsecureImages=true \
      --set logLevel=debug \
      --wait"""
    run_command(cmd_helm_dns)

    # ALB Controller
    print("   ➤ Instalando AWS Load Balancer Controller...")
    cmd_helm_alb = f"""helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
      -n kube-system \
      --set clusterName={CLUSTER_NAME} \
      --set serviceAccount.create=false \
      --set serviceAccount.name=aws-load-balancer-controller \
      --set region={REGION} \
      --set vpcId={vpc_id} \
      --wait"""
    run_command(cmd_helm_alb)

    # ---------------------------------------------------------
    # PASO 5: Despliegue de la App
    # ---------------------------------------------------------
    print(f"\n{Colors.GREEN}[5/5] Desplegando Aplicación Web...{Colors.END}")
    generate_app_yaml()
    run_command("kubectl apply -f amazon-generated.yaml")
    
    print(f"\n{Colors.BLUE}================================================={Colors.END}")
    print(f"{Colors.BLUE}   ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE        {Colors.END}")
    print(f"{Colors.BLUE}================================================={Colors.END}")
    print(f"Tu web estará disponible en unos minutos en: https://{DOMAIN_NAME}")
    print(f"Puedes monitorear el progreso con: kubectl get ingress")

if __name__ == "__main__":
    main()