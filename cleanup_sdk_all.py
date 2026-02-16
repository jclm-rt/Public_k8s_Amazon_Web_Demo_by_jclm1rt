#!/usr/bin/env python3
import boto3
import subprocess
import time
import sys
from botocore.exceptions import ClientError

# ==========================================
# CONFIGURACIÓN
# ==========================================
CLUSTER_NAME = "cluster-sre-demo"
REGION = "us-east-1"
POLICIES_TO_DELETE = [
    "AllowExternalDNSUpdates",
    "AWSLoadBalancerControllerIAMPolicy"
]

# Inicializar clientes de Boto3
iam_client = boto3.client('iam', region_name=REGION)
sts_client = boto3.client('sts', region_name=REGION)

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def run_command(command, ignore_errors=True):
    print(f"   > Ejecutando: {command}")
    try:
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        if ignore_errors:
            print(f"     {Colors.YELLOW}(Ignorado) El recurso no existía o falló.{Colors.END}")
        else:
            print(f"     {Colors.RED}Error crítico.{Colors.END}")
            sys.exit(1)

def delete_iam_policy(policy_name, account_id):
    """Borra una política IAM usando Boto3 (Maneja versiones y detach)."""
    arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
    print(f"   > Buscando política: {policy_name}")
    
    try:
        # 1. Listar versiones de la política
        versions = iam_client.list_policy_versions(PolicyArn=arn)['Versions']
        
        # 2. Borrar versiones no predeterminadas
        for v in versions:
            if not v['IsDefaultVersion']:
                print(f"     - Borrando versión antigua: {v['VersionId']}")
                iam_client.delete_policy_version(PolicyArn=arn, VersionId=v['VersionId'])
        
        # 3. Borrar la política
        iam_client.delete_policy(PolicyArn=arn)
        print(f"     {Colors.GREEN}✔ Política eliminada correctamente.{Colors.END}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"     {Colors.YELLOW}(Ignorado) La política no existe.{Colors.END}")
        elif e.response['Error']['Code'] == 'DeleteConflict':
            print(f"     {Colors.RED}⚠ No se pudo borrar. Aún está adjunta a algún Rol.{Colors.END}")
        else:
            print(f"     {Colors.RED}Error AWS: {e}{Colors.END}")

def main():
    print(f"{Colors.BLUE}================================================={Colors.END}")
    print(f"{Colors.BLUE}   CLEANUP SCRIPT (AWS SDK + MONITORING)         {Colors.END}")
    print(f"{Colors.BLUE}================================================={Colors.END}")
    
    # Validar identidad con Boto3
    try:
        identity = sts_client.get_caller_identity()
        account_id = identity['Account']
        print(f"🔑 AWS Account ID: {Colors.GREEN}{account_id}{Colors.END}")
        print(f"🌎 Región:        {Colors.GREEN}{REGION}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error conectando con AWS. Revisa tus credenciales.{Colors.END}")
        sys.exit(1)

    confirm = input(f"\n¿Borrar clúster {Colors.YELLOW}{CLUSTER_NAME}{Colors.END} y TODOS sus recursos (App + Monitoreo)? (si/no): ")
    if confirm.lower() != "si":
        sys.exit(0)

    # ---------------------------------------------------------
    # PASO 1: Recursos Kubernetes (Ingress/ALB) - CRÍTICO
    # ---------------------------------------------------------
    print(f"\n{Colors.BLUE}[1/4] Eliminando Ingress para liberar Balanceadores (ALBs)...{Colors.END}")
    
    # 1. App Principal
    print("   - Limpiando App Amazon...")
    run_command("kubectl delete ingress amazon-ingress-alb --ignore-not-found=true")
    run_command("kubectl delete service amazon-service-alb --ignore-not-found=true")
    run_command("kubectl delete deployment amazon-deployment --ignore-not-found=true")
    
    # 2. Monitoreo (Grafana) - NUEVO
    print("   - Limpiando Stack de Monitoreo...")
    # Esto borra el ALB de Grafana
    run_command("kubectl delete ingress grafana-ingress -n monitoring --ignore-not-found=true")
    # Esto borra el servicio LoadBalancer si existiera alguno extra
    run_command("kubectl delete service prometheus-grafana -n monitoring --ignore-not-found=true")

    print(f"{Colors.YELLOW}⏳ Esperando 30s para que AWS elimine los balanceadores físicos...{Colors.END}")
    # Damos un poco más de tiempo porque ahora son 2 balanceadores
    time.sleep(30)

    # ---------------------------------------------------------
    # PASO 2: Helm y Namespaces
    # ---------------------------------------------------------
    print(f"\n{Colors.BLUE}[2/4] Desinstalando Helm Charts y Namespaces...{Colors.END}")
    
    # Controladores Base
    run_command("helm uninstall external-dns -n default")
    run_command("helm uninstall aws-load-balancer-controller -n kube-system")
    
    # Stack Prometeus - NUEVO
    run_command("helm uninstall prometheus -n monitoring")
    # Borramos el namespace completo para asegurar limpieza
    run_command("kubectl delete namespace monitoring --ignore-not-found=true")

    # Service Accounts (IRSA)
    print("   - Borrando IAM Service Accounts...")
    run_command(f"eksctl delete iamserviceaccount --name external-dns --cluster {CLUSTER_NAME} --namespace default")
    run_command(f"eksctl delete iamserviceaccount --name aws-load-balancer-controller --cluster {CLUSTER_NAME} --namespace kube-system")

    # ---------------------------------------------------------
    # PASO 3: Clúster EKS
    # ---------------------------------------------------------
    print(f"\n{Colors.BLUE}[3/4] Destruyendo Clúster EKS (eksctl)...{Colors.END}")
    try:
        subprocess.run(f"eksctl delete cluster --name {CLUSTER_NAME} --region {REGION}", shell=True, check=True)
    except subprocess.CalledProcessError:
        print(f"{Colors.RED}Error borrando el clúster. Puede que ya no exista.{Colors.END}")

    # ---------------------------------------------------------
    # PASO 4: Políticas IAM (Puro Boto3)
    # ---------------------------------------------------------
    print(f"\n{Colors.BLUE}[4/4] Limpiando Políticas IAM huérfanas...{Colors.END}")
    for policy in POLICIES_TO_DELETE:
        delete_iam_policy(policy, account_id)

    print(f"\n{Colors.GREEN}✨ Limpieza TOTAL completada exitosamente. ✨{Colors.END}")

if __name__ == "__main__":
    main()