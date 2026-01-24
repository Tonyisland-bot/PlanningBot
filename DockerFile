# Image officielle Python 3.11 (audioop toujours présent)
FROM python:3.11.9-slim

# Empêche Python de bufferiser les logs
ENV PYTHONUNBUFFERED=1

# Dossier de travail dans le container
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copie du reste du code
COPY . .

# Commande de démarrage
CMD ["python", "bot.py"]
