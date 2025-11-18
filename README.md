1. New PAT token

Go to `Settings` -> `Developer settings` -> `Personal access tokens`

2. Generate github token in k8s

```
kubectl create secret generic github-token -n argocd --from-literal=token=YourPAT
```

3. Update applicationset.yaml

4. Create argocd app

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

5. Update /k8s file in projects

Tell cursor/kiro to generate 

```
I want to create /k8s files for this project so that my argo-cd service can detect and auto deploy.
```

TIPS:

- Github only supports list repo by organization for now.
- User https instead of ssh to sync
- Remove rewrite target in Ingress/Nginx config if you want to keep parameters in url
- If you have `endpoints NONE` issue, means service can't match any pods. Check k8s files generated.
