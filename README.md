# 📊 Generador de Tablas de Frecuencia — App Web

## Instalación (una sola vez)

```bash
pip install flask pandas openpyxl
```

## Cómo ejecutar

```bash
python app.py
```

El navegador se abre solo en **http://localhost:5050**

## Uso

1. Arrastrá o seleccioná tu archivo CSV (separador `;`, decimales `,`)
2. Elegí la columna a analizar
3. Seleccioná el modo:
   - **Sturges Automático** → k se calcula solo
   - **Distribución Arbitraria** → vos elegís k
4. Hacé clic en **Calcular tabla**
5. Exportá a Excel con el botón **Exportar Excel**
