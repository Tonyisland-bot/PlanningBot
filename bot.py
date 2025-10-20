import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask
import threading

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

plannings = defaultdict(lambda: defaultdict(list))

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def init_database():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        try:
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
            cur.close()
    finally:
        conn.close()


def load_plannings():
    plannings.clear()

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute('SELECT guild_id, date, texte FROM plannings')
            rows = cur.fetchall()

            for row in rows:
                plannings[row['guild_id']][row['date']].append(row['texte'])
        finally:
            cur.close()
    finally:
        conn.close()


def save_event(guild_id, date, texte):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO plannings (guild_id, date, texte) VALUES (%s, %s, %s)',
                (guild_id, date, texte)
            )
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()


def delete_events(guild_id, date=None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        try:
            if date is None:
                cur.execute('DELETE FROM plannings WHERE guild_id = %s', (guild_id,))
            else:
                cur.execute(
                    'DELETE FROM plannings WHERE guild_id = %s AND date = %s',
                    (guild_id, date)
                )
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()


def get_week_days():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_days = []
    jours_fr = [
        'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'
    ]
    mois_fr = [
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
        'août', 'septembre', 'octobre', 'novembre', 'décembre'
    ]

    for i in range(7):
        day = monday + timedelta(days=i)
        week_days.append({
            'jour': jours_fr[i],
            'date': day.day,
            'mois': mois_fr[day.month - 1],
            'full_date': day.strftime('%Y-%m-%d')
        })
    return week_days


@bot.event
async def on_ready():
    print(f"✅ Bot connecté comme {bot.user}")
    init_database()
    load_plannings()
    total = sum(len(days) for guild in plannings.values() for days in guild.values())
    print(f"{bot.user} est connecté et {total} événements ont été chargés depuis la base !")



@bot.command()
@commands.has_permissions(manage_messages=True)
async def bonjour(ctx):
    await ctx.send(f'Bonjour {ctx.author.mention} !')
    await ctx.send(
        f'Je suis un bot qui donne des planning {ctx.author.mention} !')
    await ctx.send(f"J'espère que tu vas bien {ctx.author.mention} !")
    await ctx.send(
        f"Si tu as besoin d'aide, n'hésite pas à demander {ctx.author.mention} !"
    )
    await ctx.send(f"Je suis en cours de développement {ctx.author.mention} !")


@bot.command(aliases=['p', 'P', 'Planning'])
async def planning(ctx):
    week_days = get_week_days()
    guild_id = ctx.guild.id
    premier_jour = week_days[0]
    dernier_jour = week_days[6]
    description = f"Du {premier_jour['date']} {premier_jour['mois']} au {dernier_jour['date']} {dernier_jour['mois']}\n​"

    embed = discord.Embed(title="📅 Planning du Sonic UHC",
                          description=description,
                          color=discord.Color.blue())

    for day_info in week_days:
        jour = day_info['jour']
        date = day_info['date']
        mois = day_info['mois']
        full_date = day_info['full_date']

        events = plannings[guild_id].get(full_date, [])
        if events:
            events_text = '\n\n'.join(f"• {event}" for event in events)
            events_text = f"{events_text}\n​"
        else:
            events_text = "*Aucune partie prévue.*\n​"

        embed.add_field(name=f"━━━━━━━━━━━━━━━━━━━\n**{jour} {date} {mois}**",
                        value=events_text,
                        inline=False)

    await ctx.send(embed=embed)


@bot.command(aliases=['ap', 'aplanning'])
@commands.has_permissions(manage_messages=True)
async def ajouter_planning(ctx, jour: str, *, texte: str):
    week_days = get_week_days()
    guild_id = ctx.guild.id

    jour_lower = jour.lower()
    jours_map = {
        'lundi': 0,
        'mardi': 1,
        'mercredi': 2,
        'jeudi': 3,
        'vendredi': 4,
        'samedi': 5,
        'dimanche': 6
    }

    if jour_lower not in jours_map:
        await ctx.send(
            "❌ Jour invalide ! Utilisez : lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche"
        )
        return

    day_index = jours_map[jour_lower]
    day_info = week_days[day_index]
    full_date = day_info['full_date']

    plannings[guild_id][full_date].append(texte)
    save_event(guild_id, full_date, texte)

    await ctx.send(
        f"✅ Événement ajouté au planning du {day_info['jour']} {day_info['date']} {day_info['mois']} !"
    )


@bot.command(aliases=[
    'ep',
    'eplanning',
])
@commands.has_permissions(manage_messages=True)
async def effacer_planning(ctx, jour: str | None = None):
    guild_id = ctx.guild.id

    if jour is None:
        plannings[guild_id].clear()
        delete_events(guild_id)
        await ctx.send("✅ Tout le planning a été effacé !")
    else:
        week_days = get_week_days()
        jour_lower = jour.lower()
        jours_map = {
            'lundi': 0,
            'mardi': 1,
            'mercredi': 2,
            'jeudi': 3,
            'vendredi': 4,
            'samedi': 5,
            'dimanche': 6
        }

        if jour_lower not in jours_map:
            await ctx.send(
                "❌ Jour invalide ! Utilisez : lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche"
            )
            return

        day_index = jours_map[jour_lower]
        day_info = week_days[day_index]
        full_date = day_info['full_date']

        if full_date in plannings[guild_id]:
            del plannings[guild_id][full_date]
            delete_events(guild_id, full_date)
            await ctx.send(f"✅ Planning du {day_info['jour']} effacé !")
        else:
            await ctx.send(f"ℹ️ Aucun événement pour {day_info['jour']}")

@bot.command()
async def debug_planning(ctx):
    guild_id = ctx.guild.id
    events = plannings[guild_id]
    if not events:
        await ctx.send("Aucun planning chargé en mémoire.")
    else:
        count = sum(len(v) for v in events.values())
        await ctx.send(f"{count} événements chargés pour ce serveur.")



@bonjour.error
@ajouter_planning.error
@effacer_planning.error
async def permission_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Vous devez être modérateur pour utiliser cette commande !")

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    bot.run(TOKEN)

token = os.environ["TOKEN_BOT_DISCORD"]
bot.run(token)
