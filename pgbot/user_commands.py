import asyncio
import os
import random
import time

import discord
import pygame

from . import clock, common, docs, emotion, sandbox, util


class UserCommand:
    """
    Base class to handle user commands.
    """
    def __init__(self):
        """
        Initialise UserCommand class
        """
        # Create a dictionary of command names and respective handler functions
        self.cmds_and_funcs = {}
        for i in dir(self):
            if i.startswith("cmd_"):
                self.cmds_and_funcs[i[len("cmd_"):]] = self.__getattribute__(i)

    async def handle_cmd(
        self, invoke_msg: discord.Message, resp_msg: discord.Message, is_priv
    ):
        """
        Calles the appropriate sub function to handle commands.
        Must return True on successful command execution, False otherwise
        """
        self.invoke_msg = invoke_msg
        self.response_msg = resp_msg

        cmd_str = invoke_msg.content[len(common.PREFIX):].lstrip()
        self.args = cmd_str.split()
        cmd = self.args.pop(0)
        self.string = cmd_str[len(cmd):].strip()
        self.is_priv = is_priv

        try:
            await self.cmds_and_funcs[cmd]()
            return True
        except (KeyError, RuntimeError):
            return False

    def check_args(self, minarg, maxarg=None):
        """
        A utility for a function to check that the correct number of args were
        passed
        """
        if maxarg is None:
            maxarg = minarg

        if not (minarg <= len(self.args) <= maxarg):
            raise RuntimeError()

    async def cmd_version(self):
        """
        Implement pg!version, to report bot version
        """
        self.check_args(0)
        await util.edit_embed(
            self.response_msg, "Current bot's version", f"`{common.VERSION}`"
        )

    async def cmd_clock(self):
        """
        Implement pg!clock, to display a clock of helpfulies/mods/wizards
        """
        self.check_args(0)

        t = time.time()
        pygame.image.save(clock.user_clock(t), f"temp{t}.png")
        common.cmd_logs[self.invoke_msg.id] = \
            await self.response_msg.channel.send(
                file=discord.File(f"temp{t}.png")
            )
        await self.response_msg.delete()
        os.remove(f"temp{t}.png")

    async def cmd_doc(self):
        """
        Implement pg!doc, to view documentation
        """
        self.check_args(1)

        title, body = docs.get(self.args[0])
        await util.edit_embed(self.response_msg, title, body)

    async def cmd_exec(self):
        """
        Implement pg!exec, for execution of python code
        """
        code = self.string.lstrip('`').rstrip('`')
        if code.startswith("python\n"):
            code = code[7:]
        elif code.startswith("py\n"):
            code = code[3:]

        start = time.perf_counter()
        returned = await sandbox.exec_sandbox(code, 10 if self.is_priv else 5)
        duration = returned.duration  # the execution time of the script alone

        if not isinstance(returned.exc, BaseException):
            if isinstance(returned.img, pygame.Surface):
                pygame.image.save(returned.img, f"temp{start}.png")
                if os.path.getsize(f"temp{start}.png") < 2 ** 22:
                    await self.response_msg.channel.send(
                        file=discord.File(f"temp{start}.png")
                    )
                else:
                    await util.edit_embed(
                        self.response_msg,
                        "Image cannot be sent:",
                        "The image file size is above 4MiB",
                    )
                os.remove(f"temp{start}.png")

            str_repr = str(returned.text).replace(
                "```", common.ESC_CODE_BLOCK_QUOTE
            )

            # if not str_repr and isinstance(returned.img, pygame.Surface):
            #     return

            if len(str_repr) + 11 > 2048:
                await util.edit_embed(
                    self.response_msg,
                    f"Returned text (code executed in {util.format_time(duration)}):",
                    "```\n" + str_repr[:2037] + " ...```",
                )
            else:
                await util.edit_embed(
                    self.response_msg,
                    f"Returned text (code executed in {util.format_time(duration)}):",
                    "```\n" + str_repr + "```",
                )

        else:
            exp = (
                    type(returned.exc).__name__.replace(
                        "```", common.ESC_CODE_BLOCK_QUOTE
                    )
                    + ": "
                    + ", ".join(str(t) for t in returned.exc.args).replace(
                      "```", common.ESC_CODE_BLOCK_QUOTE
                    )
            )

            if len(exp) + 11 > 2048:
                await util.edit_embed(
                    self.response_msg,
                    common.EXC_TITLES[1],
                    "```\n" + exp[:2037] + " ...```",
                )
            else:
                await util.edit_embed(
                    self.response_msg,
                    common.EXC_TITLES[1],
                    "```\n" + exp + "```"
                )

    async def cmd_help(self):
        """
        Implement pg!help, to display a help message
        """
        self.check_args(0)
        await util.edit_embed(
            self.response_msg,
            common.BOT_HELP_PROMPT["title"][0],
            common.BOT_HELP_PROMPT["message"][0],
            common.BOT_HELP_PROMPT["color"][0]
        )

    async def cmd_pet(self):
        """
        Implement pg!pet, to pet the bot
        """
        self.check_args(0)
        emotion.pet_anger -= (time.time() - emotion.last_pet - common.PET_INTERVAL) * (
                emotion.pet_anger / common.JUMPSCARE_THRESHOLD
        ) - common.PET_COST

        if emotion.pet_anger < common.PET_COST:
            emotion.pet_anger = common.PET_COST
        emotion.last_pet = time.time()

        fname = "die.gif" if emotion.pet_anger > common.JUMPSCARE_THRESHOLD else "pet.gif"
        await util.edit_embed(
            self.response_msg,
            "",
            "",
            0xFFFFAA,
            "https://raw.githubusercontent.com/PygameCommunityDiscord/" +
            f"PygameCommunityBot/main/assets/images/{fname}"
        )

    async def cmd_vibecheck(self):
        """
        Implement pg!vibecheck, to check if the bot is angry
        """
        self.check_args(0)
        await util.edit_embed(
            self.response_msg,
            "Vibe Check, snek?",
            f"Previous petting anger: {emotion.pet_anger:.2f}/{common.JUMPSCARE_THRESHOLD:.2f}" +
            f"\nIt was last pet {util.format_long_time(round(time.time() - emotion.last_pet))} ago",
        )

    async def cmd_sorry(self):
        """
        Implement pg!sorry, to ask forgiveness from the bot after bonccing it
        """
        self.check_args(0)
        if not emotion.boncc_count:
            await util.edit_embed(
                self.response_msg,
                "Ask forgiveness from snek?",
                "Snek is happy. Awww, don't be sorry."
            )
            return

        if random.random() < common.SORRY_CHANCE:
            emotion.boncc_count -= common.BONCC_PARDON
            if emotion.boncc_count < 0:
                emotion.boncc_count = 0
            await util.edit_embed(
                self.response_msg,
                "Ask forgiveness from snek?",
                "Your pythonic lord accepts your apology.\n" +
                f"Now go to code again.\nThe boncc count is {emotion.boncc_count}"
            )
        else:
            await util.edit_embed(
                self.response_msg,
                "Ask forgiveness from snek?",
                "How did you dare to boncc a snake?\nBold of you to assume " +
                "I would apologize to you, two-feet-standing being!\nThe " +
                f"boncc count is {emotion.boncc_count}"
            )

    async def cmd_bonkcheck(self):
        """
        Implement pg!bonkcheck, to check how much the snek has been boncced
        """
        self.check_args(0)
        if emotion.boncc_count:
            await util.edit_embed(
                self.response_msg,
                "The snek is hurt and angry:",
                f"The boncc count is {emotion.boncc_count}"
            )
        else:
            await util.edit_embed(
                self.response_msg,
                "The snek is right",
                "Please, don't hit the snek"
            )
