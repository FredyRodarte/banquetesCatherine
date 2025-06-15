from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import cx_Oracle
import re

dsn = cx_Oracle.makedsn("localhost", 1521, service_name="xe") 
conn = cx_Oracle.connect(user="banquetes", password="banquetes", dsn=dsn)
cursor = conn.cursor()

#funcion para abrir y cerrar conexion
def get_db_connection():
    dsn = cx_Oracle.makedsn("localhost", 1521, service_name="xe")
    return cx_Oracle.connect(user="banquetes", password="banquetes", dsn=dsn)

app = Flask(__name__)
app.secret_key = 'contraseña'

@app.route('/')
def index():
    
    return render_template('index.html')

@app.route('/admin/proyectos')
def admin_proyectos():
    try:
        #crear conexion a la bd
        conexion = get_db_connection()
        cursor1 = conexion.cursor()

        query = """
        SELECT 
            p.ID_PROYECTO,
            p.COMENSALES,
            s.NOMBRE_SALON AS NOMBRE_SALON,
            g.NOMBRE || ' ' || g.APATERNO || ' ' || g.AMATERNO AS NOMBRE_GERENTE,
            p.RFC_GERENTE,
            p.CURP_GERENTE,
            u.NOMBRE || ' ' || u.APATERNO || ' ' || u.AMATERNO AS NOMBRE_USUARIO,
            p.RFC_USUARIO,
            p.CURP_USUARIO,
            paq.NOMBRE_PAQUETE AS NOMBRE_PAQUETE,
            TO_CHAR(p.FECHA_EVENTO, 'DD/MM/YYYY') AS FECHA_EVENTO_FORM,
            p.ANTICIPO,
            CASE p.ESTATUS_EVENTO 
                WHEN 1 THEN 'Pendiente'
                WHEN 2 THEN 'Confirmado'
                WHEN 3 THEN 'Cancelado'
                WHEN 4 THEN 'Completado'
                ELSE 'Desconocido'
            END AS ESTATUS_EVENTO
        FROM 
            proyecto p
        JOIN 
            salon s ON p.ID_SALON = s.ID_SALON
        JOIN 
            gerente_evento g ON p.ID_GERENTE = g.ID_GERENTE
        JOIN 
            usuario u ON p.ID_USUARIO = u.ID_USUARIO
        JOIN 
            paquete paq ON p.ID_PAQUETE = paq.ID_PAQUETE
        ORDER BY
            p.ID_PROYECTO
        """

        cursor1.execute(query)
        rows = cursor1.fetchall()
        proyectos = []

        for row in rows:
            proyectos.append({
                'id_proyecto': row[0],
                'comensales': row[1],
                'nombre_salon': row[2],
                'nombre_gerente': row[3],
                'rfc_gerente': row[4],
                'curp_gerente': row[5],
                'nombre_usuario': row[6],
                'rfc_usuario': row[7],
                'curp_usuario': row[8],
                'nombre_paquete': row[9],
                'fecha_evento': row[10],
                'anticipo': row[11],
                'estatus_evento': row[12]
            })
        
        #cerrar conexion 
        cursor1.close()
        conexion.close()
        return render_template('/administrador/proyectos.html', proyectos=proyectos)
    except Exception as e:
        print("Error al cargar proyectos")
        return render_template('index.html')

@app.route('/admin/nuevo_proyecto')
def nuevo_proyecto():
    return render_template('/administrador/nuevo_proyecto.html')

@app.route('/admin/complementos')
def admin_complementos():
    try:
        #crear conexion a la bd
        conexion = get_db_connection()
        cursor1 = conexion.cursor()

        query = """
        SELECT
            ID_COMPLEMENTO,
            NOMBRE_COMPLEMENTO,
            UNIDAD_MEDIDA,
            PRESENTACION,
            CANTIDAD
        FROM BANQUETES.COMPLEMENTO
        ORDER BY ID_COMPLEMENTO
        """
        #print("consulta a ejecutar:", query)
        cursor1.execute(query)
        rows = cursor1.fetchall()
        complementos = []

        for row in rows:
            complementos.append({
                'id_complemento': row[0],
                'nombre': row[1],
                'medida': row[2],
                'presentacion': row[3],
                'cantidad': row[4]
            })

        #cerrar conexion 
        cursor1.close()
        conexion.close()
        #print("complementos:", complementos)
        return render_template('/administrador/complementos.html', complementos=complementos)
    except Exception as e:
        print("Error al cargar la tabla complementos", e)


#=======================================================
# Ruta base agregar Usuarios(que son los clientes)
#========================================================
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
        return redirect(url_for('nuevo_usuario'))

    except Exception as e:
        print("❌ ERROR al registrar usuario:", e)
        flash("⚠️ El usuario no se pudo crear. Verifica los datos o que no esté duplicado el ID.", "danger")
        return redirect(url_for('nuevo_usuario'))
    
#=======================================================
# Ruta que muestra los usuarios(que son los clientes)
#========================================================
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


#=======================================================
# Ruta base agregar Ingredientes de platillos
#========================================================
@app.route('/admin/ingredientes')
def lista_ingredientes():
    try:
        cursor.execute("SELECT * FROM ingrediente ORDER BY id_ingrediente")
        rows = cursor.fetchall()
        ingredientes = []
        for row in rows:
            ingredientes.append({
                'id': row[0],
                'nombre': row[1],
                'unidad': row[2],
                'presentacion': row[3],
                'descripcion': row[4],
                'precio': row[5]
            })
        #print(ingredientes)
        return render_template("administrador/ingredientes.html", ingredientes=ingredientes)
    except Exception as e:
        print(f"Error al consultar ingredientes: {e}")
        return "Error cargando ingredientes"

@app.route('/admin/ingrediente/nuevo', methods=['GET', 'POST'])
def nuevo_ingrediente():
    if request.method == 'POST':
        try:
            datos = (
                request.form['nombre'],
                request.form['unidad'],
                request.form['presentacion'],
                request.form['descripcion'],
                float(request.form['precio'])
            )
            cursor.execute("""
                INSERT INTO ingrediente (
                    id_ingrediente, nombre_ingrediente, unidad_medida,
                    presentacion, descripcion, precio
                ) VALUES (
                    ingrediente_seq.NEXTVAL, :1, :2, :3, :4, :5
                )
            """, datos)
            conn.commit()
            flash("Ingrediente registrado correctamente.", "success")
            return redirect(url_for('listar_ingredientes'))
        except Exception as e:
            print(f"Error al registrar ingrediente: {e}")
            flash("Error al registrar el ingrediente.", "danger")
            return redirect(url_for('nuevo_ingrediente'))

    return render_template("administrador/nuevo_ingrediente.html")

@app.route('/admin/ingrediente/editar/<int:id>', methods=['GET'])
def editar_ingrediente(id):
    try:
        cursor.execute("SELECT * FROM ingrediente WHERE id_ingrediente = :1", [id])
        row = cursor.fetchone()
        if row:
            ingrediente = {
                'id': row[0],
                'nombre': row[1],
                'unidad': row[2],
                'presentacion': row[3],
                'descripcion': row[4],
                'precio': row[5]
            }
            return render_template("administrador/editar_ingrediente.html", ingrediente=ingrediente)
        else:
            flash("Ingrediente no encontrado.", "danger")
            return redirect(url_for('lista_ingredientes'))
    except Exception as e:
        print(f"Error al cargar ingrediente: {e}")
        flash("Error al cargar el ingrediente.", "danger")
        return redirect(url_for('lista_ingredientes'))

@app.route('/admin/ingrediente/actualizar/<int:id>', methods=['POST'])
def actualizar_ingrediente(id):
    try:
        datos = (
            request.form['nombre'],
            request.form['unidad'],
            request.form['presentacion'],
            request.form['descripcion'],
            float(request.form['precio']),
            id
        )
        cursor.execute("""
            UPDATE ingrediente SET
                nombre_ingrediente = :1,
                unidad_medida = :2,
                presentacion = :3,
                descripcion = :4,
                precio = :5
            WHERE id_ingrediente = :6
        """, datos)
        conn.commit()
        flash("Ingrediente actualizado correctamente.", "success")
        return redirect(url_for('lista_ingredientes'))
    except Exception as e:
        print(f"Error al actualizar ingrediente: {e}")
        flash("Error al actualizar el ingrediente.", "danger")
        return redirect(url_for('editar_ingrediente', id=id))

@app.route('/admin/ingrediente/eliminar/<int:id>', methods=['POST'])
def eliminar_ingrediente(id):
    try:
        cursor.execute("DELETE FROM ingrediente WHERE id_ingrediente = :1", [id])
        conn.commit()
        flash("Ingrediente eliminado correctamente.", "success")
    except Exception as e:
        print(f"Error al eliminar ingrediente: {e}")
        flash("No se pudo eliminar el ingrediente.", "danger")
    return redirect(url_for('lista_ingredientes'))


#=======================================================
# Ruta base para el Gerente de Proyecto
#========================================================
@app.route('/admin/gerente_proyecto')
def dashboard_gerente():
    # Datos simulados 
    proyectos = [
        {"nombre": "Boda González", "fecha": "2025-07-12", "estatus": "En preparación"},
        {"nombre": "Conferencia Tech", "fecha": "2025-08-01", "estatus": "Confirmado"},
        {"nombre": "Graduación UNAM", "fecha": "2025-06-28", "estatus": "Finalizado"}
    ]
    return render_template('administrador/gerente_proyecto.html', proyectos=proyectos)

#=======================================================
# Ruta base para Salones
#========================================================

@app.route('/admin/salones')
def listar_salones():
    try:
        cursor.execute("""
            SELECT 
                ID_SALON, 
                NOMBRE_SALON, 
                CAPACIDAD,
                CALLE || ' ' || NUMERO || ', ' || LOCALIDAD || ', ' || MUNICIPIO || ', ' || ESTADO || ', CP ' || C_POSTAL AS UBICACION
            FROM SALON
        """)
        resultados = cursor.fetchall()

        salones = []
        for row in resultados:
            salones.append({
                'id': row[0],
                'nombre': row[1],
                'capacidad': row[2],
                'ubicacion': row[3]
            })
            
        #print(salones)

        return render_template("administrador/salones.html", salones=salones)
    
    except Exception as e:
        print(f"❌ ERROR en listar_salones: {e}")
        return "Error al consultar los salones", 500

cursor.execute("SELECT USER FROM DUAL")
print("Usuario conectado:", cursor.fetchone()[0])

#=======================================================
# Ruta base agregar Salones
#========================================================

@app.route('/admin/salones/nuevo', methods=['GET', 'POST'])
def nuevo_salon():
    if request.method == 'POST':
        try:
            id_gerente_s = request.form['id_gerente_s']
            nombre = request.form['nombre']
            capacidad = request.form['capacidad']
            calle = request.form['calle']
            numero = request.form['numero']
            localidad = request.form['localidad']
            municipio = request.form['municipio']
            estado = request.form['estado']
            c_postal = request.form['c_postal']

            cursor.execute("""
                INSERT INTO SALON (
                    ID_SALON, ID_GERENTE_S, NOMBRE_SALON, CAPACIDAD, CALLE, NUMERO, LOCALIDAD, MUNICIPIO, ESTADO, C_POSTAL
                ) VALUES (
                    SQ_ID_SALON.NEXTVAL, :id_gerente_S, :nombre, :capacidad, :calle, :numero, :localidad, :municipio, :estado, :c_postal
                )
            """, {
                'id_gerente_s': id_gerente_s,
                'nombre': nombre,
                'capacidad': capacidad,
                'calle': calle,
                'numero': numero,
                'localidad': localidad,
                'municipio': municipio,
                'estado': estado,
                'c_postal': c_postal
            })

            conn.commit()

            return redirect(url_for('listar_salones'))

        except Exception as e:
            print(f"❌ ERROR al agregar salón: {e}")
            return "Error al agregar el salón", 500

    # Vista del formulario
    try:
        cursor.execute("SELECT ID_GERENTE_S, NOMBRE FROM GERENTE_SALON")
        resultados = cursor.fetchall()
        gerentes = [{'id': row[0], 'nombre': row[1]} for row in resultados]

        return render_template('administrador/nuevo_salon.html', gerentes=gerentes)

    except Exception as e:
        print(f"❌ ERROR al cargar gerentes: {e}")
        return "Error al cargar formulario", 500
    


#=======================================================
# Función para generar ID único para nuevo gerente
#=======================================================
def generar_id_gerente():
    conexion = get_db_connection()
    cursor = conexion.cursor()
    cursor.execute("SELECT MAX(ID_GERENTE) FROM GERENTE_SALON")
    resultado = cursor.fetchone()
    cursor.close()
    conexion.close()

    if resultado and resultado[0]:
        ultimo_id = int(resultado[0][2:])  # de 'GS005' obtiene 5
        nuevo_num = ultimo_id + 1
    else:
        nuevo_num = 1
    return f"GS{nuevo_num:03}"  # da formato 'GS006'

#=======================================================
# Ruta para listar gerentes de salón
#=======================================================
@app.route('/admin/gerente_salon')
def gerente_salon():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT ID_GERENTE, APATERNO, AMATERNO, NOMBRE, TELEFONO, EMAIL
            FROM GERENTE_SALON ORDER BY ID_GERENTE
        """)
        rows = cursor.fetchall()
        gerentes = []
        for r in rows:
            gerentes.append({
                'id_gerente': r[0],
                'apaterno': r[1],
                'amaterno': r[2],
                'nombre': r[3],
                'telefono': r[4],
                'email': r[5]
            })
        cursor.close()
        conexion.close()
        return render_template('administrador/gerente_salon.html', gerentes=gerentes)
    except Exception as e:
        print('Error cargar gerentes:', e)
        flash('Error al cargar gerentes', 'danger')
        return render_template('administrador/gerente_salon.html', gerentes=[])

#========================================================
# Ruta para registrar nuevo gerente
#========================================================
@app.route('/admin/nuevo_gerente_salon', methods=['GET', 'POST'])
def nuevo_gerente_salon():
    if request.method == 'POST':
        apaterno = request.form.get('apaterno')
        amaterno = request.form.get('amaterno')
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        email = request.form.get('email')

        try:
            
            id_gerente = generar_id_gerente()  # Generar nuevo ID único

            conexion = get_db_connection()
            cursor = conexion.cursor()
            print (id_gerente, apaterno, amaterno, nombre, telefono, email)
            cursor.execute("""
                INSERT INTO GERENTE_SALON (ID_GERENTE, APATERNO, AMATERNO, NOMBRE, TELEFONO, EMAIL)
                VALUES (:1, :2, :3, :4, :5, :6)
            """, (id_gerente, apaterno, amaterno, nombre, telefono, email))
            
            conexion.commit()
        
            cursor.close()
            conexion.close()
            
            flash('Gerente agregado correctamente', 'success')
            
            return redirect(url_for('gerente_salon'))
        except Exception as e:
            print('Error agregar gerente:', e)
            flash('Error al agregar gerente', 'danger')
            return redirect(url_for('nuevo_gerente_salon'))

    # GET - mostrar formulario
    return render_template('administrador/nuevo_gerente_salon.html')

#========================================================
# Ruta para actualizar gerente desde el modal
#========================================================
@app.route('/admin/actualizar_gerente', methods=['POST'])
def actualizar_gerente():
    id_gerente = request.form.get('id_gerente')
    apaterno = request.form.get('apaterno')
    amaterno = request.form.get('amaterno')
    nombre = request.form.get('nombre')
    telefono = request.form.get('telefono')
    email = request.form.get('email')

    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE GERENTE_SALON
            SET APATERNO = :1,
                AMATERNO = :2,
                NOMBRE = :3,
                TELEFONO = :4,
                EMAIL = :5
            WHERE ID_GERENTE = :6
        """, (apaterno, amaterno, nombre, telefono, email, id_gerente))
        conexion.commit()
        cursor.close()
        conexion.close()
        flash('Gerente actualizado correctamente', 'success')
    except Exception as e:
        print("Error al actualizar gerente:", e)
        flash('Error al actualizar gerente', 'danger')
    return redirect(url_for('gerente_salon'))





#=======================================================
# Ruta para mostrar Salones
#========================================================
@app.route('/salones_public')
def salones_public():
    try:
        cursor.execute("""
            SELECT ID_SALON, NOMBRE_SALON, CAPACIDAD,
            CALLE || ' ' || NUMERO || ', ' || LOCALIDAD || ', ' || MUNICIPIO || ', ' || ESTADO || ', CP ' || C_POSTAL AS UBICACION
            FROM SALON
        """)
        resultados = cursor.fetchall()

        salones = []
        for row in resultados:
            nombre = row[1]
            nombre_lower = nombre.lower()
            
            if 'diamante' in nombre_lower:
                imagen = 'Diamante.jpeg'
            elif 'esmeralda' in nombre_lower:
                imagen = 'Esmeralda.jpeg'
            elif 'azteca' in nombre_lower:
                imagen = 'Azteca.jpeg'
            else:
                imagen = 'Default.jpg'

            salones.append({
                'id': row[0],
                'nombre': nombre,
                'capacidad': row[2],
                'ubicacion': row[3],
                'imagen': imagen
            })

        return render_template('publicos/salones_cliente.html', salones=salones)

    except Exception as e:
        print(f"❌ Error al cargar salones públicos: {e}")
        return "Error cargando salones", 500


if __name__ == '__main__':
    app.run(debug=True)
