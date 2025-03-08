import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

# .env 파일에서 토큰 불러오기
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# 봇 설정 (intents 추가)
intents = discord.Intents.default()
intents.message_content = True  # 메시지 인식 기능 활성화
intents.voice_states = True  # 음성 채널 관련 기능 활성화

bot = commands.Bot(command_prefix="!", intents=intents)

# YouTube 다운로드 옵션
ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
}

ffmpeg_options = {
    'options': '-vn',
}

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')

    
@bot.command()
async def join(ctx):
    """ 사용자가 있는 음성 채널에 봇을 참가하고 명령어 목록 출력 """
    if ctx.author.voice:  # 사용자가 음성 채널에 있는지 확인
        channel = ctx.author.voice.channel  # 사용자가 있는 음성 채널 가져오기
        if ctx.voice_client:  # 봇이 이미 음성 채널에 있는 경우
            await ctx.voice_client.move_to(channel)  # 사용자의 채널로 이동
            await ctx.send(f'🔄 이미 음성 채널에 있어요! `{channel.name}` 채널로 이동했습니다.')
        else:
            await channel.connect()  # 봇을 음성 채널에 연결
            await ctx.send(f'🎶 **{bot.user.name}**이(가) `{channel.name}` 채널에 입장했어요!')

        # 🔹 봇이 채널에 입장한 후 명령어 목록 출력
        await ctx.send("❓ **사용 가능한 명령어 목록:**\n"
                       "`!join` - Music Bot이 음성 채널에 접속합니다.\n"
                       "`!leave` - Music Bot이 음성 채널에서 퇴장합니다.\n"
                       "`!play <유튜브 링크>` - 링크의 음악을 재생합니다.\n"
                       "`!skip` - 현재 곡을 건너뜁니다.\n"
                       "`!queue_list` - 링크가 등록된 대기열을 확인합니다.\n"
                       "`!stop` - 현재 재생중인 음악을 정지합니다.")

    else:
        await ctx.send("❌ 먼저 음성 채널에 들어가세요!")

@bot.command()
async def leave(ctx):
    """ 봇이 음성 채널에서 나가기 """
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 음성 채널에서 나갔어요!")
    else:
        await ctx.send("❌ 아직 음성 채널에 들어가 있지 않아요!")

import asyncio

queue = []  # 노래를 저장할 큐

@bot.command()
async def play(ctx, url: str):
    """ 유튜브 링크를 입력하면 음악을 재생하고, 기존 노래가 있으면 대기열에 추가 """
    global queue
    
    if ctx.voice_client and ctx.voice_client.is_playing():
        queue.append(url)  # 현재 노래가 재생 중이면 큐에 추가
        await ctx.send(f'➕ 다음 링크가 대기열에 추가되었어요 : {url}')
        return
    
    await play_music(ctx, url)

async def play_music(ctx, url: str):
    """ 유튜브에서 음악을 가져와 재생 """
    global queue

    if not ctx.voice_client:
        await ctx.invoke(join)  # 봇이 음성 채널에 없으면 먼저 참가

    await ctx.send(f'🎵 음악 정보를 가져오는 중이에요...')

    # yt-dlp 옵션 설정
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'extractaudio': True,
        'audioformat': 'mp3'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        url2 = info['url']

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    def after_playing(error):
        """ 현재 곡이 끝나면 자동으로 다음 곡 재생 """
        asyncio.run_coroutine_threadsafe(ctx.send(f'🎵 ** {info["title"]} 노래가 끝났어요~!**'), bot.loop)

        if queue:
            next_url = queue.pop(0)
            asyncio.run_coroutine_threadsafe(play_music(ctx, next_url), bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(ctx.send("✅ 대기열의 모든 곡을 재생 완료! 제 임무가 끝났어요."), bot.loop)

    ctx.voice_client.stop()
    ctx.voice_client.play(discord.FFmpegPCMAudio(url2, **ffmpeg_options), after=after_playing)
    await ctx.send(f'▶️ **{info["title"]}** 재생 중! 🎶')

@bot.command()
async def skip(ctx):
    """ 현재 재생 중인 곡을 건너뛰고 다음 곡을 재생 """
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏩ 다음 곡으로 넘어갑니다!")

@bot.command()
async def queue_list(ctx):
    """ 현재 대기열 출력 """
    if queue:
        queue_text = "\n".join([f"{i+1}. {url}" for i, url in enumerate(queue)])
        await ctx.send(f'🎵 **대기열 목록:**\n{queue_text}')
    else:
        await ctx.send("❌ 대기열이 비어 있네요...")

@bot.command()
async def stop(ctx):
    """ 음악을 멈춤 """
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹ 음악을 정지했어요!")
    else:
        await ctx.send("❌ 지금 재생 중인 음악이 없어요 ㅠㅠ")


# 봇 실행
bot.run(TOKEN)