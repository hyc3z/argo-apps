1. New PAT token

Go to `Settings` -> `Developer settings` -> `Personal access tokens`

2. Generate github token in k8s

```
kubectl create secret generic github-token -n argocd --from-literal=token=YourPAT
```

3. Update 