import os
import sys
import time

import psutil

from . import user_commands, common, util

process = psutil.Process(os.getpid())


class AdminCommand(user_commands.UserCommand):
    """
    Base class to handle admin commands. Inherits all user commands, and also
    implements some more
    """
    async def cmd_eval(self):
        """
        Implement pg!eval, for admins to run arbitrary code on the bot
        """
        try:
            script = compile(
                self.string, "<string>", "eval"
            )  # compile script first

            script_start = time.perf_counter()
            eval_output = eval(script)  # pylint: disable = eval-used
            script_duration = time.perf_counter() - script_start

            enhanced_eval_output = repr(eval_output).replace(
                "```", common.ESC_CODE_BLOCK_QUOTE
            )

            if len(enhanced_eval_output) + 11 > 2048:
                await util.edit_embed(
                    self.response_msg,
                    f"Return output (code executed in {util.format_time(script_duration)}):",
                    "```\n" + enhanced_eval_output[:2037] + " ...```",
                )
            else:
                await util.edit_embed(
                    self.response_msg,
                    f"Return output (code executed in {util.format_time(script_duration)}):",
                    "```\n" + enhanced_eval_output + "```",
                )
        except Exception as ex:
            exp = (
                    type(ex).__name__.replace("```", common.ESC_CODE_BLOCK_QUOTE)
                    + ": "
                    + ", ".join(str(t) for t in ex.args).replace(
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
                    self.response_msg, common.EXC_TITLES[1], "```\n" + exp + "```"
                )

    async def cmd_sudo(self):
        """
        Implement pg!sudo, for admins to send messages via the bot
        """
        await self.invoke_msg.channel.send(self.string)
        await self.response_msg.delete()
        await self.invoke_msg.delete()

    async def cmd_sudo_edit(self):
        """
        Implement pg!sudo_edit, for admins to edit messages via the bot
        """
        edit_msg = await self.invoke_msg.channel.fetch_message(
            util.filter_id(self.args[0])
        )
        await edit_msg.edit(content=self.string[len(self.args[0]) + 1:])
        await self.response_msg.delete()
        await self.invoke_msg.delete()

    async def cmd_heap(self):
        """
        Implement pg!heap, for admins to check memory taken up by the bot
        """
        self.check_args(0)
        mem = process.memory_info().rss
        await util.edit_embed(
            self.response_msg,
            "Total memory used:",
            f"**{util.format_byte(mem, 4)}**\n({mem} B)"
        )

    async def cmd_stop(self):
        """
        Implement pg!stop, for admins to stop the bot
        """
        self.check_args(0)
        await util.edit_embed(
            self.response_msg,
            "Stopping bot...",
            "Change da world,\nMy final message,\nGoodbye."
        )
        sys.exit(0)

    async def cmd_emsudo(self):
        """
        Implement pg!emsudo, for admins to send images via the bot
        """
        args = eval(self.string)

        if len(args) == 1:
            await util.send_embed(
                self.invoke_msg.channel,
                args[0],
                ""
            )
        elif len(args) == 2:
            await util.send_embed(
                self.invoke_msg.channel,
                args[0],
                args[1]
            )
        elif len(args) == 3:
            await util.send_embed(
                self.invoke_msg.channel,
                args[0],
                args[1],
                args[2]
            )
        elif len(args) == 4:
            if isinstance(args[3], list):
                fields = util.get_embed_fields(args[3])
                await util.send_embed(
                    self.invoke_msg.channel,
                    args[0],
                    args[1],
                    args[2],
                    fields=fields
                )
            else:
                await util.send_embed(
                    self.invoke_msg.channel,
                    args[0],
                    args[1],
                    args[2],
                    args[3]
                )
        elif len(args) == 5:
            fields = util.get_embed_fields(args[3])
            await util.send_embed(
                self.invoke_msg.channel,
                args[0],
                args[1],
                args[2],
                args[3],
                fields=fields
            )
        else:
            await util.edit_embed(
                self.response_msg,
                "Invalid arguments!",
                ""
            )
            return

        await self.response_msg.delete()
        await self.invoke_msg.delete()

    async def cmd_emsudo_edit(self):
        """
        Implement pg!emsudo_edit, for admins to edit images via the bot
        """
        args = eval(self.string)
        edit_msg = await self.invoke_msg.channel.fetch_message(
            args[0]
        )

        if len(args) == 2:
            await util.edit_embed(
                edit_msg,
                args[1],
                ""
            )
        elif len(args) == 3:
            await util.edit_embed(
                edit_msg,
                args[1],
                args[2]
            )
        elif len(args) == 4:
            await util.edit_embed(
                edit_msg,
                args[1],
                args[2],
                args[3]
            )
        elif len(args) == 5:
            if isinstance(args[4], list):
                fields = util.get_embed_fields(args[4])
                await util.edit_embed(
                    edit_msg,
                    args[1],
                    args[2],
                    args[3],
                    fields=fields
                )
            else:
                await util.edit_embed(
                    edit_msg,
                    args[1],
                    args[2],
                    args[3],
                    args[4]
                )
        elif len(args) == 6:
            fields = util.get_embed_fields(args[4])
            await util.edit_embed(
                edit_msg,
                args[1],
                args[2],
                args[3],
                args[4],
                fields=fields
            )
        else:
            await util.edit_embed(
                self.response_msg,
                "Invalid arguments!",
                ""
            )
            return

        await self.response_msg.delete()
        await self.invoke_msg.delete()

    async def cmd_archive(self):
        """
        Implement pg!archive, for admins to archive messages
        """
        self.check_args(3)
        origin = int(util.filter_id(self.args[0]))
        quantity = int(self.args[1])
        destination = int(util.filter_id(self.args[2]))

        origin_channel = None
        destination_channel = None

        for channel in common.bot.get_all_channels():
            if channel.id == origin:
                origin_channel = channel
            if channel.id == destination:
                destination_channel = channel

        if not origin_channel:
            await util.edit_embed(
                self.response_msg,
                "Cannot execute command:",
                "Invalid origin channel!"
            )
            return
        elif not destination_channel:
            await util.edit_embed(
                self.response_msg,
                "Cannot execute command:",
                "Invalid destination channel!"
            )
            return

        messages = await origin_channel.history(limit=quantity).flatten()
        messages.reverse()
        message_list = await util.format_archive_messages(messages)

        archive_str = f"+{'=' * 40}+\n" + f"+{'=' * 40}+\n".join(message_list) + f"+{'=' * 40}+\n"
        archive_list = util.split_long_message(archive_str)

        for message in archive_list:
            await destination_channel.send(message)

        await util.edit_embed(
            self.response_msg,
            f"Successfully archived {len(messages)} message(s)!",
            ""
        )
