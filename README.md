# Description
Tis is a fork from [zabbix-kubernetes-monitoring](https://github.com/sleepka/zabbix-kubernetes-monitoring), it is zabbix-agent script and template for zabbix server. It is used for Kubernetes monitoring by Zabbix. Easy to deploy and configure. Auto discovery of pods, deployments, services, etc.

# Installation
1. Copy [kubernetes-stats.py](https://raw.githubusercontent.com/EduardCloud/zabbix-kubernetes-monitoring/master/kubernetes-stats.py) to /usr/lib/zabbix/externalscripts/. Remind to give execute permission to the file: ``chown zabbix kubernetes-stats.py && chmod 770 kubernetes-stats.py``
2. Import Zabbix template ([Kubernetes-Template.xml](https://raw.githubusercontent.com/EduardCloud/zabbix-kubernetes-monitoring/master/Kubernetes-Template.xml)) to Zabbix server.
3. Create zabbix user in Kubernetes (can use [zabbix-user-example.yml](https://raw.githubusercontent.com/EduardCloud/zabbix-kubernetes-monitoring/master/zabbix-user.yml)).
4. Set the token and API server url in [kubernetes-clusters.json](https://raw.githubusercontent.com/EduardCloud/zabbix-kubernetes-monitoring/master/kubernetes-clusters.json) and left the file in /usr/lib/zabbix/externalscripts/ for multi cluster feature.
5. Apply template to host, and set the Macros as your needs:
``{$CLUSTER_NAME}``: Cluster name
``{$POD_FILTER}``: Filter discovery by pod name (optional)

## How to create zabbix user in Kubernetes
```bash
$ kubectl apply -n kube-system -f zabbix-user.yml 
serviceaccount/zabbix-user created
clusterrole.rbac.authorization.k8s.io/zabbix-user created
clusterrolebinding.rbac.authorization.k8s.io/zabbix-user created
```

## How to retrieve TOKEN and API SERVER
1. **TOKEN**:
```bash
$ TOKENNAME=$(kubectl get sa/zabbix-user -n kube-system -o jsonpath='{.secrets[0].name}')
$ TOKEN=$(kubectl -n kube-system get secret $TOKENNAME -o jsonpath='{.data.token}'| base64 --decode)
$ echo $TOKEN
```
2. **API SERVER**:
```bash
$ APISERVER=https://$(kubectl -n default get endpoints kubernetes --no-headers | awk '{ print $2 }')
$ echo $APISERVER
```
