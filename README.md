### Prerequisites:

- k3s
- helm
```
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
```

- ingress-nginx

Note : **don't** use apply -f to install, if you do please uninstall using same yaml:
```
kubectl delete -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.13.4/deploy/static/provider/cloud/deploy.yaml
```

k3s default comes with `Traefik` and may conflict, need uninstall:
```
helm uninstall traefik -n kube-system
```

Install with helm

这里用LoadBalancer类型也行，但是因为我用的是腾讯云轻量服务器，不提供端口映射。

```
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.nodePorts.http=80 \
  --set controller.service.nodePorts.https=443
```

- Let's encrypt
```
# Add the Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io --force-update

# Install the cert-manager helm chart
helm install \
  cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.19.1 \
  --set crds.enabled=true
```

Install cluster issuer
Remember to change email below in yaml, otherwise issuer will fail.

```
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    # You must replace this email address with your own.
    # Let's Encrypt will use this to contact you about expiring
    # certificates, and issues related to your account.
    email: user@example.com
    # If the ACME server supports profiles, you can specify the profile name here.
    # See #acme-certificate-profiles below.
    profile: tlsserver
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      # Secret resource that will be used to store the account's private key.
      # This is your identity with your ACME provider. Any secret name may be
      # chosen. It will be populated with data automatically, so generally
      # nothing further needs to be done with the secret. If you lose this
      # identity/secret, you will be able to generate a new one and generate
      # certificates for any/all domains managed using your previous account,
      # but you will be unable to revoke any certificates generated using that
      # previous account.
      name: letsencrypt-prod-account-key
    # Add a single challenge solver, HTTP01 using nginx
    solvers:
    - http01:
        ingress:
          ingressClassName: nginx
```

To debug, use
```
kubectl get Issuers,ClusterIssuers,Certificates,CertificateRequests,Orders,Challenges --all-namespaces
```

### 1. New PAT token

Go to `Settings` -> `Developer settings` -> `Personal access tokens`

### 2. Generate github token in k8s

```
kubectl create secret generic github-token -n argocd --from-literal=token=YourPAT
```

### 3. Update applicationset.yaml

### 4. Create argocd app

```
argocd app create bubba-root \
  --repo https://github.com/hyc3z/argo-apps.git \
  --path . \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace argocd \
  --directory-recurse \
  --sync-policy automated \
  --auto-prune --self-heal
```

### 5. Update /k8s file in projects

Tell cursor/kiro to generate 

```
I want to create /k8s files for this project so that my argo-cd service can detect and auto deploy.
```

### TIPS for step #5:

- Github only supports list repo by organization for now.
- User https instead of ssh to sync
- Remove rewrite target in Ingress/Nginx config if you want to keep parameters in url
- remember to add `cert-manager.io/cluster-issuer: "letsencrypt-prod"` to auto get cert. Let's encrypt supports `staging` cert for testing purpose, not trusted by browsers.
- remember to add `managed-by: argocd` in kustomization so that argocd has control to resources created.
- For ingress controller for api, need to configure cors. Example:
```
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lovetest-api
  namespace: lovetest
  labels:
    app: lovetest-api
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    # CORS配置
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "*"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization"
    nginx.ingress.kubernetes.io/cors-expose-headers: "Content-Length,Content-Range"
    nginx.ingress.kubernetes.io/cors-allow-credentials: "true"
    nginx.ingress.kubernetes.io/cors-max-age: "86400"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.lovetest.com.cn
    secretName: lovetest-api-tls
  rules:
  - host: api.lovetest.com.cn
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: lovetest-api
            port:
              number: 80

```

### Overall FAQ:

- If you have `endpoints NONE` issue, means service can't match any pods. Check k8s files generated.
- Failed to register ACME account: 400 urn:ietf:params:acme:error:invalidContact: Error validating contact(s) :: contact email has forbidden domain "example.com" means you need to change your email to real email in issuer config
- ArcoCD session expired:
```
{"level":"fatal","msg":"rpc error: code = Unauthenticated desc = invalid session: token has invalid claims: token is expired","time":"2025-11-20T09:18:18+08:00"}
```

login again with below command:
```
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
argocd login localhost:8080 --username admin --password $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d) --insecure
```
- If version is stuck, check CI pipeline first to see if build fails. (Notification?)
- For pod logs, add `--previous` after `kubectl logs ...` to see last run errors.

### For test only:

- generate tls keys
```
# 生成自签名证书（仅用于测试）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=api.lovetest.com.cn"

# 创建 TLS secret
kubectl create secret tls lovetest-api-tls \
  --key tls.key \
  --cert tls.crt

# After generate keys, can delete source .key/.crt files
```

- staging issuer
Install cluster issuer

```
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    # You must replace this email address with your own.
    # Let's Encrypt will use this to contact you about expiring
    # certificates, and issues related to your account.
    email: user@example.com
    # If the ACME server supports profiles, you can specify the profile name here.
    # See #acme-certificate-profiles below.
    profile: tlsserver
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      # Secret resource that will be used to store the account's private key.
      # This is your identity with your ACME provider. Any secret name may be
      # chosen. It will be populated with data automatically, so generally
      # nothing further needs to be done with the secret. If you lose this
      # identity/secret, you will be able to generate a new one and generate
      # certificates for any/all domains managed using your previous account,
      # but you will be unable to revoke any certificates generated using that
      # previous account.
      name: example-issuer-account-key
    # Add a single challenge solver, HTTP01 using nginx
    solvers:
    - http01:
        ingress:
          ingressClassName: nginx
```