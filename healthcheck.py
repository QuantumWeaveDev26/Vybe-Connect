"""Container-local readiness check using the configured public Host boundary."""
import http.client
import os
from deployment import configuration


if __name__=='__main__':
    config=configuration();port=int(os.environ.get('TW_PORT','8788'));connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    try:
        connection.request('GET','/readyz',headers={'Host':config.authority if config.production else '127.0.0.1:'+str(port)});response=connection.getresponse();response.read();raise SystemExit(0 if response.status==200 else 1)
    finally:connection.close()
