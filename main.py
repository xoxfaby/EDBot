import discord
import aiohttp
import asyncio

from random import choice

from config import token
from config import dev
from config import activities
from config import channels_setup
from config import roles_setup

client = discord.Client()
client.built = False
systems_json = {}
zws = "​"   #zero width space for formatting in discord

client.i = 0


async def metallic_search(message):
    search_string = message.content[1:].replace("`", "")
    params = {'systemName': search_string}
    async with message.channel.typing():
        async with client.session.request('get', 'https://www.edsm.net/api-v1/sphere-systems', params=params) as r:
            rjson = await r.json()
            if not rjson:
                async with client.session.request('get', 'https://www.edsm.net/api-v1/systems',
                                                  params=params) as r2:
                    r2json = await r2.json()
                    if not r2json:
                        await message.channel.send(
                            f"I'm sorry, {message.author.mention}, I couldn't find `{search_string}`")
                        return
                    search_string = r2json[0]['name']
                    params = {'systemName': search_string}
                    r = await client.session.request('get', 'https://www.edsm.net/api-v1/sphere-systems', params=params)
                    rjson = await r.json()
                    if not rjson:
                        await message.channel.send(
                            f"I'm sorry, {message.author.mention}, I couldn't find `{search_string}`")
                        return
            rjson = [system for system in rjson if systems_json.get(system['name'])]
            rsorted = sorted(rjson, key=lambda x: x['distance'])[:5]
            embed = discord.Embed(title=f"Closest Pristine Metallics to  {search_string}:",
                                  color=discord.Color.dark_orange())
            if not len(rsorted):
                await message.channel.send(
                    f"I'm sorry, {message.author.mention}, no Pristine Metallics within 100ly of `{search_string}`")
                return
            for system in rsorted:
                psystem = systems_json[system['name']]
                if psystem.get('res'):
                    if psystem.get('res') == 'no':
                        pRes = '**RES**: no'
                    else:
                        pRes = '**RES**: yes'
                else:
                    pRes = '**RES**: *<unknown>*'
                value = ( f"{zws} **Security**: {psystem.get('security','')}   "
                          f"**Rings**: {psystem.get('rings','')}   "
                          + pRes )

                embed.add_field(name=f"**{system['distance']}ly**   {system['name']}", value=value, inline=False)

            await message.channel.send(embed=embed)

async def grant_role(message):
    if message.content.lower()[1:] in roles[message.guild.id]:
        try:
            await message.author.add_roles(roles[message.guild.id][message.content.lower()[1:]])
            await message.add_reaction('\U00002705')
        except Exception as e:
            await message.add_reaction('\U0000274c')
            raise
    else:
        await message.add_reaction('\U0000274c')

async def revoke_role(message):
    if message.content.lower()[1:] in roles[message.guild.id]:
        try:
            await message.author.remove_roles(roles[message.guild.id][message.content.lower()[1:]])
            await message.add_reaction('\U00002705')
        except:
            await message.add_reaction('\U0000274c')
            raise
    else:
        await message.add_reaction('\U0000274c')

async def test(message):
    return

async def status_changer():
    await client.wait_until_ready()
    while not client.is_closed():
        await client.change_presence(activity=choice(activities))
        await asyncio.sleep(60*60*3)

roles = {}
channels={}
commands={
    'metallic_finder':{
        '!':metallic_search
    },
    'platform':{
        '+':grant_role,
        '-':revoke_role
    },
    'bot_testing':{
        't':test
    }
}

commands_dev={}
for k,v in commands.items():
    for prefix,func in v.items():
        commands_dev[prefix] = func
if dev:
    commands = {'bot_testing':commands_dev}
else:
    commands['bot_testing'] = commands_dev

@client.event
async def on_ready():
    client.session = aiohttp.ClientSession()
    global systems_json
    async with client.session.request('get', 'http://edtools.ddns.net/pris_met.json') as systems:
        systems_json = await systems.json()
    for guild in client.guilds:
        print(f"Building channels and roles for {guild.name}")
        channels[guild.id] = {}
        for channel,fallback in channels_setup.items():
            found_channel = discord.utils.find(lambda c:c.name.lower() == channel.lower(),guild.text_channels) \
                                          or guild.get_channel(fallback)
            if found_channel:
                channels[guild.id][found_channel.id] = channel
            else:
                print("Could not find all channels.")
                del channels[guild.id]

        roles[guild.id] = {}
        for role in roles_setup:
            roles[guild.id][role] = discord.utils.find(lambda r:r.name.lower() == role.lower(),guild.roles)
            if not roles[guild.id][role]:
                del roles[guild.id][role]

        print(f"Found roles {', '.join([role.name for role in roles[guild.id].values()])}")

    client.built = True
    print('Done')
    client.status_changer = client.loop.create_task(status_changer())



@client.event
async def on_message(message):
    if client.built and message.guild.id in channels:
        if message.channel.id in channels[message.guild.id]:
            if message.content[0] in commands[channels[message.guild.id][message.channel.id]]:
                await commands[channels[message.guild.id][message.channel.id]][message.content[0]](message)



client.run(token)