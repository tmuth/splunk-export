import gevent
from gevent.subprocess import Popen, PIPE

def cron():
    while True:
        print("cron")
        gevent.sleep(0.5)

# g = gevent.spawn(cron)
def subp():
    sub = Popen('sleep 1; ping www.google.com -c 2; sleep 5; uname', stdout=PIPE, shell=True)
    while True:
        s = sub.stdout.readline()
        # if s == "":
        # if s is  None:
        if len(s)==0:
            break
        else:
            print(s.strip())
            print(len(s))
    # g.kill()
subp()