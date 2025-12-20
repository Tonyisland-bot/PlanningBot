import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask
import threading
import socket
import sys

lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    lock.bind(("127.0.0.1", 9999))
except OSError:
    print("⛔ Bot déjà lancé, arrêt.")
    sys.exit(0)
# ================== CONFIG DISCORD ==================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ================== DONNÉES EN MÉMOIRE ==================
plannings = defaultdict(lambda: defaultdict(list))

# ================== SERVEUR WEB (Render) ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot Discord en ligne"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================== BASE DE DONNÉES ==================
def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def init_database():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS plannings (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    date VARCHAR(10) NOT NULL,
                    texte TEXT NOT NULL
                )
            """)
            conn.commit()
    finally:
        conn.close()

def load_plannings():
    plannings.clear()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT guild_id, date, texte FROM plannings")
            for row in cur.fetchall():
                plannings[row["guild_id"]][row["date"]].append(row["texte"])
    finally:
        conn.close()

def save_event(guild_id, date, texte):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO plannings (guild_id, date, texte) VALUES (%s, %s, %s)",
                (guild_id, date, texte)
            )
            conn.commit()
    finally:
        conn.close()

def delete_events(guild_id, date=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if date is None:
                cur.execute("DELETE FROM plannings WHERE guild_id = %s", (guild_id,))
            else:
                cur.execute(
                    "DELETE FROM plannings WHERE guild_id = %s AND date = %s",
                    (guild_id, date)
                )
            conn.commit()
    finally:
        conn.close()

# ================== OUTILS ==================
def get_week_days():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois_fr = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]

    week_days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        week_days.append({
            "jour": jours_fr[i],
            "date": day.day,
            "mois": mois_fr[day.month - 1],
            "full_date": day.strftime("%Y-%m-%d")
        })
    return week_days

# ================== EVENTS ==================
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    init_database()
    load_plannings()
    total = sum(len(v) for g in plannings.values() for v in g.values())
    print(f"📅 {total} événements chargés depuis la base")

# ================== COMMANDES ==================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def bonjour(ctx):
    await ctx.send(f"👋 Bonjour {ctx.author.mention} !")

@bot.command(aliases=["p", "P", "Planning"])
async def planning(ctx):
    week_days = get_week_days()
    guild_id = ctx.guild.id
    premier_jour = week_days[0]
    dernier_jour = week_days[-1]

    embed = discord.Embed(
        title="📅 Planning du Sonic UHC",
        description=f"Du {premier_jour['date']} {premier_jour['mois']} au {dernier_jour['date']} {dernier_jour['mois']}",
        color=discord.Color.blue()
    )

    for day in week_days:
        events = plannings[guild_id].get(day["full_date"], [])
        text = "\n\n".join(f"• {e}" for e in events) if events else "*Aucune partie prévue.*"

        embed.add_field(
            name=f"━━━━━━━━━━━━━━━\n**{day['jour']} {day['date']} {day['mois']}**",
            value=f"{text}\n\u200b",
            inline=False
        )

    embed.add_field(
        name="ℹ️ Information",
        value="Si vous souhaitez avoir des games les jours où aucune game n'est prévue, "
              "vous pouvez toujours en acheter en faisant un ticket pour acheter un host (3€)",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command(aliases=["ap", "aplanning"])
@commands.has_permissions(manage_messages=True)
async def ajouter_planning(ctx, jour: str, *, texte: str):
    jours = {
        "lundi": 0, "mardi": 1, "mercredi": 2,
        "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6
    }

    jour = jour.lower()
    if jour not in jours:
        await ctx.send("❌ Jour invalide (lundi à dimanche)")
        return

    week_days = get_week_days()
    day = week_days[jours[jour]]
    guild_id = ctx.guild.id

    plannings[guild_id][day["full_date"]].append(texte)
    save_event(guild_id, day["full_date"], texte)

    await ctx.send(f"✅ Événement ajouté pour {day['jour']} {day['date']} {day['mois']}")

@bot.command(aliases=["ep", "eplanning"])
@commands.has_permissions(manage_messages=True)
async def effacer_planning(ctx, jour: str | None = None):
    guild_id = ctx.guild.id

    if jour is None:
        plannings[guild_id].clear()
        delete_events(guild_id)
        await ctx.send("✅ Planning entièrement effacé")
        return

    jours = {
        "lundi": 0, "mardi": 1, "mercredi": 2,
        "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6
    }

    jour = jour.lower()
    if jour not in jours:
        await ctx.send("❌ Jour invalide")
        return

    week_days = get_week_days()
    day = week_days[jours[jour]]

    if day["full_date"] in plannings[guild_id]:
        del plannings[guild_id][day["full_date"]]
        delete_events(guild_id, day["full_date"])
        await ctx.send(f"✅ Planning du {day['jour']} effacé")
    else:
        await ctx.send("ℹ️ Aucun événement ce jour-là")

# ================== LANCEMENT ==================
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.environ["TOKEN_BOT_DISCORD"])
