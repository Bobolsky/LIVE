import discord
from discord.ext import commands
from settings import WELCOME_CHANNEL_ID, GOODBYE_CHANNEL_ID, DEFAULT_ROLE_IDS


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Benvenuto
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(f"Benvenuto {member.mention} nella Famiglia LIVE! <:LIVE:772499018831233034>")

        # Ruoli di default da assegnare
        roles = [member.guild.get_role(role_id) for role_id in DEFAULT_ROLE_IDS]
        for role in roles:
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    print(f"Non ho il permesso di aggiungere il ruolo {role.name} a {member.name}.")
                except discord.HTTPException as e:
                    print(f"Errore durante l'aggiunta del ruolo {role.name} a {member.name}: {str(e)}")

    # Addio
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = self.bot.get_channel(GOODBYE_CHANNEL_ID)
        if channel:
            await channel.send(f'**{member.name}** è morto. :skull:')


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
