from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    consulta = [1,2,3,4,5,6]
    return render_template('index.html', consulta = consulta)

@app.route('/admin/proyectos')
def admin_proyectos():
    return render_template('administrador/proyectos.html')

if __name__ == '__main__':
    app.run(debug=True)