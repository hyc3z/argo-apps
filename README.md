# ArgoCD K8s 部署指南

## 一、环境准备

### 1. 安装 Helm
```bash
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
```

### 2. 安装 Ingress-Nginx

卸载 k3s 自带的 Traefik（避免冲突）：
```bash
helm uninstall traefik -n kube-system
```

使用 Helm 安装（NodePort 模式，适用于腾讯云轻量服务器）：
```bash
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.nodePorts.http=80 \
  --set controller.service.nodePorts.https=443
```

### 3. 安装 Cert-Manager

```bash
helm repo add jetstack https://charts.jetstack.io --force-update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.19.1 \
  --set crds.enabled=true
```

创建 ClusterIssuer（记得修改邮箱地址）：
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    email: your-email@example.com  # 修改为你的邮箱
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
    - http01:
        ingress:
          ingressClassName: nginx
```

调试命令：
```bash
kubectl get Issuers,ClusterIssuers,Certificates,CertificateRequests,Orders,Challenges --all-namespaces
```

## 二、配置 ArgoCD

### 1. 创建 GitHub PAT Token
进入 GitHub：`Settings` → `Developer settings` → `Personal access tokens`

### 2. 在 K8s 中创建 Secret
```bash
kubectl create secret generic github-token -n argocd --from-literal=token=你的PAT
```

### 3. 更新 applicationset.yaml
根据实际情况修改配置文件

### 4. 创建 ArgoCD 应用
```bash
argocd app create bubba-root \
  --repo https://github.com/hyc3z/argo-apps.git \
  --path . \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace argocd \
  --directory-recurse \
  --sync-policy automated \
  --auto-prune --self-heal
```

## 三、项目配置要点

### K8s 配置文件生成
可以让 AI 助手生成：
```
I want to create /k8s files for this project so that my argo-cd service can detect and auto deploy.
```

### 关键配置注意事项

1. **命名空间**：每个应用使用独立的 namespace，避免 ArgoCD 冲突
2. **证书自动签发**：在 Ingress 中添加 `cert-manager.io/cluster-issuer: "letsencrypt-prod"`
3. **ArgoCD 管理标签**：在 kustomization 中添加 `managed-by: argocd`
4. **同步方式**：使用 HTTPS 而非 SSH
5. **URL 参数保留**：如需保留 URL 参数，移除 Ingress 中的 rewrite-target
6. **健康检查**：谨慎使用 `startupProbe`、`livenessProbe`、`readinessProbe`，确保服务已实现

### API CORS 配置示例
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "*"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
```

### 镜像版本管理
避免使用 `latest` 标签，推荐使用语义化版本（semver）：
- 问题：ArgoCD 检测到 Git 变更触发更新，但 CI 构建镜像尚未完成
- 解决：使用 precommit hook / CI pipeline / ArgoCD Image Updater 自动更新版本号

## 四、常见问题

### 部署问题
- **endpoints NONE**：Service 无法匹配 Pod，检查 label selector
- **证书签发失败**：检查 ClusterIssuer 中的邮箱是否为真实邮箱（不能用 example.com）
- **版本卡住不更新**：检查 CI pipeline 是否构建失败

### ArgoCD 会话过期
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
argocd login localhost:8080 --username admin \
  --password $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d) \
  --insecure
```

### 查看 Pod 日志
查看上一次运行的错误日志：
```bash
kubectl logs <pod-name> --previous
```

## 五、测试环境配置

### 生成自签名证书
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=api.example.com"

kubectl create secret tls api-tls --key tls.key --cert tls.crt
```

### 使用 Let's Encrypt Staging 环境
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    email: your-email@example.com
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-staging-account-key
    solvers:
    - http01:
        ingress:
          ingressClassName: nginx
```