
from gevent import monkey; monkey.patch_all()
from gevent import sleep
from gevent import signal as gsignal
import gevent
from gevent.subprocess import Popen, PIPE


from bottle import get, post, request,run,route,Bottle,template, static_file,response # or route
import os, re, subprocess,sys,signal
import splunklib.client as client
import splunklib.results as results
import urllib.parse



from bottle import get, post, request, response,redirect
from bottle import GeventServer, run
import time, gc
from pprint import pprint
import configargparse
import io


ui_subdir='ui'
UPLOAD_DIR='ui_tmp'

app = Bottle()

def merge_dicts(*args):
    result = {}
    for dictionary in args:
        result.update(dictionary)
    return result

my_module = os.path.abspath(__file__)
parent_dir = os.path.dirname(my_module)
jquery_ui_dir = os.path.join(parent_dir, ui_subdir,'static','jquery-ui-1.13.2.custom')
# print(static_dir)
static_dir = os.path.join(parent_dir, ui_subdir,'static')

# @app.route('/jquery-ui-1.13.2.custom/<filepath:path>')
# def server_jqui(filepath):
#     return static_file(filepath, root=jquery_ui_dir)

@app.route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=static_dir)

# @app.get('/login') # or @route('/login')
@app.route('/login', method='GET')
def login():
    return '''
        <form action="/login" method="post">
            Username: <input name="username" type="text" />
            Password: <input name="password" type="password" />
            <input value="Login" type="submit" />
        </form>
    '''



@app.route('/', method='GET')
def show_parameters():
    response.set_header("Cache-Control", "public, max-age=86400")
    stored_cookie_payload=request.cookies.get('payload')
    return template(ui_subdir+'/parameters',cookie_payload=stored_cookie_payload)

@app.route('/display_table', method='POST')
def generate_patameters():
    # return "Generated"
    # form = StateForm(request.form)
    # for k, v in request.forms.getall('value'):
    #     print(k, v)
    payload = merge_dicts(dict(request.forms), dict(request.query.decode()))
    # for k, v in payload.items():
        # print(k, v)
    # print(payload)
    return template(ui_subdir+'/disp_table', rows=payload)

@app.route('/config-file', method='POST')
def config_file_parameters():
    payload = merge_dicts(dict(request.forms), dict(request.query.decode()))
    response.set_cookie('payload', str(payload))
    return template(ui_subdir+'/config-file', rows=payload)
    
@app.route('/command-line', method='POST')
def command_line_parameters():
    payload = merge_dicts(dict(request.forms), dict(request.query.decode()))
    response.set_cookie('payload', str(payload))
    return template(ui_subdir+'/command-line', rows=payload)

@app.route('/splunk-connect', method='POST')
def splunk_connect():
    payload = merge_dicts(dict(request.forms), dict(request.query.decode()))

    # SPLUNK_HOST='localhost'
    # SPLUNK_PORT=8089
    # SPLUNK_AUTH_TOKEN='eyJraWQiOiJzcGx1bmsuc2VjcmV0IiwiYWxnIjoiSFM1MTIiLCJ2ZXIiOiJ2MiIsInR0eXAiOiJzdGF0aWMifQ.eyJpc3MiOiJhZG1pbiBmcm9tIEMwMkcyMzVCTUQ2UiIsInN1YiI6ImFkbWluIiwiYXVkIjoicHl0aG9uIHRlc3RzIiwiaWRwIjoiU3BsdW5rIiwianRpIjoiYWIyMzQ4M2FhYjk2OTA1ZGJmNGUwZTdlM2Y0OGI1MjE1ODcyOTUwM2ZmNjE0YjVjNzc5MWUyZWRlOGFkZjBhNSIsImlhdCI6MTY2Mzc4MDc3MiwiZXhwIjoxNzE1NjIwNzcyLCJuYnIiOjE2NjM3ODA3NzJ9.b0SRVIBCn3mEy3kXuE5BXyrNruW392Sch52QzWeCQ2n5NukW3dkT8FdH_YvQNwAr1DdP7JUROgdHdhCu2cT18A'
    output=''
    service={}

    try:

        # logging.info('connect-start')
        # logging.debug('SPLUNK_HOST: %s',options.SPLUNK_HOST)
        # logging.debug('SPLUNK_PORT: %s',options.SPLUNK_PORT)
        # logging.debug('SPLUNK_AUTH_TOKEN: %s',options.SPLUNK_AUTH_TOKEN)
        auth_token=payload['SPLUNK_AUTH_TOKEN']
        token_match=re.search("%.+%",auth_token)
        if token_match:
            # print(options.SPLUNK_AUTH_TOKEN)
            # print(auth_token)
            env_var=re.sub(r"%(.+)%","\\1",auth_token)
            # print(env_var)
            env_var_val=os.environ.get(env_var)
            # print(env_var_val)
            auth_token=env_var_val
        
        service = client.connect(
            host=payload['SPLUNK_HOST'],
            port=payload['SPLUNK_PORT'],
            splunkToken=auth_token,
            autologin=True)

        # logging.debug(service)
        # logging.info('connect-successful')
        # logging.info('connect-end')
        # assert isinstance(service, client.Service)
        # print(service.info('os_build'))
        # for key,value in service.info.items():
        #     print(key,value)
        # print('Success')
        # return service
        output='Success'
        # for key,value in service.info.items():
        #     print(key,value)
    except Exception as Argument:
        pass
        # logging.exception('Splunk Search Error')
        # print('Error:',Argument)
        # print(service)
        # output='Error'
        
    

    try:
        getattr(service, 'info')
        rows=service.info
        status="Success"
    # except AttributeError:
    except:
        # Do something
        rows=False
        status="Connection Test Failed"
        pass
    
    return template(ui_subdir+'/server_info', rows=rows,payload=payload,status=status)

    # return output


@app.route('/run-interactively', method='POST')
def run_interactively():
    payload = merge_dicts(dict(request.forms), dict(request.query.decode()))
    return template(ui_subdir+'/run-interactively', rows=payload)
    

@app.route('/run-script', methods=['GET', 'POST'])
def run_script():
    
    # payload = merge_dicts(dict(request.forms), dict(request.query.decode()))
    # return template(ui_subdir+'/run-interactively', rows=payload)
    print('yep')
    output =  '''
        % import subprocess
        % output=subprocess.run(["ls", "-l", "/dev/null"], capture_output=True)
        {{output}}
    '''
    return template(output)



@app.route('/stream1',methods=['GET', 'POST'])
def stream():
    yield 'START'
    sleep(3)
    yield 'MIDDLE'
    sleep(5)
    yield 'END'


global sub
@app.route('/stream',methods=['GET', 'POST'])
def stream():
    # "Using server-sent events"
    # https://developer.mozilla.org/en-US/docs/Server-sent_events/Using_server-sent_events
    # "Stream updates with server-sent events"
    # http://www.html5rocks.com/en/tutorials/eventsource/basics/

    payload = merge_dicts(dict(request.forms), dict(request.query.decode()))
    print(urllib.parse.unquote(payload["parameters"]))

    response.content_type  = 'text/event-stream'
    response.cache_control = 'no-cache'

    # Set client-side auto-reconnect timeout, ms.

    yield 'retry: 1000000\n\n'
    # try:
        # with subprocess.Popen(['/usr/bin/srun'] + argv[1:]) as cmd:
            # cmd.wait()
    
    # python3 splunk_export_parallel.py 
    exec_string="python3 splunk_export_parallel.py "+urllib.parse.unquote(payload["parameters"])
    # exec_string="python misc/logging-test.py"
    sub = Popen(exec_string, stdout=PIPE, stderr=subprocess.STDOUT, shell=True, preexec_fn=os.setsid)
    # sub = Popen('sleep 1; ping www.google.com -c 2; sleep 5; uname', stdout=PIPE, shell=True, preexec_fn=os.setsid)
    # global_process=sub
    while True:
        s = sub.stdout.readline()
        # gevent.sleep(1)
        # if s == "":
        # if s is  None:
        pprint(s)
        if len(s)==0:
            print("CLOSE")
            
            msg = 'event: end_session\ndata: {"message":"closing SSE"} \n\n'
            yield msg
            break
        else:
            # print(s.strip())
            n = s.strip()
            # print(n.decode())
            msg = "event: log\n"+'data: %s\n\n' % n.decode()
            # msg = 'event: foo \ndata: {"message":"bar"} \n\n'
            yield msg


    # print("CLOSE")
    # yield 'CLOSE:'
 
@app.route('/load-parameters-from-file', method='GET')
def load_parameters():
    # payload = merge_dicts(dict(request.forms), dict(request.query.decode()))
    # response.set_cookie('payload', str(payload))
    return template(ui_subdir+'/load-parameters-from-file')

@app.route('/process-uploaded-parameters', method='POST')
def process_parameter_file():
    """Handle file upload form"""
    # print('yep')
    import configparser
    # get the 'newfile' field from the form
    newfile = request.files.get('parameterFile')
    print(newfile.content_type)
    # only allow upload of text files
    # if newfile.content_type != 'text/plain':
    #     return "Only text files allowed"
    def create_output_dir(path_in):
        path_new=os.path.normpath(path_in)
        
        if not os.path.exists(path_new):
            os.makedirs(path_new)
    create_output_dir(UPLOAD_DIR)
    save_path = os.path.join(UPLOAD_DIR, newfile.filename)
    # newfile.save(save_path)

    # name = request.forms.name
    # data = request.files.data
    
    raw = newfile.file.read().decode() # This is dangerous for big files
    for line in io.StringIO(raw):
        print(line)
    
    # config = configparser.ConfigParser(allow_no_value=True)
    # self.config = ConfigParser.ConfigParser()
    # self.config.optionxform = str
    # from configparser import ConfigParser, ExtendedInterpolation
    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    config.optionxform = str
    config.read_string(raw)
    # print(config.sections())
    parameter_list=[]
    for each_section in config.sections():
        for (each_key, each_val) in config.items(each_section):
            print(each_key,each_val)
            val = re.sub(r'\s{0,}#.*', r'', each_val)
            parameter_list.append(each_key+'='+val)

    print(parameter_list)
    parameter_string='&'.join(parameter_list)
    print(parameter_string)
    parameter_string_encoded=urllib.parse.quote_plus(parameter_string)

    # filename = newfile.filename
    # return "Hello! You uploaded %s (%d bytes). <br /> <pre>%s</pre>" % (filename, len(raw), raw)

    # redirect to home page if it all works ok
    return redirect('/?'+parameter_string_encoded)



def shutdown(data, context):
    print('Shutting down ...')
    # server.stop(timeout=60)
    exit(signal.SIGTERM)
gsignal.signal(signal.SIGTERM, shutdown)
gsignal.signal(signal.SIGINT, shutdown) #CTRL C





# app.run(host='localhost', port=8080, debug=True,reloader=True)
try:
    app.run(host='localhost', server=GeventServer, port=8080, debug=True,reloader=True)
except KeyboardInterrupt:
    gsignal.signal(signal.SIGTERM, shutdown)
    gsignal.signal(signal.SIGINT, shutdown) #CTRL C
# if __name__ == '__main__':
    # run(server=GeventServer, port = 8081)