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

Tell cursor/kiro

