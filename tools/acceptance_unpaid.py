"""Run isolated local service contracts with external network access blocked."""
import argparse,concurrent.futures,json,os,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CHILD=r'''
import io,json,socket,sys,unittest
blocked=0
original_connect=socket.socket.connect
original_connect_ex=socket.socket.connect_ex
original_lookup=socket.getaddrinfo
def local(host):return host in ('localhost','127.0.0.1','::1','0.0.0.0',None)
def connect(sock,address):
 global blocked
 if sock.family in (socket.AF_INET,socket.AF_INET6) and not local(address[0]):
  blocked+=1;raise OSError('External network is disabled during unpaid acceptance')
 return original_connect(sock,address)
def connect_ex(sock,address):
 global blocked
 if sock.family in (socket.AF_INET,socket.AF_INET6) and not local(address[0]):
  blocked+=1;raise OSError('External network is disabled during unpaid acceptance')
 return original_connect_ex(sock,address)
def lookup(host,*args,**kwargs):
 global blocked
 if not local(host):
  blocked+=1;raise OSError('External network is disabled during unpaid acceptance')
 return original_lookup(host,*args,**kwargs)
socket.socket.connect=connect;socket.socket.connect_ex=connect_ex;socket.getaddrinfo=lookup
suite=unittest.defaultTestLoader.discover('tests',pattern=sys.argv[1])
log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=1).run(suite)
print(json.dumps({'module':sys.argv[1],'tests':result.testsRun,'skipped':len(result.skipped),'passed':result.wasSuccessful(),'external_attempts_blocked':blocked,'failure_output':log.getvalue() if not result.wasSuccessful() else ''}))
sys.exit(0 if result.wasSuccessful() else 1)
'''

def run(path):
    # Never inherit real provider configuration into tests.
    env={key:value for key,value in os.environ.items() if not key.startswith(('TW_','OPENAI_','META_','RAZORPAY_','SHIPROCKET_','GOOGLE_','SMTP_'))}
    env['PYTHONUTF8']='1'
    result=subprocess.run([sys.executable,'-B','-c',CHILD,path.name],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
    try:value=json.loads(result.stdout.splitlines()[-1])
    except (ValueError,IndexError):value={'module':path.name,'tests':0,'passed':False,'failure_output':result.stderr[-5000:]}
    if result.returncode:value['passed']=False
    return value

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path);parser.add_argument('--workers',type=int,choices=range(1,5),default=4)
    args=parser.parse_args()
    # This separate, manually invoked live script is deliberately never imported.
    paths=[p for p in sorted((ROOT/'tests').glob('test_*.py')) if p.name!='test_live_deployment.py']
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(run,paths):
            results.append(result)
            print(json.dumps({key:result.get(key) for key in ('module','tests','passed')}),flush=True)
    report={'external_network':'blocked','paid_requests_submitted':0,'live_provider_acceptance':False,'tests':sum(r['tests'] for r in results),'skipped':sum(r.get('skipped',0) for r in results),'passed':all(r['passed'] for r in results),'results':results}
    if args.output:args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='results'}))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
