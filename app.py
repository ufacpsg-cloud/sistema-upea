from flask import Flask, jsonify, request, render_template_string, make_response
import psycopg2
import os

app = Flask(__name__)

ADMIN_PIN = "1375" # Tu clave

DATABASE_URL = "postgresql://neondb_owner:npg_ucDUbfEr29Bn@ep-small-base-ahys4mod-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# --- DISEÑO CON LÓGICA DE 2 CAMINOS ---
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
        .search-box { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 15px; border: 2px solid #ddd; border-radius: 10px; font-size: 16px; outline: none; }
        .btn-primary { background: #1a73e8; color: white; padding: 12px 20px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
        
        .result-item { border-left: 6px solid #1a73e8; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
        .tag { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; margin-top: 5px; }
        .tag-secretaria { background: #eee; color: #666; }
        .tag-enviado { background: #d4edda; color: #155724; }
        .tag-recogido { background: #cfe2ff; color: #084298; }
        
        .btn-group { display: flex; flex-direction: column; gap: 5px; }
        .btn-status { padding: 8px 15px; border-radius: 6px; font-size: 11px; text-transform: uppercase; border: none; cursor: pointer; color: white; width: 150px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🎓 Control de Certificados UPEA</h1>
            <div class="search-box">
                <input type="text" id="busqueda" placeholder="Nombre, CI o Celular..." onkeypress="if(event.key==='Enter') buscar()">
                <button class="btn-primary" onclick="buscar()">🔍 BUSCAR</button>
            </div>
        </div>
        <div id="resultados"></div>
    </div>

    <script>
        let filtroActual = "";

        function buscar() {
            let texto = document.getElementById('busqueda').value;
            filtroActual = texto;
            let divRes = document.getElementById('resultados');
            fetch('/buscar?q=' + encodeURIComponent(texto))
                .then(res => res.json())
                .then(data => {
                    let html = "";
                    data.forEach(alum => {
                        let st = alum.estado;
                        let tagClass = "tag-" + st;
                        
                        // LÓGICA DE BOTONES SEGÚN TU SOLICITUD
                        let btnRecogidoHTML = "";
                        let btnEnviadoHTML = "";

                        if (st === 'recogido') {
                            // Si ya está recogido, el botón de Recogido cambia a "No Recogido" (Rojo)
                            btnRecogidoHTML = `<button class="btn-status" style="background:#dc3545" onclick="cambiarEstado('${alum.carnet}', 'secretaria', false)">❌ No Recogido</button>`;
                            btnEnviadoHTML = `<button class="btn-status" style="background:#6c757d" disabled>Enviado 🔐</button>`;
                        } else if (st === 'enviado') {
                            // Si ya está enviado, el botón de enviado permite revertir con PIN
                            btnRecogidoHTML = `<button class="btn-status" style="background:#0d6efd" onclick="cambiarEstado('${alum.carnet}', 'recogido', false)">Recogido</button>`;
                            btnEnviadoHTML = `<button class="btn-status" style="background:#f39c12" onclick="cambiarEstado('${alum.carnet}', 'secretaria', true)">Regresar a Sec 🔐</button>`;
                        } else {
                            // Estado SECRETARIA (Por defecto)
                            btnRecogidoHTML = `<button class="btn-status" style="background:#0d6efd" onclick="cambiarEstado('${alum.carnet}', 'recogido', false)">Recogido</button>`;
                            btnEnviadoHTML = `<button class="btn-status" style="background:#28a745" onclick="cambiarEstado('${alum.carnet}', 'enviado', true)">Enviado 🔐</button>`;
                        }

                        html += `
                            <div class="card result-item">
                                <div>
                                    <div style="font-weight:bold;">👤 ${alum.nombre}</div>
                                    <div style="font-size:12px; color:#666;">🆔 CI: ${alum.carnet} | 📞 ${alum.celular}</div>
                                    <div style="margin-top:5px;">
                                        <span class="tag" style="background:#e8f0fe; color:#1a73e8;">${alum.curso}</span>
                                        <span class="tag ${tagClass}">📍 ${st.toUpperCase()}</span>
                                    </div>
                                </div>
                                <div class="btn-group">
                                    ${btnRecogidoHTML}
                                    ${btnEnviadoHTML}
                                </div>
                            </div>`;
                    });
                    divRes.innerHTML = html || "<p style='text-align:center'>No se encontraron resultados.</p>";
                });
        }

        function cambiarEstado(carnet, nuevoEstado, requierePin) {
            let pin = "";
            if(requierePin) {
                pin = prompt("🔐 Se requiere PIN administrativo:");
                if(!pin) return;
            }
            fetch('/actualizar_estado', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({carnet: carnet, estado: nuevoEstado, pin: pin})
            }).then(res => res.json()).then(data => {
                if(data.status === 'success') buscar();
                else alert("❌ " + (data.message || "Error"));
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML_APP)

@app.route('/buscar')
def buscar_alumno():
    query = request.args.get('q', '').strip()
    conn = get_db_connection(); cur = conn.cursor()
    sql = "SELECT a.nombre_completo, a.carnet, a.celular, c.nombre_curso, COALESCE(i.estado_certificacion, 'secretaria') FROM inscripciones i JOIN alumnos a ON i.alumno_id = a.id JOIN cursos c ON i.curso_id = c.id WHERE a.nombre_completo ILIKE %s OR a.carnet ILIKE %s OR a.celular ILIKE %s OR c.nombre_curso ILIKE %s ORDER BY a.nombre_completo ASC LIMIT 50"
    p = f"%{query}%"; cur.execute(sql, (p, p, p, p))
    datos = cur.fetchall(); conn.close()
    return jsonify([{"nombre": r[0], "carnet": r[1], "celular": r[2], "curso": r[3], "estado": r[4]} for r in datos])

@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    data = request.json
    nuevo_estado = data.get('estado')
    # Solo pide PIN si vamos a 'enviado' o si vamos a 'secretaria' DESDE enviado
    if data.get('pin') != ADMIN_PIN and data.get('pin') != "" :
         pass # Lógica de PIN manejada abajo
    
    if nuevo_estado == 'enviado' or (nuevo_estado == 'secretaria' and data.get('pin') != ""):
        if data.get('pin') != ADMIN_PIN:
            return jsonify({"status": "error", "message": "PIN incorrecto"}), 403

    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("UPDATE inscripciones SET estado_certificacion = %s WHERE alumno_id = (SELECT id FROM alumnos WHERE carnet = %s)", (nuevo_estado, data.get('carnet')))
    conn.commit(); conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
