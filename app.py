from flask import Flask, jsonify, request, render_template_string, make_response
import psycopg2
import os
import csv
from io import StringIO

app = Flask(__name__)

# URL de tu base de datos en Neon
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
    <title>Sistema UPEA - Gestión de Inscritos</title>
    <style>
        body { font-family: sans-serif; background: #f0f2f5; padding: 20px; margin: 0; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1 { color: #1a73e8; text-align: center; margin-bottom: 5px; }
        input { width: 100%; padding: 15px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box; }
        .btn-buscar { width: 100%; padding: 15px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; margin-top: 10px; cursor: pointer; }
        .btn-excel { background: #1d6f42; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; margin-bottom: 20px; }
        .result-item { border-left: 5px solid #1a73e8; padding-left: 15px; margin-bottom: 15px; }
        .tag { background: #e8f0fe; color: #1a73e8; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; display: inline-block; margin-top: 5px; }
        .tag-estado { background: #fff3cd; color: #856404; }
        .btn-accion { padding: 8px 12px; border: none; border-radius: 5px; color: white; cursor: pointer; margin-top: 10px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🎓 Buscador UPEA</h1>
        <p style="text-align:center; color:#666; margin-top:0;">Gestión de Certificados y Cursos</p>
        <input type="text" id="busqueda" placeholder="Nombre, CI o nombre del curso...">
        <button class="btn-buscar" onclick="buscar()">🔍 BUSCAR AHORA</button>
    </div>

    <div id="contenedor-reporte" style="text-align: right; display: none;">
        <button class="btn-excel" onclick="descargarExcel()">📊 Descargar Lista para Excel</button>
    </div>

    <div id="resultados"></div>

    <script>
        let ultimaBusqueda = "";

        function buscar() {
            let texto = document.getElementById('busqueda').value;
            ultimaBusqueda = texto;
            let divRes = document.getElementById('resultados');
            let divRepo = document.getElementById('contenedor-reporte');
            
            divRes.innerHTML = "<p style='text-align:center'>Buscando en la base de datos...</p>";

            fetch('/buscar?q=' + encodeURIComponent(texto))
                .then(res => res.json())
                .then(data => {
                    if(data.length === 0) {
                        divRes.innerHTML = "<div class='card'><p style='text-align:center'>❌ No se encontraron resultados</p></div>";
                        divRepo.style.display = "none";
                        return;
                    }
                    
                    divRepo.style.display = "block";
                    let html = "";
                    data.forEach(alum => {
                        let esSecretaria = alum.estado === 'secretaria';
                        let btnTexto = esSecretaria ? '✅ Enviar Certificado' : '🔙 Regresar a Secretaría';
                        let btnColor = esSecretaria ? '#28a745' : '#f39c12';
                        let proxEstado = esSecretaria ? 'enviado' : 'secretaria';

                        html += `<div class="card result-item">
                                    <div style="font-weight:bold; font-size:1.1em">👤 ${alum.nombre}</div>
                                    <div>🆔 CI: ${alum.carnet} | 📞 Cel: ${alum.celular}</div>
                                    <div>
                                        <span class="tag">${alum.curso}</span>
                                        <span class="tag tag-estado">📍 Estado: ${alum.estado.toUpperCase()}</span>
                                    </div>
                                    <button class="btn-accion" style="background:${btnColor}" 
                                            onclick="cambiarEstado('${alum.carnet}', '${proxEstado}')">
                                        ${btnTexto}
                                    </button>
                                 </div>`;
                    });
                    divRes.innerHTML = html;
                });
        }

        function cambiarEstado(carnet, nuevoEstado) {
            fetch('/actualizar_estado', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({carnet: carnet, estado: nuevoEstado})
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'success') buscar();
                else alert("Error al actualizar");
            });
        }

        function descargarExcel() {
            window.location.href = '/reporte/excel?q=' + encodeURIComponent(ultimaBusqueda);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_APP)

@app.route('/buscar')
def buscar_alumno():
    query = request.args.get('q', '').strip()
    conn = get_db_connection()
    if not conn: return jsonify([])
    cur = conn.cursor()
    sql = """
        SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, 
               COALESCE(i.estado_certificacion, 'secretaria')
        FROM inscripciones i
        JOIN alumnos a ON i.alumno_id = a.id
        JOIN cursos c ON i.curso_id = c.id
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
    cur.execute("""
        UPDATE inscripciones SET estado_certificacion = %s 
        WHERE alumno_id = (SELECT id FROM alumnos WHERE carnet = %s)
    """, (data.get('estado'), data.get('carnet')))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/reporte/excel')
def generar_excel():
    try:
        query = request.args.get('q', '').strip()
        conn = get_db_connection()
        cur = conn.cursor()
        sql = """
            SELECT a.nombre_completo, a.carnet, c.nombre_curso, 
                   COALESCE(i.estado_certificacion, 'secretaria')
            FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id
            JOIN cursos c ON i.curso_id = c.id
            WHERE a.nombre_completo ILIKE %s OR a.carnet ILIKE %s OR c.nombre_curso ILIKE %s
            ORDER BY c.nombre_curso, a.nombre_completo ASC
        """
        p = f"%{query}%"
        cur.execute(sql, (p, p, p))
        filas = cur.fetchall()
        conn.close()

        # Generar CSV en memoria
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['Nombre Completo', 'Carnet', 'Curso', 'Estado'])
        for r in filas:
            cw.writerow([r[0], r[1], r[2], r[3]])

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=reporte_{query}.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)