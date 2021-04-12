#!/usr/bin/env python3
# prometheus import

from prometheus_api_client import PrometheusConnect


class my_prometheus():
    def __init__(self, host, port, disablessl):
        if disablessl == True:
            self.schema = "http"
        else:
            self.schema = "https"
        try:
            self.prom = PrometheusConnect(url = self.schema + "://" + host + ":" + port, disable_ssl=disablessl)
        except Exception:
            print("Fehler")
    
    def prom_query(self, query):
        self.lasttemps = self.prom.custom_query(query=query)
        self.lasttemp = sorted(self.lasttemps[0]["values"], reverse=True)[0][1]
