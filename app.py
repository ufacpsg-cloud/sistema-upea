from flask import Flask, jsonify, request, render_template_string, make_response
import psycopg2
import os
from fpdf import FPDF

app = Flask(__name__)

# Tu URL de Neon (Se mantiene igual)
DATABASE_URL = "postgresql://neondb_owner:npg_ucDUbfEr29Bn@ep-small-base-ahys4mod-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# --- DISEÑO MEJORADO CON BOTÓN DE REPORTE ---
HTML_APP = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consulta UPEA</title>
    <style>
        body { font-family: sans-serif; background: #f0f2f5; padding: 20px; margin: 0; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1 { color: #1a73e8; text-align: center; margin-bottom: 5px; }
        input { width: 100%; padding: 15px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; margin-top: 10px; cursor: pointer; transition: 0.3s; }
        button:hover { background: #1557b0; }
        .result-item { border-left: 5px solid #1a73e8; padding-left: 15px; position: relative; }
        .tag { background: #e8f0fe; color: #1a73e8; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; display: inline-block; margin-top: 5px; }
        .tag-estado { background: #fff3cd; color: #856404; }
        .btn-pdf { background: #28a745; margin-top: 15px; width: auto; padding: 10px 20px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🎓 Buscador UPEA</h1>
        <p style="text-align:center; color:#666; margin-top:0;">Gestión de Inscritos y Certificados</p>
        <input type="text" id="busqueda" placeholder="Escribe Nombre, CI, Celular o NOMBRE DEL CURSO...">
        <button onclick="buscar()">🔍 BUSCAR AHORA</button>
    </div>
    <div id="resultados"></div>

    <script>
        function buscar() {
            let texto = document.getElementById('busqueda').value;
            let divRes = document.getElementById('resultados');
            divRes.innerHTML = "<p style='text-align:center'>Buscando en la nube...</p>";

            fetch('/buscar?q=' + encodeURIComponent(texto))
                .then(res => res.json())
                .then(data => {
                    if(data.length === 0) {
                        divRes.innerHTML = "<div class='card'><p style='text-align:center'>❌ No se encontraron coincidencias</p></div>";
                        return;
                    }
                    
                    // Si buscamos por curso, mostramos opción de imprimir lista completa
                    let html = "";
                    let cursoDetectado = data[0].curso;

                    html += `<div style="margin-bottom:10px; text-align:right;">
                                <button class="btn-pdf" onclick="descargarPDF('${texto}')">📄 Exportar PDF de esta búsqueda</button>
                             </div>`;

                    data.forEach(alum => {
                        html += `<div class="card result-item">
                                    <div style="font-weight:bold; font-size:1.1em">👤 ${alum.nombre}</div>
                                    <div>🆔 CI: ${alum.carnet} | 📞 Cel: ${alum.celular}</div>
                                    <div>
                                        <span class="tag">${alum.curso}</span>
                                        <span class="tag tag-estado">📍 Estado: ${alum.estado}</span>
                                    </div>
                                 </div>`;
                    });
                    divRes.innerHTML = html;
                })
                .catch(err => divRes.innerHTML = "<p style='text-align:center'>Error de conexión</p>");
        }

        function descargarPDF(query) {
            window.location.href = `/reporte/pdf?q=` + encodeURIComponent(query);
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
    # SQL mejorado: Ahora busca también por el nombre del curso
    sql = """
        SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, 
               COALESCE(i.estado_certificacion, 'secretaria')
        FROM inscripciones i
        JOIN alumnos a ON i.alumno_id = a.id
        JOIN cursos c ON i.curso_id = c.id
        WHERE a.nombre_completo ILIKE %s 
           OR a.carnet ILIKE %s 
           OR c.nombre_curso ILIKE %s
        ORDER BY a.nombre_completo ASC
        LIMIT 100
    """
    param = f"%{query}%"
    cur.execute(sql, (param, param, param))
    datos = cur.fetchall()
    conn.close()
    
    lista = [{"nombre": r[0], "carnet": r[1] or "S/D", "celular": r[2] or "S/D", "curso": r[3], "estado": r[4]} for r in datos]
    return jsonify(lista)

@app.route('/reporte/pdf')
def generar_pdf():
    try:
        query = request.args.get('q', '').strip()
        conn = get_db_connection()
        if not conn:
            return "Error de conexión a la base de datos", 500
            
        cur = conn.cursor()
        
        # SQL: Buscamos por nombre, CI o nombre del curso
        sql = """
            SELECT a.nombre_completo, a.carnet, c.nombre_curso, 
                   COALESCE(i.estado_certificacion, 'secretaria')
            FROM inscripciones i
            JOIN alumnos a ON i.alumno_id = a.id
            JOIN cursos c ON i.curso_id = c.id
            WHERE a.nombre_completo ILIKE %s 
               OR a.carnet ILIKE %s 
               OR c.nombre_curso ILIKE %s
            ORDER BY c.nombre_curso, a.nombre_completo ASC
        """
        param = f"%{query}%"
        cur.execute(sql, (param, param, param))
        filas = cur.fetchall()
        conn.close()

        # Configuración del PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Título Principal
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(190, 10, "REPORTE DE INSCRITOS - UPEA", ln=True, align='C')
        
        # Subtítulo con el filtro usado
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(190, 7, f"Filtro aplicado: {query}", ln=True, align='C')
        pdf.ln(5)

        # Encabezado de la Tabla (Colores institucionales)
        pdf.set_fill_color(26, 115, 232) # Azul
        pdf.set_text_color(255, 255, 255) # Blanco
        pdf.set_font("Helvetica", "B", 10)
        
        pdf.cell(80, 10, " NOMBRE COMPLETO", 1, 0, 'L', True)
        pdf.cell(30, 10, " CI", 1, 0, 'C', True)
        pdf.cell(50, 10, " CURSO", 1, 0, 'L', True)
        pdf.cell(30, 10, " ESTADO", 1, 1, 'C', True)

        # Cuerpo de la Tabla
        pdf.set_text_color(0, 0, 0) # Volver a negro
        pdf.set_font("Helvetica", "", 9)
        
        for r in filas:
            # Limpieza de caracteres para evitar error 502 (tildes y Ñ)
            nombre = str(r[0]).encode('latin-1', 'replace').decode('latin-1')
            ci = str(r[1]).encode('latin-1', 'replace').decode('latin-1')
            curso = str(r[2]).encode('latin-1', 'replace').decode('latin-1')
            estado = str(r[3]).encode('latin-1', 'replace').decode('latin-1')
            
            # Dibujar celdas (usamos MultiCell si el nombre es muy largo, o truncamos)
            pdf.cell(80, 8, nombre[:40], 1)
            pdf.cell(30, 8, ci, 1, 0, 'C')
            pdf.cell(50, 8, curso[:25], 1)
            pdf.cell(30, 8, estado.upper(), 1, 1, 'C')

        # Generar la respuesta del archivo
        response = make_response(pdf.output(dest='S'))
        response.headers.set('Content-Disposition', 'attachment', filename=f'reporte_upea.pdf')
        response.headers.set('Content-Type', 'application/pdf')
        return response

    except Exception as e:
        print(f"Error crítico en PDF: {e}")
        return f"Error al generar reporte: {str(e)}", 500
    
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)