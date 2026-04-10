from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
import math
import io

app = Flask(__name__)


# ─────────────────────────────
# DETERMINAR PRECISIÓN DECIMAL
# ─────────────────────────────
def determinar_precision(datos):
    if (datos % 1 == 0).all():
        return 1, 0

    str_datos = datos.astype(str).str.split('.')
    nd = int(str_datos.apply(lambda x: len(x[1]) if len(x) > 1 else 0).max())
    c = 10.0 ** (-nd)

    return round(c, nd), nd


def fmt(valor, nd):
    if nd == 0:
        return str(int(round(valor, 0)))
    return f"{valor:.{nd}f}"


# ─────────────────────────────
# MÉTODOS PARA CALCULAR k
# ─────────────────────────────
def calcular_k_sturges(n):
    """
    Fórmula de Sturges: k = 1 + 3.322 * log10(n)
    Sugerida para distribuciones aproximadamente normales.
    """
    exacto = 1 + 3.322 * math.log10(n)
    return round(exacto), round(exacto, 3)


def calcular_k_rango(datos, c):
    """
    Método basado en el rango (Máximo − Mínimo):
    Propone un número de clases proporcional a la raíz cuadrada de n,
    pero ajustado para que el tamaño de clase sea un múltiplo de c
    y cubra todo el rango.

    Variante práctica:
        k = ceil( (D − d) / t_sugerido )
    donde  t_sugerido = ceil( (D − d) / sqrt(n) / c ) * c
    """
    n  = len(datos)
    d  = float(datos.min())
    D  = float(datos.max())
    rango = D - d

    # paso sugerido = rango / sqrt(n), redondeado al múltiplo de c superior
    t_sugerido_exacto = rango / math.sqrt(n)
    t_sugerido = math.ceil(t_sugerido_exacto / c) * c

    k = math.ceil(rango / t_sugerido)

    # garantizar al menos 2 clases
    k = max(k, 2)

    return k, round(t_sugerido_exacto, 6), round(t_sugerido, 10)


# ─────────────────────────────
# CALCULAR TABLA
# ─────────────────────────────
def calcular_tabla(datos, k, metodo="sturges", k_sturges_info=None, rango_info=None):

    n = len(datos)
    d = float(datos.min())
    D = float(datos.max())

    c, nd = determinar_precision(datos)

    la = round(D - d + c, nd)

    # Referencia Sturges siempre se calcula (para mostrar en pasos)
    k_sturges_exacto = 1 + 3.322 * math.log10(n)
    k_sturges = round(k_sturges_exacto)

    # tamaño de clase
    t_exacto = la / k
    t = round(math.ceil(t_exacto / c) * c, nd)

    if nd == 0:
        t = int(t)

    # nuevo alcance
    la_nuevo = round(k * t, nd)
    exceso = round(la_nuevo - la, nd)

    ajuste_inf = 0
    ajuste_sup = 0

    if exceso > 1e-9:
        ajuste_inf = round(math.floor((exceso / 2) / c) * c, nd)
        ajuste_sup = round(exceso - ajuste_inf, nd)

    d_nuevo = round(d - ajuste_inf, nd)

    # intervalos
    bins = [round(d_nuevo + i * t, nd) for i in range(k + 1)]

    frecuencias = pd.cut(datos, bins=bins, right=False)

    fi_vals = frecuencias.value_counts().sort_index().values.tolist()

    hi_vals = [round(fi / n, 4) for fi in fi_vals]
    pi_vals = [round(hi * 100, 4) for hi in hi_vals]

    Fi_vals = list(np.cumsum(fi_vals))
    Hi_vals = [round(v, 4) for v in np.cumsum(hi_vals)]
    Pi_vals = [round(v, 4) for v in np.cumsum(pi_vals)]

    intervalos = [
        f"[{fmt(bins[i],nd)} ; {fmt(bins[i+1],nd)})"
        for i in range(len(bins) - 1)
    ]

    # ─────────────────────────────
    # PASOS EXPLICADOS  (varían según método)
    # ─────────────────────────────

    if metodo == "sturges":
        paso_k = {
            "num": 4,
            "titulo": "Número de intervalos (Sturges)",
            "formula": "k = 1 + 3.322 · log₁₀(n)",
            "desarrollo": f"1 + 3.322 · log₁₀({n}) = {k_sturges_exacto:.3f}",
            "valor": f"{k}  (redondeado)"
        }

    elif metodo == "arbitrario":
        paso_k = {
            "num": 4,
            "titulo": "Número de intervalos (Arbitrario)",
            "formula": "k definido por el usuario",
            "desarrollo": f"El usuario eligió k = {k}",
            "valor": f"{k}"
        }

    else:  # rango / máximo-mínimo
        t_sug_exacto = rango_info["t_sugerido_exacto"] if rango_info else "—"
        t_sug        = rango_info["t_sugerido"]        if rango_info else "—"
        paso_k = {
            "num": 4,
            "titulo": "Número de intervalos (Máximo − Mínimo)",
            "formula": "t* = (D−d) / √n  →  k = ⌈(D−d) / t*⌉",
            "desarrollo": (
                f"t* exacto = ({fmt(D,nd)} − {fmt(d,nd)}) / √{n} = {t_sug_exacto:.4f}  →  "
                f"t* redondeado = {fmt(t_sug, nd)}  →  "
                f"k = ⌈{fmt(D-d, nd)} / {fmt(t_sug, nd)}⌉ = {k}"
            ),
            "valor": f"{k}"
        }

    pasos = [
        {
            "num": 1,
            "titulo": "Número de datos",
            "formula": "n",
            "desarrollo": "",
            "valor": f"{n}"
        },
        {
            "num": 2,
            "titulo": "Alcance original",
            "formula": "a = [d ; D]",
            "desarrollo": f"[{fmt(d,nd)} ; {fmt(D,nd)}]",
            "valor": f"[{fmt(d,nd)} ; {fmt(D,nd)}]"
        },
        {
            "num": 3,
            "titulo": "Longitud del alcance",
            "formula": "la = D − d + c",
            "desarrollo": f"{fmt(D,nd)} − {fmt(d,nd)} + {fmt(c,nd)}",
            "valor": f"{fmt(la,nd)}"
        },
        paso_k,
        {
            "num": 5,
            "titulo": "Tamaño de clase",
            "formula": "t = la / k  (redondeado al múltiplo de c superior)",
            "desarrollo": f"{fmt(la,nd)} / {k} = {t_exacto:.4f}  →  t = {fmt(t,nd)}",
            "valor": f"{fmt(t,nd)}"
        },
        {
            "num": 6,
            "titulo": "Ajuste del rango",
            "formula": "Nuevo rango",
            "desarrollo": f"Exceso = {fmt(exceso,nd)}",
            "valor": f"[{fmt(d_nuevo,nd)} ; {fmt(round(d_nuevo+k*t,nd),nd)}]"
        }
    ]

    return {
        "n": n,
        "d": d,
        "D": D,
        "c": float(c),
        "nd": nd,
        "la": la,

        "k": k,
        "k_sturges": k_sturges,
        "k_sturges_exacto": round(k_sturges_exacto, 3),

        "t": float(t),
        "exceso": float(exceso),

        "d_nuevo": d_nuevo,

        "intervalos": intervalos,

        "fi": fi_vals,
        "hi": hi_vals,
        "pi": pi_vals,

        "Fi": [int(v) for v in Fi_vals],
        "Hi": Hi_vals,
        "Pi": Pi_vals,

        "pasos": pasos,
        "metodo": metodo
    }


# ─────────────────────────────
# RUTAS
# ─────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/calcular", methods=["POST"])
def calcular():

    try:

        archivo = request.files["csv"]

        # ── leer modo y parámetros ──────────────────────────────────────────
        # modo: "auto" (Sturges) | "arbitrario" | "rango"
        modo      = request.form.get("modo", "auto")
        k_manual  = request.form.get("k_manual")

        contenido = archivo.read().decode("utf-8-sig")

        from io import StringIO
        df = pd.read_csv(StringIO(contenido), sep=";", decimal=",")
        df.columns = df.columns.str.strip()

        columna = request.form.get("columna", "").strip()

        if columna not in df.columns:
            return jsonify({
                "error": f"Columna '{columna}' no encontrada. Disponibles: {list(df.columns)}"
            }), 400

        datos = df[columna].dropna()
        n     = len(datos)

        c, nd = determinar_precision(datos)

        rango_info = None

        if modo == "auto":
            # ── Sturges ────────────────────────────────────────────────────
            k, _ = calcular_k_sturges(n)
            metodo = "sturges"

        elif modo == "arbitrario":
            # ── Arbitrario ─────────────────────────────────────────────────
            if not k_manual:
                return jsonify({"error": "Debes ingresar k para el modo arbitrario."}), 400
            k = int(k_manual)
            if k < 2:
                return jsonify({"error": "k debe ser al menos 2."}), 400
            metodo = "arbitrario"

        elif modo == "rango":
            # ── Máximo − Mínimo ────────────────────────────────────────────
            k, t_sug_exacto, t_sug = calcular_k_rango(datos, c)
            rango_info = {
                "t_sugerido_exacto": t_sug_exacto,
                "t_sugerido":        t_sug
            }
            metodo = "rango"

        else:
            return jsonify({"error": f"Modo desconocido: {modo}"}), 400

        resultado = calcular_tabla(datos, k, metodo=metodo, rango_info=rango_info)
        resultado["modo"] = modo

        return jsonify(resultado)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/columnas", methods=["POST"])
def columnas():

    try:

        archivo = request.files["csv"]

        contenido = archivo.read().decode("utf-8-sig")

        from io import StringIO
        df = pd.read_csv(StringIO(contenido), sep=";", decimal=",")
        df.columns = df.columns.str.strip()

        numericas = df.select_dtypes(include=[np.number]).columns.tolist()

        return jsonify({
            "columnas": numericas if numericas else df.columns.tolist()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/exportar", methods=["POST"])
def exportar():

    try:

        data = request.json

        intervalos = data["intervalos"]
        fi = data["fi"]
        hi = data["hi"]
        pi = data["pi"]
        Fi = data["Fi"]
        Hi = data["Hi"]
        Pi = data["Pi"]

        df_exp = pd.DataFrame({
            "Intervalo": intervalos,
            "fi":        fi,
            "hi":        [f"{v:.2f}" for v in hi],
            "pi (%)":    [f"{v:.2f}%" for v in pi],
            "Fi":        Fi,
            "Hi":        [f"{v:.2f}" for v in Hi],
            "Pi (%)":    [f"{v:.2f}%" for v in Pi]
        })

        total = pd.DataFrame({
            "Intervalo": ["TOTAL"],
            "fi":        [sum(fi)],
            "hi":        [f"{sum(hi):.2f}"],
            "pi (%)":    ["100,00%"],
            "Fi":        [""],
            "Hi":        [""],
            "Pi (%)":    [""]
        })

        df_exp = pd.concat([df_exp, total], ignore_index=True)

        buf = io.BytesIO()

        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_exp.to_excel(writer, index=False, sheet_name="Frecuencias")

        buf.seek(0)

        return send_file(
            buf,
            as_attachment=True,
            download_name="tabla_frecuencias.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────
# INICIAR SERVIDOR
# ─────────────────────────────

if __name__ == "__main__":

    import webbrowser
    import threading

    threading.Timer(
        1.0,
        lambda: webbrowser.open("http://localhost:5050")
    ).start()

    app.run(debug=False, port=5050)