from flask import Flask, jsonify, request, render_template_string
import psycopg2
import os

app = Flask(__name__)

DATABASE_URL = "postgresql://neondb_owner:npg_ucDUbfEr29Bn@ep-small-base-ahys4mod-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# --- DISEÑO DE LA APP (Igual que antes) ---
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
        h1 { color: #1a73e8; text-align: center; }
        input { width: 100%; padding: 15px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; margin-top: 10px; cursor: pointer; }
        .result-item { border-bottom: 1px solid #eee; padding: 15px 0; }
        .tag { background: #e8f0fe; color: #1a73e8; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🎓 Buscador UPEA</h1>
        <p style="text-align:center; color:#666;">Base de Datos Actualizada</p>
        <input type="text" id="busqueda" placeholder="Escribe Nombre, CI o Celular...">
        <button onclick="buscar()">🔍 BUSCAR AHORA</button>
    </div>
    <div id="resultados"></div>

    <script>
        const API_URL = ""; 
        function buscar() {
            let texto = document.getElementById('busqueda').value;
            let divRes = document.getElementById('resultados');
            divRes.innerHTML = "<p style='text-align:center'>Buscando en la nube...</p>";

            fetch(API_URL + '/buscar?q=' + texto)
                .then(res => res.json())
                .then(data => {
                    if(data.length === 0) {
                        divRes.innerHTML = "<div class='card'><p style='text-align:center'>❌ No encontrado</p></div>";
                        return;
                    }
                    let html = "";
                    data.forEach(alum => {
                        html += `<div class="card result-item">
                                    <div style="font-weight:bold; font-size:1.1em">👤 ${alum.nombre}</div>
                                    <div>🆔 CI: ${alum.carnet}</div>
                                    <div>📞 Cel: ${alum.celular}</div>
                                    <div style="margin-top:8px"><span class="tag">${alum.curso}</span></div>
                                 </div>`;
                    });
                    divRes.innerHTML = html;
                })
                .catch(err => divRes.innerHTML = "<p style='text-align:center'>Error de conexión</p>");
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
    # Búsqueda optimizada
    sql = """
        SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso
        FROM inscripciones i
        JOIN alumnos a ON i.alumno_id = a.id
        JOIN cursos c ON i.curso_id = c.id
        WHERE a.nombre_completo ILIKE %s 
           OR a.carnet ILIKE %s 
           OR a.celular ILIKE %s
        LIMIT 20
    """
    param = f"%{query}%"
    cur.execute(sql, (param, param, param))
    datos = cur.fetchall()
    conn.close()
    
    lista = []
    for r in datos:
        lista.append({"nombre": r[0], "carnet": r[1] or "S/D", "celular": r[2] or "S/D", "curso": r[3]})
    return jsonify(lista)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)