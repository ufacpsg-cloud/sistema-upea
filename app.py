from flask import Flask, jsonify, request, render_template_string, make_response
import psycopg2
import os
import csv
from io import StringIO

app = Flask(__name__)

# Configura aquí tu PIN de seguridad (Cámbialo por el que quieras)
ADMIN_PIN = "1375" 

DATABASE_URL = "postgresql://neondb_owner:npg_ucDUbfEr29Bn@ep-small-base-ahys4mod-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# --- DISEÑO DE LA APP ---
HTML_APP = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel Privado UPEA</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f4f8; padding: 20px; margin: 0; }
        .container { max-width: 900px; margin: auto; }
        .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
        h1 { color: #1a73e8; text-align: center; margin-bottom: 20px; }
        
        .search-box { display: flex; gap: 10px; margin-bottom: 10px; }
        input { flex: 1; padding: 15px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 16px; outline: none; }
        input:focus { border-color: #1a73e8; }
        
        .btn { padding: 12px 20px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; color: white; transition: 0.3s; }
        .btn-primary { background: #1a73e8; }
        .btn-secondary { background: #5f6368; width: 100%; margin-top: 10px; }
        .btn-excel { background: #1d6f42; margin-bottom: 15px; }
        
        #seccion-cursos { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; max-height: 300px; overflow-y: auto; padding: 10px; }
        .course-chip { background: #fff; border: 2px solid #fbbc04; color: #3c4043; padding: 12px; border-radius: 10px; cursor: pointer; text-align: center; font-size: 13px; font-weight: bold; transition: 0.2s; }
        .course-chip:hover { background: #fbbc04; transform: translateY(-2px); }
        
        .result-item { border-left: 6px solid #1a73e8; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
        .tag { background: #e8f0fe; color: #1a73e8; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .tag-estado { background: #fff3cd; color: #856404; text-transform: uppercase; }
        
        .btn-status { padding: 8px 15px; border-radius: 6px; font-size: 11px; text-transform: uppercase; border: none; cursor: pointer; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🎓 Gestión de Cursos UPEA</h1>
            <div class="search-box">
                <input type="text" id="busqueda" placeholder="Buscar por Nombre, CI o Celular ...">
                <button class="btn btn-primary" onclick="buscar()">🔍</button>
            </div>
            <button id="btn-lista-maestra" class="btn btn-secondary" onclick="toggleCursos()">📚 MOSTRAR LISTA DE CURSOS</button>
            
            <div id="wrapper-cursos" style="display:none; margin-top:15px;">
                <div id="seccion-cursos"></div>
            </div>
        </div>

        <div id="contenedor-reporte" style="text-align: right; display: none;">
            <button class="btn btn-excel" onclick="descargarExcel()">📊 Descargar este Curso para Excel</button>
        </div>

        <div id="resultados"></div>
    </div>

    <script>
        let filtroActual = "";

        function toggleCursos() {
            let wrapper = document.getElementById('wrapper-cursos');
            let btn = document.getElementById('btn-lista-maestra');
            
            if(wrapper.style.display === "none") {
                wrapper.style.display = "block";
                btn.innerText = "🔼 ESCONDER LISTA DE CURSOS";
                listarCursos();
            } else {
                wrapper.style.display = "none";
                btn.innerText = "📚 MOSTRAR LISTA DE CURSOS";
            }
        }

        function listarCursos() {
            let listaDiv = document.getElementById('seccion-cursos');
            listaDiv.innerHTML = "Cargando...";
            fetch('/cursos_lista')
                .then(res => res.json())
                .then(data => {
                    listaDiv.innerHTML = "";
                    data.forEach(c => {
                        let chip = document.createElement('div');
                        chip.className = 'course-chip';
                        chip.innerText = c;
                        chip.onclick = () => {
                            buscar(c);
                            document.getElementById('wrapper-cursos').style.display = "none";
                            document.getElementById('btn-lista-maestra').innerText = "📚 MOSTRAR LISTA DE CURSOS";
                        };
                        listaDiv.appendChild(chip);
                    });
                });
        }

        function buscar(filtroExacto = false) {
            let texto = filtroExacto ? filtroExacto : document.getElementById('busqueda').value;
            filtroActual = texto;
            let divRes = document.getElementById('resultados');
            let divRepo = document.getElementById('contenedor-reporte');
            divRes.innerHTML = "<p style='text-align:center'>Obteniendo alumnos...</p>";

            let url = `/buscar?q=${encodeURIComponent(texto)}${filtroExacto ? '&exacto=true' : ''}`;

            fetch(url)
                .then(res => res.json())
                .then(data => {
                    if(data.length === 0) {
                        divRes.innerHTML = "<div class='card'><p style='text-align:center'>❌ No hay inscritos</p></div>";
                        divRepo.style.display = "none";
                        return;
                    }
                    divRepo.style.display = "block";
                    let html = `<h3>Resultados para: ${texto}</h3>`;
                    data.forEach(alum => {
                        let esSec = alum.estado === 'secretaria';
                        html += `
                            <div class="card result-item">
                                <div>
                                    <div style="font-weight:bold;">👤 ${alum.nombre}</div>
                                    <div style="font-size:13px; color:#555; margin: 3px 0;">
                                        🆔 CI: ${alum.carnet} | 📞 Celular: ${alum.celular}
                                    </div>
                                    <span class="tag">${alum.curso}</span>
                                    <span class="tag tag-estado">${alum.estado}</span>
                                </div>
                                <button class="btn-status" style="background:${esSec ? '#28a745' : '#f39c12'}" 
                                        onclick="intentarCambio('${alum.carnet}', '${esSec ? 'enviado' : 'secretaria'}')">
                                    ${esSec ? 'Enviar' : 'Revertir'}
                                </button>
                            </div>`;
                    });
                    divRes.innerHTML = html;
                });
        }

        function intentarCambio(carnet, nuevoEstado) {
            let pin = prompt("🔐 Ingrese el PIN de administrador para cambiar el estado:");
            if(pin === null) return;

            fetch('/actualizar_estado', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({carnet: carnet, estado: nuevoEstado, pin: pin})
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'success') {
                    buscar(filtroActual);
                } else {
                    alert("❌ PIN Incorrecto o error de acceso.");
                }
            });
        }

        function descargarExcel() {
            window.location.href = `/reporte/excel?q=${encodeURIComponent(filtroActual)}`;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_APP)

@app.route('/cursos_lista')
def cursos_lista():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT nombre_curso FROM cursos ORDER BY nombre_curso ASC")
    cursos = [r[0] for r in cur.fetchall()]
    conn.close()
    return jsonify(cursos)

@app.route('/buscar')
def buscar_alumno():
    query = request.args.get('q', '').strip()
    es_exacto = request.args.get('exacto', 'false') == 'true'
    conn = get_db_connection()
    cur = conn.cursor()
    
    if es_exacto:
        # Búsqueda exacta por curso (cuando presionas un chip)
        sql = """SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria')
                 FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id
                 WHERE c.nombre_curso = %s ORDER BY a.nombre_completo ASC"""
        cur.execute(sql, (query,))
    else:
        # Búsqueda general: Nombre, CI o CELULAR (Añadido nuevamente)
        sql = """SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria')
                 FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id
                 WHERE a.nombre_completo ILIKE %s 
                    OR a.carnet ILIKE %s 
                    OR a.celular ILIKE %s 
                    OR c.nombre_curso ILIKE %s 
                 ORDER BY a.nombre_completo ASC LIMIT 100"""
        p = f"%{query}%"
        cur.execute(sql, (p, p, p, p))
        
    datos = cur.fetchall()
    conn.close()
    return jsonify([{"nombre": r[0], "carnet": r[1], "celular": r[2], "curso": r[3], "estado": r[4]} for r in datos])

@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    data = request.json
    nuevo = data.get('estado')
    curso_nombre = data.get('curso')
    carnet_alumno = data.get('carnet')
    pin_ingresado = data.get('pin', '')

    if nuevo == 'enviado' or (nuevo == 'secretaria' and pin_ingresado != ''):
        if pin_ingresado != ADMIN_PIN:
            return jsonify({"status": "error", "message": "PIN incorrecto"}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Filtramos por Alumno Y por Curso para no afectar otras inscripciones
        sql = """
            UPDATE inscripciones 
            SET estado_certificacion = %s 
            WHERE alumno_id = (SELECT id FROM alumnos WHERE carnet = %s)
            AND curso_id = (SELECT id FROM cursos WHERE nombre_curso = %s)
        """
        cur.execute(sql, (nuevo, carnet_alumno, curso_nombre))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/reporte/excel')
def generar_excel():
    query = request.args.get('q', '').strip()
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """SELECT a.nombre_completo, a.carnet, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria')
             FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id
             WHERE c.nombre_curso = %s OR a.nombre_completo ILIKE %s OR a.carnet ILIKE %s
             ORDER BY c.nombre_curso, a.nombre_completo ASC"""
    p = f"%{query}%"
    cur.execute(sql, (query, p, p))
    filas = cur.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['NOMBRE DEL ALUMNO', 'CARNET DE IDENTIDAD', 'NOMBRE DEL CURSO', 'ESTADO ACTUAL'])
    for r in filas:
        cw.writerow([r[0], r[1], r[2], r[3]])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=Reporte_UPEA.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)