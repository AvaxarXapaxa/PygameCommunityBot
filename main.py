import asyncio
import os
import random

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import discord
import pygame

from pgbot import commands, common, moderation, util


@common.bot.event
async def on_ready():
    """
    Startup routines when the bot starts
    """
    print("The PygameCommunityBot is now online!")
    print("The bot is present in these server(s):")
    for server in common.bot.guilds:
        print("-", server.name)
        for channel in server.channels:
            print(" +", channel.name)
            if channel.id == common.LOG_CHANNEL_ID:
                common.log_channel = channel
            if channel.id == common.ARRIVALS_CHANNEL_ID:
                common.arrivals_channel = channel
            if channel.id == common.GUIDE_CHANNEL_ID:
                common.guide_channel = channel
            if channel.id == common.ROLES_CHANNEL_ID:
                common.roles_channel = channel

    while True:
        await common.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name="discord.io/pygame_community"
            )
        )
        await asyncio.sleep(2.5)
        await common.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing, 
                name="in discord.io/pygame_community"
            )
        )
        await asyncio.sleep(2.5)


@common.bot.event
async def on_member_join(member: discord.Member):
    """
    This function handles the greet message when a new member joins
    """
    greet = random.choice(common.BOT_WELCOME_MSG["greet"])
    check = random.choice(common.BOT_WELCOME_MSG["check"])
 
    grab = random.choice(common.BOT_WELCOME_MSG["grab"])
    end = random.choice(common.BOT_WELCOME_MSG["end"])

    # This function is called right when a member joins, even before the member
    # finishes the join screening. So we wait for that to happen and then send 
    # the message
    while member.pending:
        await asyncio.sleep(3)

    # We can't use embed here, because the newly joined member won't be pinged
    await common.arrivals_channel.send(
        f"{greet} {member.mention}! {check} {common.guide_channel.mention}{grab} " +
        f"{common.roles_channel.mention}{end}"
    )


@common.bot.event
async def on_message(msg: discord.Message):
    """
    This function is called for every message by user.
    """
    if msg.author.bot:
        return

    if await moderation.check_sus(msg):
        return

    if msg.content.startswith(common.PREFIX):
        try:
            response = await util.send_embed(
                msg.channel,
                "Your command is being processed!",
                ""
            )

            await commands.handle(msg, response)

            common.cmd_logs[msg.id] = response
            if len(common.cmd_logs) > 100:
                del common.cmd_logs[common.cmd_logs.keys()[0]]
        except discord.HTTPException:
            pass


@common.bot.event
async def on_message_delete(msg: discord.Message):
    """
    This function is called for every message deleted by user.
    """
    if msg.id in common.cmd_logs.keys():
        del common.cmd_logs[msg.id]

    elif msg.author.id == common.bot.user.id:
        for log in common.cmd_logs.keys():
            if common.cmd_logs[log].id == msg.id:
                del common.cmd_logs[log]
                return


@common.bot.event
async def on_message_edit(old: discord.Message, new: discord.Message):
    """
    This function is called for every message edited by user.
    """
    if new.author.bot:
        return

    if await moderation.check_sus(new):
        return

    if new.content.startswith(common.PREFIX):
        try:
            if new.id in common.cmd_logs.keys():
                await commands.handle(new, common.cmd_logs[new.id])
        except discord.HTTPException:
            pass


if __name__ == "__main__":
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    common.window = pygame.display.set_mode((1, 1))
    common.bot.run(common.TOKEN)
