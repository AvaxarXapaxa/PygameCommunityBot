import asyncio
import builtins
import itertools
import json
import math
import os
import pickle
import random
import re
import socket
import string
import sys
import threading
import time
import timeit

import discord
import numpy
import pkg_resources
import psutil
import pygame
import pygame.gfxdraw

from sandbox import exec_sandbox
from util import format_byte, format_time, safe_subscripting, send_embed
from constants import *

last_pet = time.time() - 3600
pet_anger = 0.1
PET_COST = 0.1
JUMPSCARE_THRESHOLD = 20.0
PET_INTERVAL = 60.0

doc_modules = {  # Modules to provide documentation for
    "pygame": pygame,
    "numpy": numpy,
    "discord": discord,
    "asyncio": asyncio,
    "json": json,
    "sys": sys,
    "os": os,
    "socket": socket,
    "random": random,
    "re": re,
    "math": math,
    "pickle": pickle,
    "threading": threading,
    "time": time,
    "timeit": timeit,
    "string": string,
    "itertools": itertools,
    "builtins": builtins,
}

for module in sys.modules:
    doc_modules[module] = sys.modules[module]

pkgs = sorted(
    [i.key for i in pkg_resources.working_set]
)  # pylint: disable=not-an-iterable
process = psutil.Process(os.getpid())

for module in pkgs:
    try:
        doc_modules[module] = __import__(module.replace("-", "_"))
    except BaseException:
        pass


async def admin_command(msg: discord.Message, args: list, prefix: str):
    if safe_subscripting(args, 0) == "eval" and len(args) > 1:
        try:
            script = compile(
                msg.content[len(prefix) + 5 :], "<string>", "eval"
            )  # compile script first

            script_start = time.perf_counter()
            eval_output = eval(script)  # pylint: disable = eval-used
            script_duration = time.perf_counter() - script_start

            enhanced_eval_output = repr(eval_output).replace(
                "```", "\u200e`\u200e`\u200e`\u200e"
            )

            # TODO: Create ellipsis functionality
            if len(enhanced_eval_output) + 11 > 2048:
                await send_embed(
                    msg.channel,
                    f"Return output (code executed in {format_time(script_duration)}):",
                    "```\n" + enhanced_eval_output[:2037] + " ...```",
                )
            else:
                await send_embed(
                    msg.channel,
                    f"Return output (code executed in {format_time(script_duration)}):",
                    "```\n" + enhanced_eval_output + "```",
                )

        except Exception as ex:
            exp = (
                type(ex).__name__.replace("```", "\u200e`\u200e`\u200e`\u200e")
                + ": "
                + ", ".join([str(t) for t in ex.args]).replace(
                    "```", "\u200e`\u200e`\u200e`\u200e"
                )
            )

            if len(exp) + 11 > 2048:
                await send_embed(
                    msg.channel,
                    "An exception occured!",
                    "```\n" + exp[:2037] + " ...```",
                )
            else:
                await send_embed(
                    msg.channel, "An exception occured!", "```\n" + exp + "```"
                )

    elif safe_subscripting(args, 0) == "sudo" and len(args) > 1:
        await msg.channel.send(msg.content[len(prefix) + 5 :])
        await msg.delete()

    elif safe_subscripting(args, 0) == "heap" and len(args) == 1:
        mem = process.memory_info().rss
        await send_embed(
            msg.channel, "Total memory used:", f"**{format_byte(mem, 4)}**\n({mem} B)"
        )

    elif safe_subscripting(args, 0) == "stop" and len(args) == 1:
        await send_embed(
            msg.channel,
            "Stopping bot...",
            "Change da world,\nMy final message,\nGoodbye.",
        )
        sys.exit(1)

    else:
        await user_command(msg, args, prefix, True, True)


async def user_command(
    msg: discord.Message, args: list, prefix: str, is_priv=False, is_admin=False
):
    # TODO: Check possible removal of globals
    global last_pet, pet_anger

    if safe_subscripting(args, 0) == "doc" and len(args) == 2:
        splits = args[1].split(".")

        if safe_subscripting(splits, 0) not in doc_modules:
            await send_embed(
                msg.channel,
                "Unknown module!",
                "No such module is available for its documentation",
            )
            return
        objects = doc_modules
        obj = None

        for part in splits:
            try:
                obj = objects[part]
                try:
                    objects = vars(obj)
                except BaseException:  # TODO: Figure out proper exception
                    objects = {}
            except BaseException:  # TODO: Figure out proper exception
                await send_embed(
                    msg.channel,
                    "Class/function/sub-module not found!",
                    "There's no such thing here named `{args[1]}`",
                )
                return
        messg = str(obj.__doc__).replace("```", "\u200e`\u200e`\u200e`\u200e")

        if len(messg) + 11 > 2048:
            await send_embed(
                msg.channel,
                f"Documentation for {args[1]}",
                "```\n" + messg[:2037] + " ...```",
            )
            return

        messg = "```\n" + messg + "```\n\n"

        if safe_subscripting(splits, 0) == "pygame":
            doclink = "https://www.pygame.org/docs"
            if len(splits) > 1:
                doclink += "/ref/" + safe_subscripting(splits, 1).lower() + ".html"
                doclink += "#"
                doclink += "".join([s + "." for s in splits])[:-1]
            messg = "Online documentation: " + doclink + "\n" + messg

        for obj in objects:
            if obj.startswith("__"):
                continue
            if type(objects[obj]).__name__ not in (
                "module",
                "type",
                "function",
                "method_descriptor",
                "builtin_function_or_method",
            ):
                continue
            messg += "**" + type(objects[obj]).__name__.upper() + "** `" + obj + "`\n"

        if len(messg) > 2048:
            await send_embed(
                msg.channel, f"Documentation for {args[1]}", messg[:2044] + " ..."
            )
        else:
            await send_embed(msg.channel, f"Documentation for {args[1]}", messg)

    elif safe_subscripting(args, 0) == "exec" and len(args) > 1:
        code = msg.content[len(prefix) + 5 :]
        ret = ""

        # TODO: Strange construct what this does?
        for i in range(len(code)):
            if code[i] in [" ", "`", "\n"]:
                ret = code[i + 1 :]
            else:
                break
        code = ret

        for i in reversed(range(len(code))):
            if code[i] in [" ", "`", "\n"]:
                ret = code[:i]
            else:
                break

        if ret.startswith("py\n"):
            ret = ret[3:]

        start = time.time()
        returned = await exec_sandbox(ret, 5 if is_priv else 2)
        duration = returned.duration  # the execution time of the script alone

        if not isinstance(returned.exc, BaseException):
            if isinstance(returned.img, pygame.Surface):
                pygame.image.save(returned.img, f"temp{start}.png")
                if os.path.getsize(f"temp{start}.png") < 2 ** 22:
                    await msg.channel.send(file=discord.File(f"temp{start}.png"))
                else:
                    await send_embed(
                        msg.channel,
                        "Image cannot be sent",
                        "The image file size is >4MiB",
                    )
                os.remove(f"temp{start}.png")
            str_repr = str(returned.text).replace(
                "```", "\u200e`\u200e`\u200e`\u200e"
            )
            if str_repr == "":
                str_repr = " "

            if len(str_repr) + 11 > 2048:
                await send_embed(
                    msg.channel,
                    f"Returned text (code executed in {format_time(duration)}):",
                    "```\n" + str_repr[:2037] + " ...```",
                )
            else:
                await send_embed(
                    msg.channel,
                    f"Returned text (code executed in {format_time(duration)}):",
                    "```\n" + str_repr + "```",
                )

        else:
            exp = (
                type(returned.exc).__name__.replace(
                    "```", "\u200e`\u200e`\u200e`\u200e"
                )
                + ": "
                + ", ".join([str(t) for t in returned.exc.args]).replace(
                    "```", "\u200e`\u200e`\u200e`\u200e"
                )
            )

            if len(exp) + 11 > 2048:
                await send_embed(
                    msg.channel,
                    "An exception occured!",
                    "```\n" + exp[:2037] + " ...```",
                )
            else:
                await send_embed(
                    msg.channel, "An exception occured!", "```\n" + exp + "```"
                )

    elif safe_subscripting(args, 0) == "pet" and len(args) == 1:
        pet_anger -= (time.time() - last_pet - PET_INTERVAL) * (
            pet_anger / JUMPSCARE_THRESHOLD
        ) - PET_COST

        if pet_anger < PET_COST:
            pet_anger = PET_COST
        last_pet = time.time()

        if pet_anger > JUMPSCARE_THRESHOLD:
            await msg.channel.send(
                "https://raw.githubusercontent.com/AvaxarXapaxa/PygameCommunityBot/main/save/die.gif"
            )
        else:
            await msg.channel.send(
                "https://raw.githubusercontent.com/AvaxarXapaxa/PygameCommunityBot/main/save/pet.gif"
            )

    elif safe_subscripting(args, 0) == "vibecheck" and len(args) == 1:
        await send_embed(
            msg.channel,
            "Vibe Check, snek?",
            f"Previous petting anger: {pet_anger:.2f}/{JUMPSCARE_THRESHOLD:.2f}\nIt was last pet {time.time() - last_pet:.2f} second(s) ago",
        )

    elif safe_subscripting(args, 0) == "clock" and len(args) == 1:
        image = pygame.Surface((1280, 1280)).convert_alpha()
        font = pygame.font.Font("save/tahoma.ttf", 36)
        texts = []
        t = time.time()
        font.bold = True

        image.fill((0, 0, 0, 0))
        pygame.draw.circle(image, (255, 255, 146), (640, 640), 600, draw_top_left=True, draw_top_right=True)
        pygame.draw.circle(image, (0, 32, 96), (640, 640), 600, draw_bottom_left=True, draw_bottom_right=True)
        pygame.draw.circle(image, (0, 0, 0), (640, 640), 620, 32)

        for offset, name, color in CLOCK_TIMEZONES:
            angle = (t + offset) % 86400 / 86400 * 360 + 180
            s, c = math.sin(math.radians(angle)), math.cos(math.radians(angle))
            pygame.draw.line(image, color, (640, 640), (s * 560 + 640, -c * 560 + 640), 32)
            color = 255 - random.randint(0, 86)
            text = font.render(name, True, (color, 0, 0))
            texts.append((text, (s * 500 + 640 - text.get_width() // 2, -c * 500 + 640 - text.get_height() // 2)))
        pygame.draw.circle(image, (0, 0, 0), (640, 640), 64)

        for text, pos in texts:
            image.blit(text, pos)

        pygame.image.save(image, f"temp{t}.png")
        await msg.channel.send(file=discord.File(f"temp{t}.png"))
        os.remove(f"temp{t}.png")

    elif safe_subscripting(args, 0) == "version" and len(args) == 1:
        await send_embed(msg.channel, 'Current bot\'s version', f'`{VERSION}`')
