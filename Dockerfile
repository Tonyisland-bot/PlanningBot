# Utiliser Python 3.11
FROM python:3.11-slim

# Créer un dossier pour l'app
WORKDIR /app

# Copier les fichiers du dépôt dans le conteneur
COPY . .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Lancer ton bot
CMD ["python", "bot.py"]
