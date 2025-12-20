import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask
import threading
import time
import requests

# === CONFIG DISCORD ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# === DONNÉES EN MÉMOIRE ===
plannings = defaultdict(lambda: defaultdict(list))

# === KEEP ALIVE (serveur Flask pour Render) ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running and alive!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive_ping():
    """Ping régulier du service Render pour éviter l’arrêt du bot."""
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        print("⚠️ Pas d'URL externe Render trouvée — ping désactivé.")
        return
    while True:
        try:
            requests.get(url)
            print(f"🌐 Ping envoyé à {url}")
        except Exception as e:
            print("⚠️ Erreur lors du ping :", e)
        time.sleep(600)  # ping toutes les 10 minutes

# === BASE DE DONNÉES ===
def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def init_database():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS plannings (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                date VARCHAR(10) NOT NULL,
                texte TEXT NOT NULL
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def load_plannings():
    plannings.clear()
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT guild_id, date, texte FROM plannings')
        for row in cur.fetchall():
            plannings[row['guild_id']][row['date']].append(row['texte'])
    finally:
        conn.close()

def save_event(guild_id, date, texte):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO plannings (guild_id, date, texte) VALUES (%s, %s, %s)',
            (guild_id, date, texte)
        )
        conn.commit()
    finally:
        conn.close()

def delete_events(guild_id, date=None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if date is None:
            cur.execute('DELETE FROM plannings WHERE guild_id = %s', (guild_id,))
        else:
            cur.execute(
                'DELETE FROM plannings WHERE guild_id = %s AND date = %s',
                (guild_id, date)
            )
        conn.commit()
    finally:
        conn.close()

def get_week_days():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    mois_fr = [
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
    ]
    week_days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        week_days.append({
            'jour': jours_fr[i],
            'date': day.day,
            'mois': mois_fr[day.month - 1],
            'full_date': day.strftime('%Y-%m-%d')
        })
    return week_days

# === ÉVÉNEMENTS DISCORD ===
@bot.event
async def on_ready():
    print(f"✅ Bot connecté comme {bot.user}")
    try:
        init_database()
        print("✅ Base de données initialisée")
    except Exception as e:
        print("⚠️ Erreur init_database :", e)
    load_plannings()
    total = sum(len(days) for guild in plannings.values() for days in guild.values())
    print(f"{bot.user} est prêt avec {total} événements chargés depuis la base !")

# === COMMANDES DISCORD ===
@bot.command()
@commands.has_permissions(manage_messages=True)
async def bonjour(ctx):
    await ctx.send(f'Bonjour {ctx.author.mention} 👋 Je suis le bot de planning du Sonic UHC !')

@bot.command(aliases=['p', 'P', 'Planning'])
async def planning(ctx):
    week_days = get_week_days()
    guild_id = ctx.guild.id
    premier_jour = week_days[0]
    dernier_jour = week_days[6]

    embed = discord.Embed(
        title="📅 Planning du Sonic UHC",
        description=f"Du {premier_jour['date']} {premier_jour['mois']} au {dernier_jour['date']} {dernier_jour['mois']}",
        color=discord.Color.blue()
    )

    for day_info in week_days:
        jour, date, mois, full_date = (
            day_info['jour'],
            day_info['date'],
            day_info['mois'],
            day_info['full_date'],
        )


        events = plannings[guild_id].get(full_date, [])
        events_text = '\n\n'.join(f"• {event}" for event in events) if events else "*Aucune partie prévue.*"
        embed.add_field(name=f"━━━━━━━━━━━━━━━\n**{jour} {date} {mois}**", value=f"{events_text}\n​", inline=False)
        
    embed.add_field(
    name="ℹ️ Information",
    value="Si vous souhaitez avoir des games les jours où aucune game n'est prévue, "
          "vous pouvez toujours en acheter en faisant un ticket pour acheter un host (3€)",
    inline=False
    )
    await ctx.send(embed=embed)
        
@bot.command(aliases=['ap', 'aplanning'])
@commands.has_permissions(manage_messages=True)
async def ajouter_planning(ctx, jour: str, *, texte: str):
    jours_map = {
        'lundi': 0, 'mardi': 1, 'mercredi': 2, 'jeudi': 3,
        'vendredi': 4, 'samedi': 5, 'dimanche': 6
    }
    jour_lower = jour.lower()
    if jour_lower not in jours_map:
        await ctx.send("❌ Jour invalide ! (lundi à dimanche)")
        return

    week_days = get_week_days()
    day_info = week_days[jours_map[jour_lower]]
    full_date = day_info['full_date']

    guild_id = ctx.guild.id
    plannings[guild_id][full_date].append(texte)
    save_event(guild_id, full_date, texte)

    await ctx.send(f"✅ Événement ajouté pour {day_info['jour']} {day_info['date']} {day_info['mois']} !")

@bot.command(aliases=['ep', 'eplanning'])
@commands.has_permissions(manage_messages=True)
async def effacer_planning(ctx, jour: str | None = None):
    guild_id = ctx.guild.id
    if jour is None:
        plannings[guild_id].clear()
        delete_events(guild_id)
        await ctx.send("✅ Tout le planning a été effacé !")
        return

    jours_map = {
        'lundi': 0, 'mardi': 1, 'mercredi': 2, 'jeudi': 3,
        'vendredi': 4, 'samedi': 5, 'dimanche': 6
    }
    jour_lower = jour.lower()
    if jour_lower not in jours_map:
        await ctx.send("❌ Jour invalide ! (lundi à dimanche)")
        return

    week_days = get_week_days()
    day_info = week_days[jours_map[jour_lower]]
    full_date = day_info['full_date']

    if full_date in plannings[guild_id]:
        del plannings[guild_id][full_date]
        delete_events(guild_id, full_date)
        await ctx.send(f"✅ Planning du {day_info['jour']} effacé !")
    else:
        await ctx.send(f"ℹ️ Aucun événement prévu pour {day_info['jour']}")

@bonjour.error
@ajouter_planning.error
@effacer_planning.error
async def permission_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Vous devez être modérateur pour utiliser cette commande !")

# === LANCEMENT DU SERVEUR WEB ET DU BOT ===
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    bot.run(os.environ["TOKEN_BOT_DISCORD"])
