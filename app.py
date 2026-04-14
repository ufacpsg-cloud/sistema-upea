from flask import Flask, jsonify, request, render_template_string, make_response
import psycopg2
import os
import csv
from io import StringIO

app = Flask(__name__)

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
    <title>Panel UPEA - Gestión Académica</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; padding: 20px; margin: 0; }
        .container { max-width: 800px; margin: auto; }
        .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 20px; }
        h1 { color: #1a73e8; text-align: center; margin-bottom: 20px; }
        
        .search-box { display: flex; gap: 10px; margin-bottom: 10px; }
        input { flex: 1; padding: 15px; border: 2px solid #eee; border-radius: 10px; font-size: 16px; outline: none; }
        input:focus { border-color: #1a73e8; }
        
        .btn { padding: 12px 20px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; transition: 0.3s; color: white; }
        .btn-primary { background: #1a73e8; }
        .btn-secondary { background: #5f6368; width: 100%; margin-top: 10px; }
        .btn-excel { background: #1d6f42; margin-bottom: 15px; }
        
        .course-chip { background: #fbbc04; color: #3c4043; padding: 10px; border-radius: 8px; margin: 5px; cursor: pointer; display: inline-block; font-size: 14px; font-weight: bold; }
        .course-chip:hover { background: #f7a600; }
        
        .result-item { border-left: 6px solid #1a73e8; padding: 15px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
        .tag { background: #e8f0fe; color: #1a73e8; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .tag-estado { background: #fff3cd; color: #856404; text-transform: uppercase; }
        
        .btn-status { padding: 8px 12px; border-radius: 6px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🎓 Gestión UPEA</h1>
            <div class="search-box">
                <input type="text" id="busqueda" placeholder="Buscar por Nombre o CI...">
                <button class="btn btn-primary" onclick="buscar()">🔍</button>
            </div>
            <button class="btn btn-secondary" onclick="listarCursos()">📚 VER TODOS LOS CURSOS</button>
        </div>

        <div id="seccion-cursos" class="card" style="display:none;">
            <h3>Seleccione un curso:</h3>
            <div id="lista-cursos-chips"></div>
        </div>

        <div id="contenedor-reporte" style="text-align: right; display: none;">
            <button class="btn btn-excel" onclick="descargarExcel()">📊 Descargar Tabla para Excel</button>
        </div>

        <div id="resultados"></div>
    </div>

    <script>
        let filtroActual = "";

        function buscar(filtroExacto = false) {
            let texto = filtroExacto ? filtroExacto : document.getElementById('busqueda').value;
            filtroActual = texto;
            
            let divRes = document.getElementById('resultados');
            let divRepo = document.getElementById('contenedor-reporte');
            divRes.innerHTML = "<p style='text-align:center'>Cargando datos...</p>";

            // Si es filtro exacto (de un chip), usamos un parámetro extra
            let url = `/buscar?q=${encodeURIComponent(texto)}${filtroExacto ? '&exacto=true' : ''}`;

            fetch(url)
                .then(res => res.json())
                .then(data => {
                    if(data.length === 0) {
                        divRes.innerHTML = "<div class='card'><p style='text-align:center'>❌ Sin resultados para esta búsqueda</p></div>";
                        divRepo.style.display = "none";
                        return;
                    }
                    divRepo.style.display = "block";
                    let html = "";
                    data.forEach(alum => {
                        let esSec = alum.estado === 'secretaria';
                        html += `
                            <div class="card result-item">
                                <div>
                                    <div style="font-weight:bold;">👤 ${alum.nombre}</div>
                                    <div style="font-size:13px; color:#555;">🆔 CI: ${alum.carnet} | 📞 ${alum.celular}</div>
                                    <span class="tag">${alum.curso}</span>
                                    <span class="tag tag-estado">📍 ${alum.estado}</span>
                                </div>
                                <button class="btn btn-status" style="background:${esSec ? '#28a745' : '#f39c12'}" 
                                        onclick="cambiarEstado('${alum.carnet}', '${esSec ? 'enviado' : 'secretaria'}')">
                                    ${esSec ? 'Enviar' : 'Revertir'}
                                </button>
                            </div>`;
                    });
                    divRes.innerHTML = html;
                });
        }

        function listarCursos() {
            let divCursos = document.getElementById('seccion-cursos');
            let listaChips = document.getElementById('lista-cursos-chips');
            divCursos.style.display = "block";
            listaChips.innerHTML = "Cargando cursos...";

            fetch('/cursos_lista')
                .then(res => res.json())
                .then(data => {
                    listaChips.innerHTML = "";
                    data.forEach(c => {
                        listaChips.innerHTML += `<div class="course-chip" onclick="buscar('${c}')">${c}</div>`;
                    });
                });
        }

        function cambiarEstado(carnet, nuevoEstado) {
            fetch('/actualizar_estado', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({carnet: carnet, estado: nuevoEstado})
            }).then(() => buscar(filtroActual));
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
    
    # Si viene de un chip de curso, la búsqueda es exacta para no mezclar versiones
    if es_exacto:
        sql = """
            SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria')
            FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id
            WHERE c.nombre_curso = %s
            ORDER BY a.nombre_completo ASC
        """
        cur.execute(sql, (query,))
    else:
        sql = """
            SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria')
            FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id
            WHERE a.nombre_completo ILIKE %s OR a.carnet ILIKE %s OR c.nombre_curso ILIKE %s
            ORDER BY a.nombre_completo ASC LIMIT 100
        """
        p = f"%{query}%"
        cur.execute(sql, (p, p, p))
        
    datos = cur.fetchall()
    conn.close()
    return jsonify([{"nombre": r[0], "carnet": r[1], "celular": r[2], "curso": r[3], "estado": r[4]} for r in datos])

@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE inscripciones SET estado_certificacion = %s WHERE alumno_id = (SELECT id FROM alumnos WHERE carnet = %s)", 
               (data.get('estado'), data.get('carnet')))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/reporte/excel')
def generar_excel():
    query = request.args.get('q', '').strip()
    conn = get_db_connection()
    cur = conn.cursor()
    # En el excel siempre buscamos exacto o parecido según lo que el usuario esté viendo
    sql = """
        SELECT a.nombre_completo, a.carnet, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria')
        FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id
        WHERE c.nombre_curso = %s OR a.nombre_completo ILIKE %s OR a.carnet ILIKE %s
        ORDER BY c.nombre_curso, a.nombre_completo ASC
    """
    p = f"%{query}%"
    cur.execute(sql, (query, p, p))
    filas = cur.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    # Tabla dividida en 3 columnas principales + CI
    cw.writerow(['NOMBRE DEL ALUMNO', 'CARNET DE IDENTIDAD', 'NOMBRE DEL CURSO', 'ESTADO ACTUAL'])
    for r in filas:
        cw.writerow([r[0], r[1], r[2], r[3]])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=Reporte_UPEA.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    return output

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)