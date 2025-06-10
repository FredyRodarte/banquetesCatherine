from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import cx_Oracle
import re

dsn = cx_Oracle.makedsn("localhost", 1521, service_name="XE") 
conn = cx_Oracle.connect(user="banquetes", password="banquetes", dsn=dsn)
cursor = conn.cursor()

app = Flask(__name__)
app.secret_key = 'contraseña'

@app.route('/')
def index():
    consulta = [1,2,3,4,5,6]
    return render_template('index.html', consulta = consulta)

@app.route('/admin/proyectos')
def admin_proyectos():
    return render_template('/administrador/proyectos.html')

@app.route('/admin/usuario/nuevo')
def nuevo_usuario():
    return render_template('administrador/nuevo_usuario.html')

def es_rfc_valido(rfc: str) -> bool:
    """
    Valida que el RFC tenga el patrón esperado:
    - 3 o 4 letras (A–Z, Ñ, &) seguidas de 6 dígitos (año/mes/día) 
      y luego 3 caracteres (alfanuméricos).
    - Total: 13 caracteres (para persona física).
    """
    patron_rfc = r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$'
    return bool(re.match(patron_rfc, rfc.strip().upper()))

def es_curp_valido(curp: str) -> bool:
    """
    Valida que la CURP tenga el patrón:
    - 4 letras (A–Z),
    - 6 dígitos (año/mes/día),
    - 1 carácter H o M,
    - 5 letras,
    - 1 dígito o letra,
    - 1 dígito verificador.
    - Total: 18 caracteres.
    """
    patron_curp = r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$'
    return bool(re.match(patron_curp, curp.strip().upper()))

@app.route('/admin/registrar', methods=['POST'])
def registrar():
    # 1) Recuperar valores desde el formulario
    rfc_form  = request.form['rfc'].strip().upper()
    curp_form = request.form['curp'].strip().upper()
    #id_usuario = request.form['id_usuario']
    # ... (otros campos)

    # 2) Validar RFC
    if not es_rfc_valido(rfc_form):
        flash("⚠️ RFC incorrecta. Verifica el formato (13 caracteres).", "danger")
        return redirect(url_for('nuevo_usuario'))

    # 3) Validar CURP
    if not es_curp_valido(curp_form):
        flash("⚠️ CURP incorrecta. Verifica el formato (18 caracteres).", "danger")
        return redirect(url_for('nuevo_usuario'))
    
    try:
        datos = (
            rfc_form,
            curp_form,
            request.form['pass'],
            request.form['apaterno'],
            request.form['amaterno'],
            request.form['nombre'],
            request.form['calle'],
            request.form['numero'],
            request.form['localidad'],
            request.form['municipio'],
            request.form['estado'],
            request.form['c_postal'],
            datetime.now(),
            1     
        )

        sql = """
        INSERT INTO usuario (
            id_usuario, rfc, curp, pass, apaterno, amaterno,
            nombre, calle, numero, localidad, municipio, estado,
            c_postal, ultimo_acceso, estatus
        ) VALUES (
             'UG-' || LPAD(seq_id_usuario.NEXTVAL, 4, '0'), :1, :2, :3, :4, :5, :6,
            :7, :8, :9, :10, :11, :12,
            :13, :14
        )
        """

        cursor.execute(sql, datos)
        conn.commit()

        flash("✅ El usuario fue registrado exitosamente.", "success")
        return redirect(url_for('listar_usuarios'))

    except Exception as e:
        print("❌ ERROR al registrar usuario:", e)
        flash("⚠️ El usuario no se pudo crear. Verifica los datos o que no esté duplicado el ID.", "danger")
        return redirect(url_for('nuevo_usuario'))
    

@app.route('/admin/usuario')
def listar_usuario():
    try:
        cursor.execute("SELECT * FROM usuario")
        rows = cursor.fetchall()
        usuarios = []

        for row in rows:
            usuarios.append({
                'id_usuario': row[0],
                'RFC': row[1],
                'CURP': row[2],
                'pass': row[3],
                'apaterno': row[4],
                'amaterno': row[5],
                'nombre': row[6],
                'calle': row[7],
                'numero': row[8],
                'localidad': row[9],
                'municipio': row[10],
                'estado': row[11],
                'codigo_postal': row[12],
                'ultimo_acceso': row[13],
                'estatus': bool(row[14])
            })

        return render_template("administrador/usuario.html", usuarios=usuarios)

    except Exception as e:
        print(f"Error consultando usuario: {e}")
        return "Error al cargar usuario"

@app.route("/admin/usuario/eliminar/<id>")
def eliminar_usuario(id):
    try:
        cursor.execute("DELETE FROM usuario WHERE id_usuario = :1", [id])
        conn.commit()
        return redirect(url_for('listar_usuario'))
    except Exception as e:
        print(f"Error al eliminar usuario con ID {id}: {e}")
        return redirect(url_for('listar_usuario'))
    

@app.route('/admin/usuario/editar/<id>', methods=['GET'])
def editar_usuario(id):
    try:
        cursor.execute("SELECT * FROM usuario WHERE id_usuario = :1", [id])
        row = cursor.fetchone()
        if row:
            usuario = {
                'id_usuario': row[0],
                'rfc': row[1],
                'curp': row[2],
                'pass': row[3],
                'apaterno': row[4],
                'amaterno': row[5],
                'nombre': row[6],
                'calle': row[7],
                'numero': row[8],
                'localidad': row[9],
                'municipio': row[10],
                'estado': row[11],
                'c_postal': row[12],
                'ultimo_acceso': row[13],
                'estatus': row[14]
            }
            return render_template("administrador/editar_usuario.html", usuario=usuario)
        else:
            return "Usuario no encontrado", 404
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/admin/usuario/actualizar/<id>', methods=['POST'])
def actualizar_usuario(id):
    try:
        datos = (
            request.form['rfc'],
            request.form['curp'],
            request.form['pass'],
            request.form['apaterno'],
            request.form['amaterno'],
            request.form['nombre'],
            request.form['calle'],
            request.form['numero'],
            request.form['localidad'],
            request.form['municipio'],
            request.form['estado'],
            request.form['c_postal'],
            request.form.get('estatus', 1), 
            id
        )
        sql = """
        UPDATE usuario SET
            rfc = :1, curp = :2, pass = :3,
            apaterno = :4, amaterno = :5, nombre = :6,
            calle = :7, numero = :8, localidad = :9,
            municipio = :10, estado = :11, c_postal = :12,
            estatus = :13
        WHERE id_usuario = :14
        """
        cursor.execute(sql, datos)
        conn.commit()
        return redirect(url_for('listar_usuario'))
    except Exception as e:
        return f"Error al actualizar: {e}", 500



@app.route('/admin/ingredientes')
def lista_ingredientes():
    ingredientes_ejemplo = [
        {
            'id_ingrediente': 1,
            'nombre_ingrediente': 'Harina de trigo',
            'unidad_medida': 'kg',
            'presentacion': 'Bolsa de 1 kg',
            'descripcion': 'Harina refinada para repostería'
        },
]
    return render_template('administrador/ingredientes.html', ingredientes=ingredientes_ejemplo)


if __name__ == '__main__':
    app.run(debug=True)