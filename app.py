from flask import Flask, jsonify, request, render_template_string, make_response
import psycopg2
import os
from fpdf import FPDF

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
    <title>Sistema UPEA - Gestión</title>
    <style>
        body { font-family: sans-serif; background: #f0f2f5; padding: 20px; margin: 0; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1 { color: #1a73e8; text-align: center; margin-bottom: 5px; }
        input { width: 100%; padding: 15px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box; }
        .btn-buscar { width: 100%; padding: 15px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; margin-top: 10px; cursor: pointer; }
        .btn-pdf { background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; margin-bottom: 20px; }
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
        <button class="btn-buscar" onclick="buscar()">🔍 BUSCAR</button>
    </div>

    <div id="contenedor-pdf" style="text-align: right; display: none;">
        <button class="btn-pdf" onclick="descargarPDF()">📄 Descargar Reporte PDF</button>
    </div>

    <div id="resultados"></div>

    <script>
        let ultimaBusqueda = "";

        function buscar() {
            let texto = document.getElementById('busqueda').value;
            ultimaBusqueda = texto;
            let divRes = document.getElementById('resultados');
            let divPdf = document.getElementById('contenedor-pdf');
            
            divRes.innerHTML = "<p style='text-align:center'>Buscando...</p>";

            fetch('/buscar?q=' + encodeURIComponent(texto))
                .then(res => res.json())
                .then(data => {
                    if(data.length === 0) {
                        divRes.innerHTML = "<div class='card'><p style='text-align:center'>❌ Sin resultados</p></div>";
                        divPdf.style.display = "none";
                        return;
                    }
                    
                    divPdf.style.display = "block";
                    let html = "";
                    data.forEach(alum => {
                        let esSecretaria = alum.estado === 'secretaria';
                        let btnTexto = esSecretaria ? '✅ Marcar como ENVIADO' : '🔙 Mover a SECRETARÍA';
                        let btnColor = esSecretaria ? '#28a745' : '#f39c12';
                        let proxEstado = esSecretaria ? 'enviado' : 'secretaria';

                        html += `<div class="card result-item">
                                    <div style="font-weight:bold; font-size:1.1em">👤 ${alum.nombre}</div>
                                    <div>🆔 CI: ${alum.carnet} | 📞 Cel: ${alum.celular}</div>
                                    <div>
                                        <span class="tag">${alum.curso}</span>
                                        <span class="tag tag-estado">📍 Estado: ${alum.estado}</span>
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

        function descargarPDF() {
            window.location.href = '/reporte/pdf?q=' + encodeURIComponent(ultimaBusqueda);
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

@app.route('/reporte/pdf')
def generar_pdf():
    try:
        query = request.args.get('q', '').strip()
        conn = get_db_connection()
        cur = conn.cursor()
        sql = """
            SELECT a.nombre_completo, a.carnet, c.nombre_curso, i.estado_certificacion
            FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id
            JOIN cursos c ON i.curso_id = c.id
            WHERE a.nombre_completo ILIKE %s OR a.carnet ILIKE %s OR c.nombre_curso ILIKE %s
            ORDER BY a.nombre_completo ASC
        """
        p = f"%{query}%"
        cur.execute(sql, (p, p, p))
        filas = cur.fetchall()
        conn.close()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(190, 10, "REPORTE UPEA", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(90, 10, "Nombre", 1)
        pdf.cell(40, 10, "CI", 1)
        pdf.cell(60, 10, "Estado", 1, 1)

        pdf.set_font("Helvetica", "", 9)
        for r in filas:
            # Limpieza extrema para evitar error 502
            n = str(r[0]).encode('ascii', 'ignore').decode('ascii')
            c = str(r[1]).encode('ascii', 'ignore').decode('ascii')
            e = str(r[3]).encode('ascii', 'ignore').decode('ascii')
            pdf.cell(90, 8, n[:40], 1)
            pdf.cell(40, 8, c, 1)
            pdf.cell(60, 8, e, 1, 1)

        response = make_response(pdf.output(dest='S'))
        response.headers.set('Content-Disposition', 'attachment', filename='reporte.pdf')
        response.headers.set('Content-Type', 'application/pdf')
        return response
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)