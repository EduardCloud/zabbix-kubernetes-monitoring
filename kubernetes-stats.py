#!/usr/bin/env python
"""
.SYNOPSIS
  This script discovers and check Kubernetes services.
.NOTES
  Version:          1.0
  Author:           sleepka - https://github.com/sleepka/zabbix-kubernetes-monitoring
  Purpose/Change:   Multi cluster & remove zabbix agent user parameters:
                    https://github.com/EduardCloud/zabbix-kubernetes-monitoring
  Updates:          Eduard / Add Api url and token user collection from json file.
  Needs:            * It's a must create a serviceacount with some grants, you can see here (added pod/logs
                      rights):
                    https://github.com/EduardCloud/zabbix-kubernetes-monitoring/blob/master/zabbix-user.yml
                    $ kubectl apply -n kube-system -f zabbix-user.yml
                    * To retrieve the cluster/s data we need to create the file kubernetes-clusters.json in
                     /usr/lib/zabbix/externalscripts/kubernetes-clusters.json:
                    {
                    "cluster1": {
                        "api_url": "https://API_SERVER_IP:PORT",
                        "access_token": "<ACCESS_TOKEN>"
                        }
                    }
"""
# -------------------------------------------------[Initialisations]--------------------------------------------------
import subprocess
import sys
import os
import json
import time

# Needs for azure-fix to ignore selfsigned ssl cert
import ssl

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

# ---------------------------------------------------[Declarations]----------------------------------------------------

with open("/usr/lib/zabbix/externalscripts/kubernetes-clusters.json") as f:
    config_file = json.load(f)

# print(config_file)
cluster = sys.argv[1]
api_server = config_file[cluster]["api_url"]
token = config_file[cluster]["access_token"]

targets = ["pods", "nodes", "containers", "deployments", "apiservices", "componentstatuses"]
target = "pods" if "containers" == sys.argv[3] else sys.argv[3]

if sys.argv[2] == "discovery":
    if "pods" == target:
        api_req = "/api/v1/" + target

elif sys.argv[2] == "stats":
    if "pods" == target and "PodLogs" not in sys.argv[6]:
        api_req = "/api/v1/" + target
    elif "pods" == target and "PodLogs" in sys.argv[6]:
        api_req = "/api/v1/namespaces/" + sys.argv[4] + "/pods/" + sys.argv[5] + "/log"

if "nodes" == target or "componentstatuses" == target:
    api_req = "/api/v1/" + target
elif "deployments" == target:
    api_req = "/apis/apps/v1/" + target
elif "apiservices" == target:
    api_req = "/apis/apiregistration.k8s.io/v1/" + target

# -----------------------------------------------------[Functions]------------------------------------------------------
def rawdata(qtime=30):
    if sys.argv[3] in targets:
        tmp_file = "/tmp/zbx-" + cluster + "-" + target + ".tmp"
        tmp_file_exists = True if os.path.isfile(tmp_file) else False
        if tmp_file_exists and (time.time() - os.path.getmtime(tmp_file)) <= qtime:
            file = open(tmp_file, "r")
            rawdata = file.read()
            file.close()
        else:
            # azure-fix to ignore selfsigned ssl cert
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib2.Request(api_server + api_req)
            req.add_header("Authorization", "Bearer " + token)
            # Use context with no ssl check for selfsigned certs
            rawdata = urllib2.urlopen(req, context=ctx).read()

            file = open(tmp_file, "wb")
            file.write(rawdata)
            file.close()
            if not tmp_file_exists:
                os.chmod(tmp_file, 0o666)
        return rawdata
    else:
        return False


def PodLogs():
    # azure-fix to ignore selfsigned ssl cert
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib2.Request(api_server + api_req)
    req.add_header("Authorization", "Bearer " + token)
    # Use context with no ssl check for selfsigned certs
    rawdata = urllib2.urlopen(req, context=ctx).read()
    # textdata = rawdata.text
    output = rawdata.decode("utf-8")
    return output


# -----------------------------------------------------[Execution]------------------------------------------------------
if sys.argv[3] in targets:
    # Discovery
    if "discovery" == sys.argv[2]:
        result = {"data": []}
        data = json.loads(rawdata())

        for item in data["items"]:
            if "nodes" == sys.argv[3] or "componentstatuses" == sys.argv[3] or "apiservices" == sys.argv[3]:
                result["data"].append({"{#NAME}": item["metadata"]["name"]})

            elif "containers" == sys.argv[3]:
                # Add containers filter by pod name macro {$POD_FILTER}
                if len(sys.argv) > 4 and len(sys.argv[4]) > 0:
                    ContainersFilter = sys.argv[4].split(",")
                else:
                    ContainersFilter = False
                if ContainersFilter:
                    for ContainerFilter in ContainersFilter:
                        for cont in item["spec"]["containers"]:
                            if ContainerFilter in item["metadata"]["name"]:
                                result["data"].append(
                                    {
                                        "{#NAME}": item["metadata"]["name"],
                                        "{#NAMESPACE}": item["metadata"]["namespace"],
                                        "{#CONTAINER}": cont["name"],
                                    }
                                )
                else:
                    for cont in item["spec"]["containers"]:
                        result["data"].append(
                            {
                                "{#NAME}": item["metadata"]["name"],
                                "{#NAMESPACE}": item["metadata"]["namespace"],
                                "{#CONTAINER}": cont["name"],
                            }
                        )

            elif "pods" == sys.argv[3]:
                # Add discovery pod filter by pod name macro {$POD_FILTER}
                if len(sys.argv) > 4 and len(sys.argv[4]) > 0:
                    PodsFilter = sys.argv[4].split(",")
                else:
                    PodsFilter = False
                if PodsFilter:
                    for PodFilter in PodsFilter:
                        if PodFilter in item["metadata"]["name"]:
                            result["data"].append(
                                {"{#NAME}": item["metadata"]["name"], "{#NAMESPACE}": item["metadata"]["namespace"]}
                            )
                else:
                    result["data"].append(
                        {"{#NAME}": item["metadata"]["name"], "{#NAMESPACE}": item["metadata"]["namespace"]}
                    )
            else:
                result["data"].append(
                    {"{#NAME}": item["metadata"]["name"], "{#NAMESPACE}": item["metadata"]["namespace"]}
                )

        print(json.dumps(result))

    # Stats
    elif "stats" == sys.argv[2]:

        # data = json.loads(rawdata(100))
        if "nodes" == sys.argv[3] or "apiservices" == sys.argv[3]:
            data = json.loads(rawdata(100))
            for item in data["items"]:
                if item["metadata"]["name"] == sys.argv[4]:
                    for status in item["status"]["conditions"]:
                        if status["type"] == sys.argv[5]:
                            print(status["status"])
                            break

        elif "componentstatuses" == sys.argv[3]:
            data = json.loads(rawdata(100))
            for item in data["items"]:
                if item["metadata"]["name"] == sys.argv[4]:
                    for status in item["conditions"]:
                        if status["type"] == sys.argv[5]:
                            print(status["status"])
                            break

        elif "PodLogs" not in sys.argv[6] and "pods" == sys.argv[3] or "deployments" == sys.argv[3]:
            data = json.loads(rawdata(100))
            for item in data["items"]:
                if item["metadata"]["namespace"] == sys.argv[4] and item["metadata"]["name"] == sys.argv[5]:
                    if "statusPhase" == sys.argv[6]:
                        print(item["status"]["phase"])
                    elif "statusPod" == sys.argv[6]:
                        for status in item["status"]["containerStatuses"]:
                            print(json.dumps(status["state"]))
                    elif "statusReason" == sys.argv[6]:
                        if "reason" in item["status"]:
                            print(item["status"]["reason"])
                    elif "statusReady" == sys.argv[6]:
                        for status in item["status"]["conditions"]:
                            if status["type"] == "Ready" or (
                                status["type"] == "Available" and "deployments" == sys.argv[3]
                            ):
                                print(status["status"])
                                break
                    elif "containerReady" == sys.argv[6]:
                        for status in item["status"]["containerStatuses"]:
                            if status["name"] == sys.argv[7]:
                                for state in status["state"]:
                                    if state == "terminated":
                                        if status["state"]["terminated"]["reason"] == "Completed":
                                            print("True")
                                            break
                                else:
                                    print(status["ready"])
                                    break
                    elif "containerRestarts" == sys.argv[6]:
                        for status in item["status"]["containerStatuses"]:
                            if status["name"] == sys.argv[7]:
                                print(status["restartCount"])
                                break
                    elif "Replicas" == sys.argv[6]:
                        print(item["spec"]["replicas"])
                    elif "updatedReplicas" == sys.argv[6]:
                        print(item["status"]["updatedReplicas"])
                    break

        elif "pods" == sys.argv[3] and "PodLogs" in sys.argv[6]:
            data = PodLogs()
            print(data)
