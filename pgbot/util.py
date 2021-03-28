import asyncio
import re

import discord

from . import common


def format_time(seconds: float, decimal_places: int = 4):
    """
    Formats time with a prefix
    """
    for fractions, unit in [
        (1.0, "s"),
        (1e-03, "ms"),
        (1e-06, "\u03bcs"),
        (1e-09, "ns"),
        (1e-12, "ps"),
        (1e-15, "fs"),
        (1e-18, "as"),
        (1e-21, "zs"),
        (1e-24, "ys"),
    ]:
        if seconds >= fractions:
            return f"{seconds / fractions:.0{decimal_places}f} {unit}"
    return f"very fast"


def format_long_time(seconds):
    result = []

    for name, count in (
            ('weeks', 604800),
            ('days', 86400),
            ('hours', 3600),
            ('minutes', 60),
            ('seconds', 1),
    ):
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name[:-1]
            result.append("{} {}".format(value, name))
    return ', '.join(result)


def format_byte(size: int, decimal_places=3):
    """
    Formats a given size and outputs a string equivalent to B, KB, MB, or GB
    """
    if size < 1e03:
        return f"{round(size, decimal_places)} B"
    if size < 1e06:
        return f"{round(size / 1e3, decimal_places)} KB"
    if size < 1e09:
        return f"{round(size / 1e6, decimal_places)} MB"

    return f"{round(size / 1e9, decimal_places)} GB"


def split_long_message(message: str):
    """
    Splits message string by 2000 characters with safe newline splitting
    """
    split_output = []
    lines = message.split('\n')
    temp = ""

    for line in lines:
        if len(temp) + len(line) + 1 > 2000:
            split_output.append(temp[:-1])
            temp = line + '\n'
        else:
            temp += line + '\n'

    if temp:
        split_output.append(temp)

    return split_output


def filter_id(mention: str):
    """
    Filters mention to get ID "<@!6969>" to "6969"
    Note that this function can error with ValueError on the int call, so the
    caller of this function must take care of this
    """
    for char in ("<", ">", "@", "&", "#", "!", " "):
        mention = mention.replace(char, "")

    return int(mention)


def get_embed_fields(messages):
    # syntax: <Field|Title|desc.[|inline=False]>
    field_regex = r"(<Field\|.*\|.*(\|True|\|False|)>)"
    field_datas = []

    for message in messages:
        field_list = re.split(field_regex, message)
        for field in field_list:
            if field:
                field = field[1:-1]
                field_data = field.split("|")

                if len(field_data) not in [3, 4]:
                    continue
                if len(field_data) == 3:
                    field_data.append("")

                field_data[3] = True if field_data[3] == "True" else False

                field_datas.append(field_data[1:])

    return field_datas

async def edit_embed(message, title, description, color=0xFFFFAA, url_image=None, fields=[]):
    """
    Edits the embed of a message with a much more tight function
    """
    embed = discord.Embed(title=title, description=description, color=color)
    if url_image:
        embed.set_image(url=url_image)

    for field in fields:
        embed.add_field(name=field[0], value=field[1], inline=field[2])

    return await message.edit(embed=embed)


async def send_embed(channel, title, description, color=0xFFFFAA, url_image=None, fields=[]):
    """
    Sends an embed with a much more tight function
    """
    embed = discord.Embed(title=title, description=description, color=color)
    if url_image:
        embed.set_image(url=url_image)

    for field in fields:
        embed.add_field(name=field[0], value=field[1], inline=field[2])

    return await channel.send(embed=embed)


async def format_archive_messages(messages):
    """
    Formats a message to be archived
    """
    formatted_msgs = []
    for message in messages:
        triple_block_quote = '```'

        author = f"{message.author} ({message.author.mention}) [{message.author.id}]"
        content = message.content.replace('\n', '\n> ') if message.content else None

        if message.attachments:
            attachment_list = []
            for i, attachment in enumerate(message.attachments):
                filename = repr(attachment.filename)
                attachment_list.append(
                    f'{i + 1}:\n    **Name**: {filename}\n    **URL**: {attachment.url}')
            attachments = '\n> '.join(attachment_list)
        else:
            attachments = ""

        if message.embeds:
            embed_list = []
            for i, embed in enumerate(message.embeds):
                if isinstance(embed, discord.Embed):
                    if isinstance(embed.description, str):
                        desc = embed.description.replace(
                            triple_block_quote, common.ESC_CODE_BLOCK_QUOTE)
                    else:
                        desc = '\n'

                    embed_list.append(
                        f'{i + 1}:\n    **Title**: {embed.title}\n    **Description**: ```\n{desc}```\n    **Image URL**: {embed.image.url}')
                else:
                    embed_list.append('\n')
            embeds = '\n> '.join(embed_list)
        else:
            embeds = ""

        formatted_msgs.append(
            f"**AUTHOR**: {author}\n" +
            (f"**MESSAGE**: \n> {content}\n" if content else "") +
            (f"**ATTACHMENT(S)**: \n> {attachments}\n" if message.attachments else "") +
            (f"**EMBED(S)**: \n> {embeds}\n" if message.embeds else "")
        )
        await asyncio.sleep(0.01)  # Lets the bot do other things

    return formatted_msgs
