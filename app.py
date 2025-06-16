from flask import Flask, render_template, session, request, redirect, url_for, flash, make_response, send_file
from datetime import datetime, timedelta
from xhtml2pdf import pisa
from io import BytesIO
import cx_Oracle
import re
import os
from werkzeug.utils import secure_filename
import pandas as pd

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
    
    return render_template(
        'index.html',
        salones=obtener_salones(),
        platillos=obtener_platillos(),
        complementos=obtener_complementos())

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
                WHEN 0 THEN 'Pendiente'
                WHEN 1 THEN 'Activo'
                WHEN 2 THEN 'Cancelado'
                WHEN 3 THEN 'Completado'
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
        print("Error al cargar proyectos", e)
        return render_template('index.html')

@app.route('/admin/nuevo_proyecto')
def nuevo_proyecto():
    try:
        #crear conexion a la bd
        conexion = get_db_connection()
        cursor1 = conexion.cursor()

        querySalon = '''
        SELECT
            ID_SALON,
            NOMBRE_SALON
        FROM
            SALON
        '''

        queryGerente = '''
        SELECT
            ID_GERENTE,
            NOMBRE || ' ' || APATERNO || ' ' || AMATERNO as NOMBRE_GERENTE
        FROM
            GERENTE_EVENTO
        '''

        queryUsuario = '''
        SELECT
            ID_USUARIO,
            NOMBRE || ' ' || APATERNO || ' ' || AMATERNO as NOMBRE_USUARIO
        FROM
            USUARIO
        '''

        queryPaquete = '''
        SELECT
            ID_PAQUETE,
            NOMBRE_PAQUETE
        FROM
            PAQUETE
        '''

        cursor1.execute(querySalon)
        rows = cursor1.fetchall()
        salones = []

        for row in rows:
            salones.append({
                'id_salon': row[0],
                'nombre_salon': row[1]
            })

        cursor1.execute(queryGerente)
        rows = cursor1.fetchall()
        gerentes = []

        for row in rows:
            gerentes.append({
                'id_gerente': row[0],
                'nombre_gerente': row[1]
            })

        cursor1.execute(queryUsuario)
        rows = cursor1.fetchall()
        usuarios = []

        for row in rows:
            usuarios.append({
                'id_usuario': row[0],
                'nombre_usuario': row[1]
            })
        
        cursor1.execute(queryPaquete)
        rows = cursor1.fetchall()
        paquetes = []

        for row in rows:
            paquetes.append({
                'id_paquete': row[0],
                'nombre_paquete': row[1]
            })

        #cerrar conexion 
        cursor1.close()
        conexion.close()
        
        #print("salones: ", salones)
        #print("Gerentes:", gerentes)
        #print("usuarios:", usuarios)
        #print("paquete:", paquetes)
        
        return render_template('/administrador/nuevo_proyecto.html', salones=salones, gerentes=gerentes, usuarios=usuarios, paquetes=paquetes)
    except Exception as e:
        print("Error al hacer las consultas en las respectivas tablas")

@app.route('/admin/registrar_proyecto', methods=['POST'])
def registrar_proyecto():
    try:
        #Recuperar los datos del formulario:
        comensales = request.form['comensalesA']
        id_salon = request.form['salonA']
        id_gerente = request.form['gerenteA']
        rfc_gerente = ''
        curp_gerente = ''
        id_usuario = request.form['usuarioA']
        rfc_usuario = ''
        curp_usuario = ''
        id_paquete = request.form['paqueteA']
        fecha = request.form['fechaA']
        anticipo = request.form['anticipoA']
        estatus = request.form['estatusA']

        #Formatear la fecha para no tener problemas con la BD
        fecha_oracle = datetime.strptime(fecha, '%Y-%m-%d').strftime('%d-%b-%y').upper()

        #crear conexion a la bd
        conexion = get_db_connection()
        cursor1 = conexion.cursor()

        queryGerente = '''
        SELECT
            RFC,
            CURP
        FROM
            GERENTE_EVENTO
        WHERE ID_GERENTE = :id_gerente
        '''

        queryUsuario = '''
        SELECT
            RFC,
            CURP
        FROM
            USUARIO
        WHERE ID_USUARIO = :id_usuario
        '''
        cursor1.execute(queryGerente,{'id_gerente': id_gerente})
        datos_gerente = cursor1.fetchone()

        if datos_gerente:
            rfc_gerente, curp_gerente = datos_gerente
        else:
            rfc_gerente, curp_gerente = '', ''

        cursor1.execute(queryUsuario,{'id_usuario': id_usuario})
        datos_usuario = cursor1.fetchone()

        if datos_usuario:
            rfc_usuario, curp_usuario = datos_usuario
        else:
            rfc_usuario, curp_usuario = '', ''

        queryProyecto = '''
        INSERT INTO PROYECTO (ID_PROYECTO,COMENSALES, ID_SALON, ID_GERENTE, RFC_GERENTE, CURP_GERENTE,
            ID_USUARIO, RFC_USUARIO, CURP_USUARIO, ID_PAQUETE, FECHA_EVENTO, ANTICIPO, ESTATUS_EVENTO)
            VALUES (SQ_PROYECTO.NEXTVAL, :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12)
        '''
        cursor1.execute(queryProyecto, [comensales, id_salon, id_gerente, rfc_gerente, curp_gerente,
                                        id_usuario, rfc_usuario, curp_usuario, id_paquete, fecha_oracle, anticipo, estatus])
        conexion.commit()

        #cerrar conexion 
        cursor1.close()
        conexion.close()

        flash("✅ El proyecto fue registrado exitosamente.", "success")
        return redirect(url_for('admin_proyectos'))
    except Exception as e:
        print("❌ ERROR al registrar proyecto:", e)
        flash("⚠️ El proyecto no se pudo registrar. Verifica los datos ingresados")


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
                'estatus': bool(row[14]),
                'rol': row[15]
            })

        return render_template("administrador/usuario.html", usuarios=usuarios)

    except Exception as e:
        print(f"Error consultando usuario: {e}")
        return "Error al cargar usuario"

@app.route('/admin/usuario/eliminar/<id>', methods=['POST'])
def eliminar_usuario(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    rol_sesion = session.get('rol')
    usuario_actual = session.get('usuario_id')

    try:
        # Verificamos quién se quiere eliminar
        cursor.execute("SELECT rol FROM usuario WHERE id_usuario = :1", [id])
        resultado = cursor.fetchone()

        if not resultado:
            flash("Usuario no encontrado.", "danger")
            return redirect(url_for('listar_usuario'))

        rol_objetivo = resultado[0]

        # Reglas
        if rol_sesion == 'jefe':
            pass  # Puede eliminar a cualquier usuario

        elif rol_sesion in ['gerente_evento', 'gerente_salon']:
            if rol_objetivo != 'cliente':
                flash("Como gerente, solo puedes eliminar clientes.", "warning")
                return redirect(url_for('listar_usuario'))

        else:
            flash("No tienes permiso para eliminar usuarios.", "danger")
            return redirect(url_for('index'))

        # Acción de eliminación
        cursor.execute("DELETE FROM usuario WHERE id_usuario = :1", [id])
        conn.commit()
        flash("Usuario eliminado correctamente.", "success")
        return redirect(url_for('listar_usuario'))

    except Exception as e:
        return f"Error al eliminar: {e}", 500

    

# @app.route('/admin/usuario/editar/<id>', methods=['GET'])
# def editar_usuario(id):
#     try:
#         cursor.execute("SELECT * FROM usuario WHERE id_usuario = :1", [id])
#         row = cursor.fetchone()
#         if row:
#             usuario = {
#                 'id_usuario': row[0],
#                 'rfc': row[1],
#                 'curp': row[2],
#                 'pass': row[3],
#                 'apaterno': row[4],
#                 'amaterno': row[5],
#                 'nombre': row[6],
#                 'calle': row[7],
#                 'numero': row[8],
#                 'localidad': row[9],
#                 'municipio': row[10],
#                 'estado': row[11],
#                 'c_postal': row[12],
#                 'ultimo_acceso': row[13],
#                 'estatus': row[14]
#             }
#             return render_template("administrador/editar_usuario.html", usuario=usuario)
#         else:
#             return "Usuario no encontrado", 404
#     except Exception as e:
#         return f"Error: {e}", 500

# @app.route('/admin/usuario/actualizar/<id>', methods=['POST'])
# def actualizar_usuario(id):
#     try:
#         datos = (
#             request.form['rfc'],
#             request.form['curp'],
#             request.form['pass'],
#             request.form['apaterno'],
#             request.form['amaterno'],
#             request.form['nombre'],
#             request.form['calle'],
#             request.form['numero'],
#             request.form['localidad'],
#             request.form['municipio'],
#             request.form['estado'],
#             request.form['c_postal'],
#             request.form.get('estatus', 1), 
#             id
#         )
#         sql = """
#         UPDATE usuario SET
#             rfc = :1, curp = :2, pass = :3,
#             apaterno = :4, amaterno = :5, nombre = :6,
#             calle = :7, numero = :8, localidad = :9,
#             municipio = :10, estado = :11, c_postal = :12,
#             estatus = :13
#         WHERE id_usuario = :14
#         """
#         cursor.execute(sql, datos)
#         conn.commit()
#         return redirect(url_for('listar_usuario'))
#     except Exception as e:
#         return f"Error al actualizar: {e}", 500



#=======================================================
# Ruta base agregar Ingredientes de platillos
#========================================================
@app.route('/admin/usuario/editar/<id>', methods=['GET'])
def editar_usuario(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    rol_sesion = session.get('rol')
    usuario_actual = session.get('usuario_id')

    try:
        cursor.execute("SELECT * FROM usuario WHERE id_usuario = :1", [id])
        row = cursor.fetchone()

        if not row:
            return "Usuario no encontrado", 404

        rol_objetivo = row[15]  # columna 16 = rol

        # Reglas de acceso
        if rol_sesion == 'jefe':
            pass  

        elif rol_sesion in ['gerente_evento', 'gerente_salon']:
            if rol_objetivo != 'cliente':
                flash("Como gerente solo puedes editar clientes.", "warning")
                return redirect(url_for('listar_usuario'))

        else:
            flash("Acceso no autorizado.", "danger")
            return redirect(url_for('index'))

        # Convertimos datos para el formulario
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

    except Exception as e:
        return f"Error: {e}", 500


@app.route('/admin/usuario/actualizar/<id>', methods=['POST'])
def actualizar_usuario(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    rol_sesion = session.get('rol')
    usuario_actual = session.get('usuario_id')

    try:
        # Validamos a quién se está editando
        cursor.execute("SELECT rol FROM usuario WHERE id_usuario = :1", [id])
        target = cursor.fetchone()

        if not target:
            flash("Usuario objetivo no encontrado.", "danger")
            return redirect(url_for('listar_usuario'))

        rol_objetivo = target[0]

        if rol_sesion == 'jefe':
            pass
        elif rol_sesion in ['gerente_evento', 'gerente_salon']:
            if rol_objetivo != 'cliente':
                flash("Como gerente solo puedes editar clientes.", "warning")
                return redirect(url_for('listar_usuario'))

        else:
            flash("Acceso denegado.", "danger")
            return redirect(url_for('index'))

        # Procesar actualización
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

        flash("Usuario actualizado correctamente.", "success")
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
                if not all(request.form.values()):
                    flash("Todos los campos son obligatorios.", "warning")
                    return redirect(url_for('nuevo_ingrediente'))

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

@app.route('/admin/reportes/ingredientes', methods=['GET', 'POST'])
def reporte_ingredientes():
    ingredientes = []
    fecha_inicio = fecha_fin = None

    if request.method == 'POST':
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']

        try:
            query = """
                SELECT 
                    i.nombre_ingrediente,
                    i.unidad_medida,
                    SUM(pi.cantidad * pr.comensales) AS total_requerido,
                    LISTAGG(pr.id_proyecto, ', ') WITHIN GROUP (ORDER BY pr.id_proyecto) AS eventos
                FROM proyecto pr
                JOIN paquete paq ON pr.id_paquete = paq.id_paquete
                JOIN platillo pla ON paq.id_platillo = pla.id_platillo
                JOIN platillo_ingrediente pi ON pla.id_platillo = pi.id_platillo
                JOIN ingrediente i ON pi.id_ingrediente = i.id_ingrediente
                WHERE pr.fecha_evento BETWEEN TO_DATE(:1, 'YYYY-MM-DD') AND TO_DATE(:2, 'YYYY-MM-DD')
                AND pr.estatus_evento = 1
                GROUP BY i.nombre_ingrediente, i.unidad_medida
                ORDER BY i.nombre_ingrediente
            """
            cursor.execute(query, [fecha_inicio, fecha_fin])
            rows = cursor.fetchall()
            for row in rows:
                ingredientes.append({
                    'nombre': row[0],
                    'unidad': row[1],
                    'cantidad': row[2],
                    'eventos': row[3]
                })
        except Exception as e:
            print(f"Error al consultar reporte: {e}")
            flash("Error al generar el reporte", "danger")

    return render_template('administrador/reporte_ingredientes.html', ingredientes=ingredientes, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

@app.route('/admin/reportes/ingredientes/pdf')
def exportar_pdf():
    inicio = request.args.get('inicio')
    fin = request.args.get('fin')
    ingredientes = []

    try:
        cursor.execute("""
            SELECT 
                i.nombre_ingrediente,
                i.unidad_medida,
                SUM(pi.cantidad * pr.comensales) AS total_requerido,
                LISTAGG(pr.id_proyecto, ', ') WITHIN GROUP (ORDER BY pr.id_proyecto) AS eventos
            FROM proyecto pr
            JOIN paquete paq ON pr.id_paquete = paq.id_paquete
            JOIN platillo pla ON paq.id_platillo = pla.id_platillo
            JOIN platillo_ingrediente pi ON pla.id_platillo = pi.id_platillo
            JOIN ingrediente i ON pi.id_ingrediente = i.id_ingrediente
            WHERE pr.fecha_evento BETWEEN TO_DATE(:1, 'YYYY-MM-DD') AND TO_DATE(:2, 'YYYY-MM-DD')
              AND pr.estatus_evento = 1
            GROUP BY i.nombre_ingrediente, i.unidad_medida
            ORDER BY i.nombre_ingrediente
        """, [inicio, fin])

        rows = cursor.fetchall()
        for row in rows:
            ingredientes.append({
                'nombre': row[0],
                'unidad': row[1],
                'cantidad': row[2],
                'eventos': row[3]
            })

            # Generar PDF
        html = render_template('administrador/pdf_ingredientes.html', ingredientes=ingredientes, fecha_inicio=inicio, fecha_fin=fin)
        
        result = BytesIO()
        pisa.CreatePDF(BytesIO(html.encode("utf-8")), dest=result)

        response = make_response(result.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "inline; filename=ingredientes.pdf"
        return response
    
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        flash("No se pudo generar el PDF.", "danger")
        return redirect(url_for('reporte_ingredientes'))

@app.route('/admin/reportes/ingredientes/excel')
def exportar_excel():
    inicio = request.args.get('inicio')
    fin = request.args.get('fin')

    ingredientes = []

    try:
        cursor.execute("""
            SELECT 
                i.nombre_ingrediente,
                i.unidad_medida,
                SUM(pi.cantidad * pr.comensales) AS total_requerido,
                LISTAGG(pr.id_proyecto, ', ') WITHIN GROUP (ORDER BY pr.id_proyecto) AS eventos
            FROM proyecto pr
            JOIN paquete paq ON pr.id_paquete = paq.id_paquete
            JOIN platillo pla ON paq.id_platillo = pla.id_platillo
            JOIN platillo_ingrediente pi ON pla.id_platillo = pi.id_platillo
            JOIN ingrediente i ON pi.id_ingrediente = i.id_ingrediente
            WHERE pr.fecha_evento BETWEEN TO_DATE(:1, 'YYYY-MM-DD') AND TO_DATE(:2, 'YYYY-MM-DD')
              AND pr.estatus_evento = 1
            GROUP BY i.nombre_ingrediente, i.unidad_medida
            ORDER BY i.nombre_ingrediente
        """, [inicio, fin])

        rows = cursor.fetchall()
        for row in rows:
            ingredientes.append({
                'nombre': row[0],
                'unidad': row[1],
                'cantidad': row[2],
                'eventos': row[3]
            })

        # Exportar a Excel
        df = pd.DataFrame(ingredientes)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Reporte')
        output.seek(0)

        return send_file(output, download_name='ingredientes.xlsx', as_attachment=True)

    except Exception as e:
            print("Error exportando a Excel:", e)
            flash("No se pudo exportar el reporte.", "danger")
            return redirect(url_for('reporte_ingredientes'))

@app.route('/admin/proyecto/<int:id>/ingredientes')
def ingredientes_evento(id):
    try:
        cursor.execute("""
            SELECT 
                i.nombre_ingrediente,
                i.unidad_medida,
                pi.cantidad * p.comensales AS cantidad_total,
                pla.nombre_platillo
            FROM proyecto p
            JOIN paquete paq ON p.id_paquete = paq.id_paquete
            JOIN platillo pla ON paq.id_platillo = pla.id_platillo
            JOIN platillo_ingrediente pi ON pla.id_platillo = pi.id_platillo
            JOIN ingrediente i ON pi.id_ingrediente = i.id_ingrediente
            WHERE p.id_proyecto = :1
        """, [id])
        rows = cursor.fetchall()
        ingredientes = []
        for row in rows:
            ingredientes.append({
                'nombre': row[0],
                'unidad': row[1],
                'cantidad': row[2],
                'platillo': row[3]
            })
        return render_template('administrador/ingredientes_evento.html', ingredientes=ingredientes, id_proyecto=id)
    except Exception as e:
        print("Error al obtener ingredientes del evento:", e)
        flash("No se pudo cargar el detalle del evento.", "danger")
        return redirect(url_for('admin_proyectos'))


#=======================================================
# Ruta base para el Gerente de Proyecto
#========================================================
# @app.route('/admin/gerente_proyecto')
# def dashboard_gerente():
#     # Datos simulados 
#     proyectos = [
#         {"nombre": "Boda González", "fecha": "2025-07-12", "estatus": "En preparación"},
#         {"nombre": "Conferencia Tech", "fecha": "2025-08-01", "estatus": "Confirmado"},
#         {"nombre": "Graduación UNAM", "fecha": "2025-06-28", "estatus": "Finalizado"}
#     ]
#     return render_template('administrador/gerente_proyecto.html', proyectos=proyectos)
@app.route('/debug/usuarios')
def debug_usuarios():
    cursor.execute("SELECT id_usuario, rfc, pass, rol FROM usuario")
    usuarios = cursor.fetchall()

    for row in usuarios:
        print(f"ID: {row[0]}, RFC: {row[1]}, PASS: {row[2]}, ROL: {row[3]}")

    return "Consulta de usuarios realizada. Revisa la consola."







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
# Ruta para mostrar Paquetes
#========================================================

# Rutas para Platillos Michi
# --- Rutas para Platillos 
@app.route('/admin/platillos')  # Asegúrate que coincida exactamente
def platillos():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("SELECT ID_PLATILLO, NOMBRE_PLATILLO, PORCIONES, DIFICULTAD FROM PLATILLO")
        platillos = []
        for row in cursor:
            platillos.append({
                'id': row[0],
                'nombre': row[1],
                'porciones': row[2],
                'dificultad': row[3]
            })
        return render_template('administrador/platillos.html', platillos=platillos)  # Asegúrate del return
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('index'))  # Siempre retorna algo
    finally:
        cursor.close()
        conexion.close()
    

@app.route('/admin/platillos/nuevo', methods=['GET'])
def nuevo_platillo():
    return render_template('administrador/nuevo_platillo.html')

@app.route('/admin/platillos/guardar', methods=['POST'])
def guardar_platillo():
    try:
        # Validar datos del formulario
        nombre = request.form.get('nombre', '').strip()
        porciones = request.form.get('porciones', '').strip()
        dificultad = request.form.get('dificultad', '').strip()

        if not nombre or not porciones or not dificultad:
            flash('⚠️ Todos los campos son requeridos', 'warning')
            return redirect(url_for('nuevo_platillo'))

        try:
            porciones = int(porciones)  # Validar que porciones sea número
        except ValueError:
            flash('⚠️ Las porciones deben ser un número entero', 'warning')
            return redirect(url_for('nuevo_platillo'))

        # Conexión a la base de datos
        conexion = get_db_connection()
        cursor = conexion.cursor()

        # Insertar usando la secuencia correcta SQ_ID_PLATILLO
        cursor.execute("""
            INSERT INTO BANQUETES.PLATILLO (
                ID_PLATILLO, 
                NOMBRE_PLATILLO, 
                PORCIONES, 
                DIFICULTAD
            ) VALUES (
                SQ_ID_PLATILLO.NEXTVAL, 
                :1, 
                :2, 
                :3
            )
        """, (nombre, porciones, dificultad))

        conexion.commit()
        flash('✅ Platillo creado exitosamente', 'success')
        return redirect(url_for('platillos'))

    except cx_Oracle.DatabaseError as error:
        error_obj, = error.args
        if error_obj.code == 2289:  # Código para "secuencia no existe"
            flash('⚠️ Error: Problema con la secuencia de platillos', 'danger')
        else:
            flash(f'⚠️ Error de base de datos: {error_obj.message}', 'danger')
        return redirect(url_for('nuevo_platillo'))

    except Exception as e:
        flash(f'⚠️ Error inesperado: {str(e)}', 'danger')
        return redirect(url_for('nuevo_platillo'))

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conexion' in locals():
            conexion.close()

@app.route('/admin/platillos/editar/<int:id>', methods=['GET'])
def editar_platillo(id):
    # Implementación para editar platillo
    pass

@app.route('/admin/platillos/actualizar/<int:id>', methods=['POST'])
def actualizar_platillo(id):
    # Implementación para actualizar platillo
    pass


@app.route('/publicos/platillos_pupulares')
def platillos_populares():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()

        # Consulta para platillos normales
        query_platillos = "SELECT NOMBRE_PLATILLO FROM BANQUETES.PLATILLO ORDER BY NOMBRE_PLATILLO"
        cursor.execute(query_platillos)
        platillos_rows = cursor.fetchall()
        platillos = [{'nombre_platillo': r[0]} for r in platillos_rows]

        # Consulta para platillos populares (IDs 1, 2, 3)
        cursor.execute("""
            SELECT ID_PLATILLO, NOMBRE_PLATILLO 
            FROM BANQUETES.PLATILLO 
            WHERE ID_PLATILLO IN (1, 2, 3)
            ORDER BY ID_PLATILLO
        """)
        populares_rows = cursor.fetchall()
        populares = [
            {'id': row[0], 'nombre': row[1], 'popularidad': '⭐️⭐️⭐️⭐️⭐️' if row[0] == 1 else 
                         '⭐️⭐️⭐️⭐️' if row[0] == 2 else '⭐️⭐️⭐️'}
            for row in populares_rows
        ]

        # Consulta para platillos menos populares (últimos 3)
        cursor.execute("""
            SELECT ID_PLATILLO, NOMBRE_PLATILLO 
            FROM (
                SELECT ID_PLATILLO, NOMBRE_PLATILLO 
                FROM BANQUETES.PLATILLO 
                ORDER BY ID_PLATILLO DESC
            ) 
            WHERE ROWNUM <= 3
            ORDER BY ID_PLATILLO
        """)
        menos_populares_rows = cursor.fetchall()
        menos_populares = [
            {'id': row[0], 'nombre': row[1], 'popularidad': '⭐️'}
            for row in menos_populares_rows
        ]

        # Resto de consultas (complementos y salones)
        query_complementos = "SELECT NOMBRE_COMPLEMENTO FROM BANQUETES.COMPLEMENTO ORDER BY NOMBRE_COMPLEMENTO"
        cursor.execute(query_complementos)
        complementos_rows = cursor.fetchall()
        complementos = [{'nombre_complemento': r[0]} for r in complementos_rows]

        query_salones = "SELECT NOMBRE_SALON, CAPACIDAD FROM BANQUETES.SALON ORDER BY NOMBRE_SALON"
        cursor.execute(query_salones)
        salones_rows = cursor.fetchall()
        salones = [{'nombre_salon': r[0], 'capacidad': r[1]} for r in salones_rows]

        cursor.close()
        conexion.close()

        return render_template('publicos/platillos_populares.html', 
                            platillos=platillos, 
                            complementos=complementos, 
                            salones=salones,
                            populares=populares,
                            menos_populares=menos_populares)
    except Exception as e:
        print("Error al cargar datos de paquetes:", e)
        flash(f"Error al cargar datos de paquetes: {e}", "danger")
        return redirect(url_for('index'))
    

# --- Rutas para Instrucciones 
@app.route('/admin/platillos/<int:id>/instrucciones')
def ver_instrucciones(id):
    # Tu implementación actual
    pass

@app.route('/admin/platillos/<int:id_platillo>/instrucciones/nueva', methods=['GET'])
def agregar_instruccion(id_platillo):
    return render_template('administrador/nueva_instruccion.html', 
                         platillo={'id': id_platillo, 'nombre': "Nombre del Platillo"})

@app.route('/admin/platillos/<int:id_platillo>/instrucciones/guardar', methods=['POST'])
def guardar_instruccion(id_platillo):
    # Implementación para guardar nueva instrucción
    pass

@app.route('/admin/instrucciones/editar/<int:id>', methods=['GET'])
def editar_instruccion(id):
    # Implementación para editar instrucción
    pass

@app.route('/admin/instrucciones/actualizar/<int:id>', methods=['POST'])
def actualizar_instruccion(id):
    # Implementación para actualizar instrucción
    pass

@app.route('/admin/instrucciones/eliminar/<int:id>', methods=['POST'])
def eliminar_instruccion(id):
    # Implementación para eliminar instrucción
    pass



#=======================================================
# Ruta paquetes
#=======================================================
@app.route('/admin/paquetes')
def admin_paquetes():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()

        query_platillos = "SELECT NOMBRE_PLATILLO FROM platillo ORDER BY NOMBRE_PLATILLO"
        cursor.execute(query_platillos)
        platillos_rows = cursor.fetchall()
        platillos = [{'nombre_platillo': r[0]} for r in platillos_rows]

        query_complementos = "SELECT NOMBRE_COMPLEMENTO FROM complemento ORDER BY NOMBRE_COMPLEMENTO"
        cursor.execute(query_complementos)
        complementos_rows = cursor.fetchall()
        complementos = [{'nombre_complemento': r[0]} for r in complementos_rows]

        query_salones = "SELECT NOMBRE_SALON, CAPACIDAD FROM salon ORDER BY NOMBRE_SALON"
        cursor.execute(query_salones)
        salones_rows = cursor.fetchall()
        salones = [{'nombre_salon': r[0], 'capacidad': r[1]} for r in salones_rows]

        # Lista manual de precios para cada paquete (ajusta los valores según los que tengas)
        precios = [2500, 2800, 3200]  # Puedes poner los que gustes según la cantidad de paquetes

        cursor.close()
        conexion.close()

        return render_template('administrador/paquetes.html', 
                               platillos=platillos, 
                               complementos=complementos, 
                               salones=salones,
                               precios=precios)
    except Exception as e:
        print("Error al cargar datos de paquetes:", e)
        return f"Error al cargar datos de paquetes: {e}"


#=======================================================
# Función para generar ID único para nuevo gerente
#=======================================================
def generar_id_gerente():
    conexion = get_db_connection()
    cursor = conexion.cursor()
    cursor.execute("SELECT MAX(ID_GERENTE_S) FROM GERENTE_SALON")
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
            SELECT ID_GERENTE_S, APATERNO, AMATERNO, NOMBRE, TELEFONO, EMAIL
            FROM GERENTE_SALON ORDER BY ID_GERENTE_S
        """)
        rows = cursor.fetchall()
        gerentes = []
        for r in rows:
            gerentes.append({
                'id_gerente_s': r[0],
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
            
            id_gerente_s = generar_id_gerente()  # Generar nuevo ID único

            conexion = get_db_connection()
            cursor = conexion.cursor()
            print (id_gerente_s, apaterno, amaterno, nombre, telefono, email)
            cursor.execute("""
                INSERT INTO GERENTE_SALON (ID_GERENTE, APATERNO, AMATERNO, NOMBRE, TELEFONO, EMAIL)
                VALUES (:1, :2, :3, :4, :5, :6)
            """, (id_gerente_s, apaterno, amaterno, nombre, telefono, email))
            
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
    id_gerente_s = request.form.get('id_gerente')
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
            WHERE ID_GERENTE_s = :6
        """, (apaterno, amaterno, nombre, telefono, email, id_gerente_s))
        conexion.commit()
        cursor.close()
        conexion.close()
        flash('Gerente actualizado correctamente', 'success')
    except Exception as e:
        print("Error al actualizar gerente:", e)
        flash('Error al actualizar gerente', 'danger')
    return redirect(url_for('gerente_salon'))





#=======================================================
# Ruta para mostrar Salones disponibles a cliente
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
    
#=======================================================
# Ruta para mostrar Banquetes disponibles a cliente
#========================================================
@app.route('/banquetes_public')
def banquetes_public():
    try:
        cursor.execute("""
            SELECT ID_PLATILLO, NOMBRE_PLATILLO, PORCIONES, DIFICULTAD, ORIGEN_PLATILLO
            FROM PLATILLO
        """)
        resultados = cursor.fetchall()

        banquetes = []
        for row in resultados:
            nombre = row[1]
            imagen_nombre = nombre.strip() + ".jpeg"

            banquetes.append({
                'id': row[0],
                'nombre': nombre,
                'porciones': row[2],
                'dificultad': row[3],
                'origen': row[4],
                'imagen': imagen_nombre
            })

        return render_template('publicos/banquetes_cliente.html', banquetes=banquetes)

    except Exception as e:
        print(f"❌ Error al cargar banquetes: {e}")
        return "Error cargando banquetes", 500

#=======================================================
# Ruta para mostrar Complementos disponibles a cliente
#========================================================
@app.route('/complementos_public')
def complementos_public():
    try:
        cursor.execute("""
            SELECT ID_COMPLEMENTO, NOMBRE_COMPLEMENTO, UNIDAD_MEDIDA, PRESENTACION, CANTIDAD
            FROM COMPLEMENTO
        """)
        resultados = cursor.fetchall()

        complementos = []
        for row in resultados:
            nombre = row[1]
            imagen_nombre = nombre.strip() + ".jpeg"

            complementos.append({
                'id': row[0],
                'nombre': nombre,
                'unidad': row[2],
                'presentacion': row[3],
                'cantidad': row[4],
                'imagen': imagen_nombre
            })

        return render_template('publicos/complementos_cliente.html', complementos=complementos)

    except Exception as e:
        print(f"❌ Error al cargar complementos: {e}")
        return "Error cargando complementos", 500



#========================================================
# Ruta para reservar
#========================================================
UPLOAD_FOLDER = 'static/comprobantes/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/reservar', methods=['GET', 'POST'])
def reservar():
    if request.method == 'POST':
        campos = ['rfc', 'curp', 'apaterno', 'amaterno', 'nombre', 'calle',
                  'numero', 'localidad', 'municipio', 'estado', 'c_postal',
                  'tipo_paquete', 'tipo_anticipo']
        datos = [request.form.get(c) for c in campos]

        tipo_anticipo = request.form.get('tipo_anticipo')
        comprobante_archivo = request.files.get('comprobante')
        comprobante_nombre = 'pendiente'

        if tipo_anticipo == 'transferencia' and comprobante_archivo:
            comprobante_nombre = secure_filename(comprobante_archivo.filename)
            ruta = os.path.join(UPLOAD_FOLDER, comprobante_nombre)
            comprobante_archivo.save(ruta)

        try:
            cursor.execute("""
                INSERT INTO solicitud_reservacion (
                    rfc, curp, apaterno, amaterno, nombre, calle, numero,
                    localidad, municipio, estado, c_postal,
                    tipo_paquete, tipo_anticipo, comprobante
                ) VALUES (
                    :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12,
                    :13, :14
                )
            """, datos + [comprobante_nombre])
            conn.commit()
            flash("Solicitud registrada correctamente.", "success")
            return redirect(url_for('reservar'))
        except Exception as e:
            return f"Error al guardar solicitud: {e}", 500

    return render_template('/publicos/reservar.html')


#=======================================================
# Ruta para Gerente apruebe solicitud
#========================================================

@app.route('/gerente/solicitudes')
def ver_solicitudes():
    if session.get('rol') not in ['gerente_evento', 'gerente_salon']:
        return redirect(url_for('login'))

    cursor.execute("""
        SELECT id_solicitud, rfc, curp, apaterno, amaterno, nombre, calle, numero,
               localidad, municipio, estado, c_postal, tipo_paquete, tipo_anticipo, comprobante
        FROM solicitud_reservacion
        WHERE revisado = 0
    """)
    rows = cursor.fetchall()

    solicitudes = []
    for row in rows:
        solicitudes.append({
            'id': row[0],
            'rfc': row[1],
            'curp': row[2],
            'apaterno': row[3],
            'amaterno': row[4],
            'nombre': row[5],
            'calle': row[6],
            'numero': row[7],
            'localidad': row[8],
            'municipio': row[9],
            'estado': row[10],
            'c_postal': row[11],
            'tipo_paquete': row[12],
            'tipo_anticipo': row[13],
            'comprobante': row[14]
        })

    return render_template("gerente/solicitudes.html", solicitudes=solicitudes)


@app.route('/gerente/solicitud/form_aprobar/<int:id>')
def form_aprobar_solicitud(id):
    if session.get('rol') not in ['gerente_evento', 'gerente_salon']:
        return redirect(url_for('login'))

    cursor.execute("SELECT * FROM solicitud_reservacion WHERE id_solicitud = :1", [id])
    row = cursor.fetchone()

    if not row:
        flash("Solicitud no encontrada.", "danger")
        return redirect(url_for('ver_solicitudes'))

    campos = ['id_solicitud', 'rfc', 'curp', 'apaterno', 'amaterno', 'nombre',
              'calle', 'numero', 'localidad', 'municipio', 'estado', 'c_postal',
              'tipo_paquete', 'tipo_anticipo', 'comprobante']
    solicitud = dict(zip(campos, row))

    return render_template("gerente/asignar_password.html", solicitud=solicitud)



@app.route('/gerente/solicitud/aprobar/<int:id>', methods=['POST'])
def aprobar_solicitud(id):
    if session.get('rol') not in ['gerente_evento', 'gerente_salon']:
        return redirect(url_for('login'))

    password = request.form['pass'] 
    
    cursor.execute("SELECT * FROM solicitud_reservacion WHERE id_solicitud = :1", [id])
    row = cursor.fetchone()

    if not row:
        flash("Solicitud no encontrada.", "danger")
        return redirect(url_for('ver_solicitudes'))

    try:
        cursor.execute("""
            INSERT INTO usuario (
                id_usuario, rfc, curp, pass, apaterno, amaterno, nombre,
                calle, numero, localidad, municipio, estado, c_postal,
                ultimo_acceso, estatus, rol
            ) VALUES (
                :1, :2, :3, :4, :5, :6, :7,
                :8, :9, :10, :11, :12, :13,
                SYSDATE, 1, 'cliente'
            )
        """, [
            f"CL-{id:04}", row[1], row[2], row[3], row[4], row[5], row[6],
            row[7], row[8], row[9], row[10], row[11], row[12]
        ])
        cursor.execute("UPDATE solicitud_reservacion SET revisado = 1 WHERE id_solicitud = :1", [id])
        conn.commit()
        flash("Cliente creado correctamente.", "success")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error al aprobar solicitud: {e}", 500

    return redirect(url_for('ver_solicitudes'))


@app.route('/gerente/solicitud/rechazar/<int:id>', methods=['POST'])
def rechazar_solicitud(id):
    if session.get('rol') not in ['gerente_evento', 'gerente_salon']:
        return redirect(url_for('login'))

    cursor.execute("UPDATE solicitud_reservacion SET revisado = 1 WHERE id_solicitud = :1", [id])
    conn.commit()
    flash("Solicitud rechazada.", "info")
    return redirect(url_for('ver_solicitudes'))



#=======================================================
# Detalles de la solicitud
#========================================================
@app.route('/gerente/solicitud/<int:id>')
def ver_detalle_solicitud(id):
    if session.get('rol') not in ['gerente_evento', 'gerente_salon']:
        return redirect(url_for('login'))

    cursor.execute("SELECT * FROM solicitud_reservacion WHERE id_solicitud = :1", [id])
    row = cursor.fetchone()

    if not row:
        flash("Solicitud no encontrada.", "danger")
        return redirect(url_for('ver_solicitudes'))

    campos = ['id_solicitud', 'rfc', 'curp', 'apaterno', 'amaterno', 'nombre',
              'calle', 'numero', 'localidad', 'municipio', 'estado', 'c_postal',
              'tipo_paquete', 'tipo_anticipo', 'comprobante']
    solicitud = dict(zip(campos, row))

    return render_template("gerente/detalle_solicitud.html", solicitud=solicitud)




#=======================================================
# Ruta para hacer cotización
#========================================================

def obtener_salones():
    cursor.execute("SELECT id_salon, nombre_salon, precio FROM salon")
    rows = cursor.fetchall()
    
    return [{'id': row[0], 'nombre': row[1], 'precio': row[2]} for row in rows]
    

def obtener_platillos():
    cursor.execute("SELECT id_platillo, nombre_platillo, precio FROM platillo")
    return [{'id': row[0], 'nombre': row[1], 'precio': row[2]} for row in cursor.fetchall()]

def obtener_complementos():
    cursor.execute("SELECT id_complemento, nombre_complemento, precio FROM complemento")
    return [{'id': row[0], 'nombre': row[1], 'precio': row[2]} for row in cursor.fetchall()]


@app.route('/cotizar', methods=['POST'])
def cotizar():

    try:
    
        id_salon = request.form['id_salon']
        id_platillo = request.form['id_platillo']
        id_complemento = request.form['id_complemento']
        comensales = int(request.form['comensales'])
        
        # Obtener comensales desde el formulario
        comensales = int(request.form['comensales'])

        # Consultar precios unitarios
        cursor.execute("SELECT PRECIO FROM SALON WHERE ID_SALON = :id", [id_salon])
        precio_salon = float(cursor.fetchone()[0])

        cursor.execute("SELECT PRECIO FROM PLATILLO WHERE ID_PLATILLO = :id", [id_platillo])
        precio_platillo_unitario = float(cursor.fetchone()[0])

        cursor.execute("SELECT PRECIO FROM COMPLEMENTO WHERE ID_COMPLEMENTO = :id", [id_complemento])
        precio_complemento_unitario = float(cursor.fetchone()[0])

        # Multiplicar por comensales
        precio_platillo_total = precio_platillo_unitario * comensales
        precio_complemento_total = precio_complemento_unitario * comensales

        # Calcular total
        total = precio_salon + precio_platillo_total + precio_complemento_total


        return render_template(
            'index.html',
            salones=obtener_salones(),
            platillos=obtener_platillos(),
            complementos=obtener_complementos(),
            total=total,
            seleccionado={
                'id_salon': int(id_salon),
                'id_platillo': int(id_platillo),
                'id_complemento': int(id_complemento),
                'comensales': int(request.form['comensales']),
                'precio_salon': precio_salon,
                'precio_platillo': precio_platillo_total,
                'precio_complemento': precio_complemento_total
            }
        )

    except Exception as e:
         print(f"❌ Error al calcular cotización: {e}")
         return "Error en la cotización", 500


#========================================================
# Ruta para El logIn
#========================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        password = request.form['password'].strip()

        cursor.execute("""
            SELECT id_usuario, nombre, pass, rol FROM usuario 
            WHERE (rfc = :usuario OR id_usuario = :usuario) AND pass = :password
        """, {'usuario':usuario, 'password':password})

        user = cursor.fetchone()
        if user:
            session['usuario_id'] = user[0]
            session['nombre'] = user[1]
            session['rol'] = user[3]

            flash(f"Bienvenido/a, {user[1]}", "success")

            if user[3] == 'cliente':
                return redirect(url_for('vista_cliente'))
            elif user[3] in ['gerente_evento', 'gerente_salon']:
                return redirect(url_for('dashboard_gerente'))
            elif user[3] == 'jefe':
                return redirect(url_for('admin_proyectos'))  # puedes cambiar esto por una vista de jefe
            else:
                flash("⚠️ Rol no válido.", "danger")
                return redirect(url_for('login'))
        else:
            flash("⚠️ Usuario o contraseña incorrectos.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


#========================================================
# Ruta Vista cliente
#========================================================

@app.route('/cliente/proyectos')
def vista_cliente():
    if 'usuario_id' not in session or session.get('rol') != 'cliente':
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']

    try:
        conexion = get_db_connection()
        cursor1 = conexion.cursor()

        cursor1.execute("""
            SELECT p.ID_PROYECTO, p.COMENSALES, s.NOMBRE_SALON, TO_CHAR(p.FECHA_EVENTO, 'DD/MM/YYYY'), p.ESTATUS_EVENTO
            FROM proyecto p
            JOIN salon s ON p.ID_SALON = s.ID_SALON
            WHERE p.ID_USUARIO = :1
        """, [usuario_id])

        proyectos = [{
            'id': row[0],
            'comensales': row[1],
            'salon': row[2],
            'fecha': row[3],
            'estatus': row[4]
        } for row in cursor1.fetchall()]

        return render_template("cliente/proyectos_cliente.html", proyectos=proyectos)

    except Exception as e:
        print("Error cliente:", e)
        return "Error cargando proyectos"
    
#========================================================
# Ruta para añadir comensales
#========================================================

@app.route('/cliente/actualizar_comensales', methods=['POST'])
def actualizar_comensales():
    if 'usuario_id' not in session or session.get('rol') != 'cliente':
        return redirect(url_for('login'))

    proyecto_id = request.form.get('proyecto_id')
    nuevos_comensales = request.form.get('comensales')
    
    try:
        if not proyecto_id or not nuevos_comensales:
            flash('ID del proyecto y número de comensales son requeridos.', 'error')
            return redirect(url_for('vista_cliente'))
        
        nuevos_comensales = int(nuevos_comensales)
        if nuevos_comensales <= 0:
            flash('El número de comensales debe ser mayor a 0.', 'error')
            return redirect(url_for('vista_cliente'))

        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT TO_CHAR(FECHA_EVENTO, 'DD/MM/YYYY')
            FROM proyecto
            WHERE ID_PROYECTO = :1 AND ID_USUARIO = :2
        """, [proyecto_id, session['usuario_id']])
        resultado = cursor.fetchone()
        
        if not resultado:
            flash('Proyecto no encontrado o no pertenece al usuario.', 'error')
            cursor.close()
            conexion.close()
            return redirect(url_for('vista_cliente'))

        fecha_evento_str = resultado[0]
        fecha_evento = datetime.strptime(fecha_evento_str, '%d/%m/%Y')
        fecha_actual = datetime.now()
        diferencia_dias = (fecha_evento - fecha_actual).days

        if diferencia_dias < 5:
            flash('No se puede actualizar el número de comensales. Faltan menos de 5 días para el evento.', 'error')
            cursor.close()
            conexion.close()
            return redirect(url_for('vista_cliente'))

        cursor.execute("""
            UPDATE proyecto
            SET COMENSALES = :1
            WHERE ID_PROYECTO = :2
        """, [nuevos_comensales, proyecto_id])
        conexion.commit()
        
        flash('Número de comensales actualizado exitosamente.', 'success')
        cursor.close()
        conexion.close()
        
    except ValueError:
        flash('El número de comensales debe ser un número válido.', 'error')
    except Exception as e:
        print("Error actualizando comensales:", e)
        flash('Error al actualizar el número de comensales.', 'error')
    
    return redirect(url_for('vista_cliente'))


##########Vista Gerente
@app.route('/gerente/dashboard')
def dashboard_gerente():
    if session.get('rol') not in ['gerente_evento', 'gerente_salon']:
        return redirect(url_for('login'))

    return render_template('gerente/dashboard.html')

###########Vista Administrador (Jefe)
@app.route('/administrador/dashboard')
def dashboard_jefe():
    if session.get('rol') != 'jefe':
        return redirect(url_for('login'))

    return render_template('administrador/dashboard.html')


#========================================================
# Ruta para El logOut
#========================================================
@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for('index'))



#========================================================
# Cobranzas
#========================================================

#========================================================
# Cobranzas
#========================================================
@app.route('/admin/cobranzas')
def admin_cobranzas():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()

        query = """
            SELECT p.id_proyecto, p.fecha_evento, p.anticipo, 
                   u.nombre, u.apaterno, u.amaterno
            FROM proyecto p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            ORDER BY p.id_proyecto
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        cobranzas = []
        hoy = datetime.today().date()  # fecha actual sin tiempo
        tres_semanas = timedelta(days=21)

        for r in rows:
            fecha_evento = r[1]
            if isinstance(fecha_evento, datetime):
                fecha_evento_date = fecha_evento.date()
                fecha_evento_str = fecha_evento_date.strftime('%Y-%m-%d')
            else:
                fecha_evento_date = fecha_evento
                fecha_evento_str = str(fecha_evento)

            # Estatus según fecha del evento
            if fecha_evento_date < hoy:
                estatus = "Pagado"
            else:
                estatus = "Pendiente"

            # Notificación para eventos en menos de 3 semanas
            dias_restantes = fecha_evento_date - hoy
            notificacion = ""
            if timedelta(0) <= dias_restantes <= tres_semanas:
                notificacion = f"¡Evento en {dias_restantes.days} días!"

            cobranzas.append({
                'id_proyecto': r[0],
                'fecha_evento': fecha_evento_str,
                'anticipo': r[2],
                'nombre': r[3],
                'apaterno': r[4],
                'amaterno': r[5],
                'estatus': estatus,
                'notificacion': notificacion
            })

        cursor.close()
        conexion.close()

        return render_template('administrador/cobranzas.html', cobranzas=cobranzas)
    except Exception as e:
        print("Error al cargar cobranzas:", e)
        return f"Error al cargar cobranzas: {e}"



# Este bloque debe ir al final del archivo
if __name__ == '__main__':
    app.run(debug=True)


