from bottle import route, run, template

@route('/hello/<name>')
def index(name):
    return template('<b>Hello {{name}}</b>!', name=name)

import webbrowser
url = "http://localhost:8080/hello/world"
webbrowser.open(url, new=0, autoraise=True)

run(host='localhost', port=8080)

