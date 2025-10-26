# --- 1. Imagen Base ---
# Usamos Python 3.11 (asumo que "Python 11" es 3.11)
# "slim" es una versión más ligera
FROM python:3.11-slim

# --- 2. Variables de Entorno ---
# Evita que Python guarde archivos .pyc
ENV PYTHONDONTWRITEBYTECODE 1
# Evita que Python guarde logs en buffer, se ven al instante
ENV PYTHONUNBUFFERED 1

# --- 3. Directorio de Trabajo ---
# Establece el directorio dentro del contenedor
WORKDIR /app

# --- 4. Instalar Dependencias ---
# Copia solo el archivo de requisitos primero
# Esto aprovecha el caché de Docker: si no cambias requirements.txt,
# no se volverán a instalar todas las librerías.
COPY requirements.txt .

# Instala las librerías
# --no-cache-dir ahorra espacio en la imagen final
RUN pip install --no-cache-dir -r requirements.txt

# --- 5. Copiar tu Aplicación ---
# Copia el resto de tus archivos (app.py, modelos .h5, etc.)
# ¡IMPORTANTE! Esto copiará tus carpetas 'templates' y 'static'
COPY . .

# --- 6. Exponer Puerto ---
# Expone el puerto en el que Gunicorn correrá
EXPOSE 8000

# --- 7. Comando de Inicio ---
# El comando para iniciar tu app con Gunicorn
# "app:app" significa: en el archivo "app.py", usa la variable "app"
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]

