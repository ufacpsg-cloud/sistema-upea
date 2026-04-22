from flask import Flask, jsonify, request, render_template_string, make_response
import psycopg2
import os

app = Flask(__name__)

ADMIN_PIN = "1375" # Tu PIN de seguridad

DATABASE_URL = "postgresql://neondb_owner:npg_ucDUbfEr29Bn@ep-small-base-ahys4mod-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# --- DISEÑO CON BOTÓN DE REVERSIÓN ---
HTML_APP = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel Gestión UPEA</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f4f8; padding: 20px; margin: 0; }
        .container { max-width: 900px; margin: auto; }
        .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
        h1 { color: #1a73e8; text-align: center; }
        .search-box { display: flex; gap: 10px; margin-bottom: 10px; }
        input { flex: 1; padding: 15px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 16px; outline: none; }
        .btn { padding: 12px 20px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; color: white; }
        .btn-primary { background: #1a73e8; }
        .btn-secondary { background: #5f6368; width: 100%; margin-top: 10px; }
        #seccion-cursos { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; max-height: 300px; overflow-y: auto; padding: 10px; }
        .course-chip { background: #fff; border: 2px solid #fbbc04; color: #3c4043; padding: 12px; border-radius: 10px; cursor: pointer; text-align: center; font-size: 13px; font-weight: bold; }
        .result-item { border-left: 6px solid #1a73e8; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
        .tag { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; margin-top: 5px; }
        .tag-secretaria { background: #fff3cd; color: #856404; }
        .tag-enviado { background: #d4edda; color: #155724; }
        .tag-recogido { background: #cfe2ff; color: #084298; }
        .btn-status { padding: 8px 15px; border-radius: 6px; font-size: 11px; text-transform: uppercase; border: none; cursor: pointer; color: white; width: 160px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🎓 Gestión UPEA</h1>
            <div class="search-box">
                <input type="text" id="busqueda" placeholder="Nombre, CI o Celular...">
                <button class="btn btn-primary" onclick="buscar()">🔍</button>
            </div>
            <button id="btn-lista-maestra" class="btn btn-secondary" onclick="toggleCursos()">📚 MOSTRAR LISTA DE CURSOS</button>
            <div id="wrapper-cursos" style="display:none; margin-top:15px;">
                <div id="seccion-cursos"></div>
            </div>
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
                let listaDiv = document.getElementById('seccion-cursos');
                listaDiv.innerHTML = "";
                data.forEach(c => {
                    let chip = document.createElement('div');
                    chip.className = 'course-chip'; chip.innerText = c;
                    chip.onclick = () => { buscar(c, true); document.getElementById('wrapper-cursos').style.display = "none"; };
                    listaDiv.appendChild(chip);
                });
            });
        }

        function buscar(textoBusqueda = false, esExacto = false) {
            let texto = textoBusqueda ? textoBusqueda : document.getElementById('busqueda').value;
            filtroActual = texto;
            let divRes = document.getElementById('resultados');
            let url = `/buscar?q=${encodeURIComponent(texto)}${esExacto ? '&exacto=true' : ''}`;

            fetch(url).then(res => res.json()).then(data => {
                let html = "";
                data.forEach(alum => {
                    let st = alum.estado;
                    let proximo, btnColor, btnTxt, tagClass, requierePin;
                    
                    if(st === 'secretaria') {
                        proximo = 'enviado'; btnColor = '#28a745'; btnTxt = 'Marcar Enviado 🔐'; tagClass = 'tag-secretaria'; requierePin = true;
                    } else if(st === 'enviado') {
                        // AQUÍ AÑADIMOS EL BOTÓN DOBLE: Uno para avanzar y otro para retroceder
                        html += `
                            <div class="card result-item">
                                <div>
                                    <div style="font-weight:bold;">👤 ${alum.nombre}</div>
                                    <div style="font-size:12px; color:#666;">🆔 CI: ${alum.carnet} | 📞 ${alum.celular}</div>
                                    <div style="margin-top:5px;">
                                        <span class="tag" style="background:#e8f0fe; color:#1a73e8;">${alum.curso}</span>
                                        <span class="tag tag-enviado">📍 ENVIADO</span>
                                    </div>
                                </div>
                                <div style="display:flex; flex-direction:column; gap:5px;">
                                    <button class="btn-status" style="background:#0d6efd" onclick="cambiarEstado('${alum.carnet}', 'recogido', false)">Entregado (Libre)</button>
                                    <button class="btn-status" style="background:#dc3545" onclick="cambiarEstado('${alum.carnet}', 'secretaria', true)">Regresar a Sec 🔐</button>
                                </div>
                            </div>`;
                        return; // Saltamos el resto para esta tarjeta
                    } else {
                        proximo = 'secretaria'; btnColor = '#6c757d'; btnTxt = 'Reiniciar a Sec 🔐'; tagClass = 'tag-recogido'; requierePin = true;
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
                            <button class="btn-status" style="background:${btnColor}" 
                                    onclick="cambiarEstado('${alum.carnet}', '${proximo}', ${requierePin})">
                                ${btnTxt}
                            </button>
                        </div>`;
                });
                divRes.innerHTML = html || "<p style='text-align:center'>Sin resultados</p>";
            });
        }

        function cambiarEstado(carnet, nuevoEstado, requierePin) {
            let pin = "";
            if(requierePin) {
                pin = prompt("🔐 Ingrese PIN para cambiar a un estado administrativo:");
                if(!pin) return;
            }
            fetch('/actualizar_estado', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({carnet: carnet, estado: nuevoEstado, pin: pin})
            }).then(res => res.json()).then(data => {
                if(data.status === 'success') buscar(filtroActual);
                else alert("❌ " + (data.message || "Error de PIN"));
            });
        }
    </script>
</body>
</html>
"""

# ... (El resto de las rutas @app.route de Python se mantienen iguales a la versión anterior)
