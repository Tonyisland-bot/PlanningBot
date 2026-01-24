import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
print("PYTHON VERSION:", sys.version)

# ================== DISCORD ==================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# ================== DONNÉES ==================
plannings = defaultdict(lambda: defaultdict(list))

# ================== BASE DE DONNÉES ==================
def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def init_database():
    with get_db_connection() as conn:
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

def load_plannings():
    plannings.clear()
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT guild_id, date, texte FROM plannings")
            for row in cur.fetchall():
                plannings[row["guild_id"]][row["date"]].append(row["texte"])

def save_event(guild_id, date, texte):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO plannings (guild_id, date, texte) VALUES (%s, %s, %s)",
                (guild_id, date, texte)
            )
            conn.commit()

def delete_events(guild_id, date=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if date:
                cur.execute(
                    "DELETE FROM plannings WHERE guild_id=%s AND date=%s",
                    (guild_id, date)
                )
            else:
                cur.execute(
                    "DELETE FROM plannings WHERE guild_id=%s",
                    (guild_id,)
                )
            conn.commit()

# ================== OUTILS ==================
def get_week_days():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())

    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]

    week = []
    for i in range(7):
        day = monday + timedelta(days=i)
        week.append({
            "jour": jours[i],
            "date": day.day,
            "mois": mois[day.month - 1],
            "full_date": day.strftime("%Y-%m-%d")
        })
    return week

# ================== EVENTS ==================
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    init_database()
    load_plannings()
    total = sum(len(v) for g in plannings.values() for v in g.values())
    print(f"📅 {total} événements chargés")

# ================== COMMANDES ==================

@bot.command(aliases=["p", "P", "Planning"])
async def planning(ctx):
    week_days = get_week_days()
    guild_id = ctx.guild.id

    premier = week_days[0]
    dernier = week_days[-1]

    embed = discord.Embed(
        title=f"📅 Planning du {premier['date']} {premier['mois']} au {dernier['date']} {dernier['mois']}",
        color=discord.Color.blue()
    )

    for day in week_days:
        events = plannings[guild_id].get(day["full_date"], [])
        text = "\n".join(f"• {e}" for e in events) if events else "*Aucune partie prévue.*"

        embed.add_field(
            name=f"━━━━━━━━━━━━━━━\n**{day['jour']} {day['date']} {day['mois']}**",
            value=text,
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(aliases=["i", "h", "host"]) 
async def info(ctx): 
    await ctx.send("Si vous souhaitez avoir des games les jours où aucune game n'est prévue vous pouvez toujours en acheter en faisant un ticket pour acheter un host (3€)")
    
# ---------- AJOUTER PLANNING ----------
@bot.command(
    aliases=["ap", "aplanning", "addplanning", "addp"]
)
@commands.has_permissions(manage_messages=True)
async def ajouter_planning(ctx, jour: str, *, texte: str):
    jours = {
        "lundi": 0, "mardi": 1, "mercredi": 2,
        "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6
    }

    jour = jour.lower()
    if jour not in jours:
        await ctx.send("❌ Jour invalide (lundi → dimanche)")
        return

    week = get_week_days()
    day = week[jours[jour]]
    guild_id = ctx.guild.id

    plannings[guild_id][day["full_date"]].append(texte)
    save_event(guild_id, day["full_date"], texte)

    await ctx.send(f"✅ Événement ajouté pour **{day['jour']} {day['date']} {day['mois']}**")

# ---------- EFFACER PLANNING ----------
@bot.command(
    aliases=["ep", "eplanning", "clearplanning", "clearp"]
)
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

    week = get_week_days()
    day = week[jours[jour]]

    if day["full_date"] in plannings[guild_id]:
        del plannings[guild_id][day["full_date"]]
        delete_events(guild_id, day["full_date"])
        await ctx.send(f"✅ Planning du **{day['jour']}** effacé")
    else:
        await ctx.send("ℹ️ Aucun événement ce jour-là")

# ================== LANCEMENT ==================
bot.run(os.environ["TOKEN_BOT_DISCORD"])
