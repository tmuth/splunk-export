from bottle import get, post, request,run,route,Bottle,template, static_file,response # or route
import os, re
import splunklib.client as client
import splunklib.results as results

ui_subdir='ui'

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

    SPLUNK_HOST='localhost'
    SPLUNK_PORT=8089
    SPLUNK_AUTH_TOKEN='eyJraWQiOiJzcGx1bmsuc2VjcmV0IiwiYWxnIjoiSFM1MTIiLCJ2ZXIiOiJ2MiIsInR0eXAiOiJzdGF0aWMifQ.eyJpc3MiOiJhZG1pbiBmcm9tIEMwMkcyMzVCTUQ2UiIsInN1YiI6ImFkbWluIiwiYXVkIjoicHl0aG9uIHRlc3RzIiwiaWRwIjoiU3BsdW5rIiwianRpIjoiYWIyMzQ4M2FhYjk2OTA1ZGJmNGUwZTdlM2Y0OGI1MjE1ODcyOTUwM2ZmNjE0YjVjNzc5MWUyZWRlOGFkZjBhNSIsImlhdCI6MTY2Mzc4MDc3MiwiZXhwIjoxNzE1NjIwNzcyLCJuYnIiOjE2NjM3ODA3NzJ9.b0SRVIBCn3mEy3kXuE5BXyrNruW392Sch52QzWeCQ2n5NukW3dkT8FdH_YvQNwAr1DdP7JUROgdHdhCu2cT18A'
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
            print(auth_token)
            env_var=re.sub(r"%(.+)%","\\1",auth_token)
            # print(env_var)
            env_var_val=os.environ.get(env_var)
            print(env_var_val)
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

    
    
app.run(host='localhost', port=8080, debug=False,reloader=True)