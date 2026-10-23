import aiohttp
from discord.ext import commands, tasks
from settings import MEDAL_CHANNEL_ID

medal_users = ['154233863', '60469834', '6577771']


class Medal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_video_ids = {}

    async def cog_load(self):
        pass  # self.check_medal_users_videos.start()

    async def cog_unload(self):
        self.check_medal_users_videos.cancel()

    @tasks.loop(seconds=30)
    async def check_medal_users_videos(self):
        url_base = "https://developers.medal.tv/v1/latest?limit=1"
        headers = {'Authorization': 'pub_4fJs7veQ3yFWSnvL8nxG9aQ8maQIdlFd'}
        for user_id in medal_users:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url_base}&userId={user_id}", headers=headers) as response:
                    if response.status != 200:
                        print(f"Errore durante la richiesta all'API: {response.status}")
                        continue
                    data = await response.json()

            if data and data['contentObjects']:
                video = data['contentObjects'][0]
                # Verifica se è un nuovo video
                if self.last_video_ids.get(user_id) != video['contentId']:
                    self.last_video_ids[user_id] = video['contentId']
                    channel = self.bot.get_channel(MEDAL_CHANNEL_ID)
                    if channel:
                        await channel.send(video['directClipUrl'])

    @check_medal_users_videos.before_loop
    async def before_check_medal_users_videos(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Medal(bot))
