from flask import Flask, jsonify, request, render_template_string, make_response
import psycopg2
import os
import csv
from io import StringIO

app = Flask(__name__)

ADMIN_PIN = "1010" 

DATABASE_URL = "postgresql://neondb_owner:npg_ucDUbfEr29Bn@ep-small-base-ahys4mod-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# --- DISEÑO CON ACTUALIZACIÓN POR CURSO ESPECÍFICO ---
HTML_APP = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel Gestión UPEA</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f9; padding: 20px; margin: 0; }
        .container { max-width: 900px; margin: auto; }
        .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
        h1 { color: #1a73e8; text-align: center; }
        .search-box { display: flex; gap: 10px; margin-bottom: 10px; }
        input { flex: 1; padding: 15px; border: 2px solid #ddd; border-radius: 10px; font-size: 16px; outline: none; }
        .btn { padding: 12px 20px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; color: white; }
        .btn-primary { background: #1a73e8; }
        .btn-secondary { background: #5f6368; width: 100%; margin-top: 10px; }
        .btn-excel { background: #1d6f42; margin-bottom: 10px; float: right; }
        #seccion-cursos { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; max-height: 300px; overflow-y: auto; padding: 10px; }
        .course-chip { background: #fff; border: 2px solid #fbbc04; color: #3c4043; padding: 12px; border-radius: 10px; cursor: pointer; text-align: center; font-size: 13px; font-weight: bold; }
        .result-item { border-left: 6px solid #1a73e8; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
        .tag { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; margin-top: 5px; }
        .tag-secretaria { background: #eee; color: #666; }
        .tag-enviado { background: #d4edda; color: #155724; }
        .tag-recogido { background: #cfe2ff; color: #084298; }
        .btn-group { display: flex; flex-direction: column; gap: 5px; }
        .btn-status { padding: 8px 15px; border-radius: 6px; font-size: 11px; text-transform: uppercase; border: none; cursor: pointer; color: white; width: 160px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🎓 Gestión UPEA</h1>
            <div class="search-box">
                <input type="text" id="busqueda" placeholder="Nombre, CI o Celular..." onkeypress="if(event.key==='Enter') buscar()">
                <button class="btn btn-primary" onclick="buscar()">🔍 BUSCAR</button>
            </div>
            <button class="btn btn-secondary" onclick="toggleCursos()">📚 MOSTRAR LISTA DE CURSOS</button>
            <div id="wrapper-cursos" style="display:none; margin-top:15px;">
                <div id="seccion-cursos"></div>
            </div>
        </div>
        <div id="cont-excel" style="display:none; overflow: hidden;">
            <button class="btn btn-excel" onclick="descargarExcel()">📊 Descargar Excel</button>
        </div>
        <div id="resultados"></div>
    </div>

    <script>
        let filtroActual = "";

        function toggleCursos() {
            let wrapper = document.getElementById('wrapper-cursos');
            wrapper.style.display = wrapper.style.display === "none" ? "block" : "none";
            if(wrapper.style.display === "block") listarCursos();
        }

        function listarCursos() {
            fetch('/cursos_lista').then(res => res.json()).then(data => {
                let div = document.getElementById('seccion-cursos');
                div.innerHTML = "";
                data.forEach(c => {
                    let chip = document.createElement('div');
                    chip.className = 'course-chip'; chip.innerText = c;
                    chip.onclick = () => { buscar(c, true); document.getElementById('wrapper-cursos').style.display = "none"; };
                    div.appendChild(chip);
                });
            });
        }

        function buscar(textoBusqueda = false, esExacto = false) {
            let texto = textoBusqueda ? textoBusqueda : document.getElementById('busqueda').value;
            filtroActual = texto;
            let divRes = document.getElementById('resultados');
            let url = `/buscar?q=${encodeURIComponent(texto)}${esExacto ? '&exacto=true' : ''}`;

            fetch(url).then(res => res.json()).then(data => {
                document.getElementById('cont-excel').style.display = data.length > 0 ? "block" : "none";
                let html = "";
                data.forEach(alum => {
                    let st = alum.estado;
                    let cur = alum.curso; 
                    let tagClass = "tag-" + st;
                    let btnRecogidoHTML = "";
                    let btnEnviadoHTML = "";
                    
                    // --- CORRECCIÓN AQUÍ: ESCAPAR COMILLAS Y CREAR LLAVES SEGURAS ---
                    let nomEscapado = alum.nombre.replace(/'/g, "\\'");
                    let ciSeguro = alum.carnet ? alum.carnet : "";

                    if (st === 'recogido') {
                        btnRecogidoHTML = `<button class="btn-status" style="background:#dc3545" onclick="cambiarEstado('${ciSeguro}', '${cur}', 'secretaria', false, '${nomEscapado}')">❌ No Recogido</button>`;
                        btnEnviadoHTML = `<button class="btn-status" style="background:#6c757d" disabled>Enviado 🔐</button>`;
                    } else if (st === 'enviado') {
                        btnRecogidoHTML = `<button class="btn-status" style="background:#0d6efd" onclick="cambiarEstado('${ciSeguro}', '${cur}', 'recogido', false, '${nomEscapado}')">Recogido</button>`;
                        btnEnviadoHTML = `<button class="btn-status" style="background:#f39c12" onclick="cambiarEstado('${ciSeguro}', '${cur}', 'secretaria', true, '${nomEscapado}')">Regresar a Sec 🔐</button>`;
                    } else {
                        btnRecogidoHTML = `<button class="btn-status" style="background:#0d6efd" onclick="cambiarEstado('${ciSeguro}', '${cur}', 'recogido', false, '${nomEscapado}')">Recogido</button>`;
                        btnEnviadoHTML = `<button class="btn-status" style="background:#28a745" onclick="cambiarEstado('${ciSeguro}', '${cur}', 'enviado', true, '${nomEscapado}')">Enviado 🔐</button>`;
                    }

                    html += `
                        <div class="card result-item">
                            <div>
                                <div style="font-weight:bold;">👤 ${alum.nombre}</div>
                                <div style="font-size:12px; color:#666;">🆔 CI: ${alum.carnet || 'SIN CARNET'} | 📞 ${alum.celular || 'SIN CELULAR'}</div>
                                <div style="margin-top:5px;">
                                    <span class="tag" style="background:#e8f0fe; color:#1a73e8;">${cur}</span>
                                    <span class="tag ${tagClass}">📍 ${st.toUpperCase()}</span>
                                </div>
                            </div>
                            <div class="btn-group">
                                ${btnRecogidoHTML}
                                ${btnEnviadoHTML}
                            </div>
                        </div>`;
                });
                divRes.innerHTML = html || "<p style='text-align:center'>No hay resultados</p>";
            });
        }

        function cambiarEstado(carnet, curso, nuevoEstado, requierePin, nombreAlumno) {
            let pin = "";
            if(requierePin) {
                pin = prompt("🔐 PIN administrativo:");
                if(!pin) return;
            }
            fetch('/actualizar_estado', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({carnet: carnet, nombre: nombreAlumno, curso: curso, estado: nuevoEstado, pin: pin})
            }).then(res => res.json()).then(data => {
                if(data.status === 'success') buscar(filtroActual);
                else alert("❌ " + (data.message || "Error"));
            });
        }

        function descargarExcel() { window.location.href = `/reporte/excel?q=${encodeURIComponent(filtroActual)}`; }
    </script>
</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML_APP)

@app.route('/cursos_lista')
def cursos_lista():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT DISTINCT nombre_curso FROM cursos ORDER BY nombre_curso ASC")
    cursos = [r[0] for r in cur.fetchall()]
    conn.close(); return jsonify(cursos)

@app.route('/buscar')
def buscar_alumno():
    query = request.args.get('q', '').strip()
    es_exacto = request.args.get('exacto', 'false') == 'true'
    conn = get_db_connection(); cur = conn.cursor()
    if es_exacto:
        sql = "SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria') FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id WHERE c.nombre_curso = %s ORDER BY a.nombre_completo ASC"
        cur.execute(sql, (query,))
    else:
        sql = "SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria') FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id WHERE a.nombre_completo ILIKE %s OR a.carnet ILIKE %s OR a.celular ILIKE %s OR c.nombre_curso ILIKE %s ORDER BY a.nombre_completo ASC LIMIT 100"
        p = f"%{query}%"; cur.execute(sql, (p, p, p, p))
    datos = cur.fetchall(); conn.close()
    return jsonify([{"nombre": r[0], "carnet": r[1], "celular": r[2], "curso": r[3], "estado": r[4]} for r in datos])

@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    data = request.json
    nuevo = data.get('estado')
    curso_nombre = data.get('curso', '').strip()
    carnet_alumno = data.get('carnet')
    nombre_alumno = data.get('nombre', '').strip() 
    pin_ingresado = data.get('pin', '')

    if nuevo == 'enviado' or (nuevo == 'secretaria' and pin_ingresado != ''):
        if pin_ingresado != ADMIN_PIN:
            return jsonify({"status": "error", "message": "PIN incorrecto"}), 403

    if carnet_alumno:
        carnet_alumno = str(carnet_alumno).strip()
        if carnet_alumno.lower() in ['', 'none', 'null']:
            carnet_alumno = None
    else:
        carnet_alumno = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if carnet_alumno:
            sql_alumno = "SELECT id FROM alumnos WHERE TRIM(carnet) ILIKE %s LIMIT 1"
            param_alumno = carnet_alumno
        else:
            sql_alumno = "SELECT id FROM alumnos WHERE TRIM(nombre_completo) ILIKE %s LIMIT 1"
            param_alumno = nombre_alumno

        sql = f"""
            UPDATE inscripciones 
            SET estado_certificacion = %s 
            WHERE alumno_id = ({sql_alumno})
              AND curso_id = (SELECT id FROM cursos WHERE TRIM(nombre_curso) ILIKE %s LIMIT 1)
        """
        
        cur.execute(sql, (nuevo, param_alumno, f"%{curso_nombre}%"))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/reporte/excel')
def generar_excel():
    query = request.args.get('q', '').strip()
    conn = get_db_connection(); cur = conn.cursor()
    sql = "SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria') FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id WHERE c.nombre_curso = %s OR a.nombre_completo ILIKE %s OR a.carnet ILIKE %s OR a.celular ILIKE %s ORDER BY c.nombre_curso, a.nombre_completo ASC"
    p = f"%{query}%"; cur.execute(sql, (query, p, p, p))
    filas = cur.fetchall(); conn.close()
    si = StringIO(); cw = csv.writer(si)
    cw.writerow(['ALUMNO', 'CI', 'CELULAR', 'CURSO', 'ESTADO'])
    for r in filas: cw.writerow([r[0], r[1], r[2], r[3], r[4]])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=Reporte_UPEA.csv"
    output.headers["Content-type"] = "text/csv"; return output

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
