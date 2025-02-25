from modules.command_sys import command, Command
from modules.game_channel import GameChannel, InputMode
from modules.game import Game
from io import BytesIO
from math import floor
from xyzzy import Xyzzy

import os
import re
import typing
import asyncio
import random
import modules.quetzal_parser as qzl


class Main:
    def __init__(self, xyzzy: Xyzzy):
        self.xyzzy = xyzzy

    @command(usage="[ command ]", has_site_help=False)
    async def help(self, ctx):
        """Show help for commands."""
        if not ctx.args:
            return await ctx.send(
                "```inform\n"
                "Detailed help can be found at the link below.\n"
                'For quick information on a command, type "@{0.name}#{0.discriminator} help (command)"\n'
                "```\n"
                "https://www.orangestar.dev/xyzzy/".format(self.xyzzy.user)
            )

        cmd = self.xyzzy.commands.get_command(ctx.args[0].lower())

        if cmd and not cmd.hidden:
            msg = '```inform7\n"{}{}{}{}"\n```'.format(
                self.xyzzy.user.mention,
                cmd.name,
                " " + cmd.usage + " " if cmd.usage else "",
                cmd.description,
            )

            if cmd.has_site_help:
                msg += (
                    "\nMore information: https://www.orangestar.dev/xyzzy/#{}".format(
                        cmd.name
                    )
                )

            return await ctx.send(msg)
        else:
            return await ctx.send(
                '```diff\n-No information found on "{}".\n```'.format(
                    ctx.args[0].lower()
                )
            )

    @command(has_site_help=False)
    async def ping(self, ctx):
        msg = await ctx.send("Pong!")

        await msg.edit(
            content="Pong! `{}ms`".format(
                floor(
                    msg.created_at.timestamp() * 1000
                    - ctx.msg.created_at.timestamp() * 1000
                )
            )
        )

    @command(has_site_help=False)
    async def about(self, ctx):
        """Sends information about xyzzy."""
        await ctx.send(
            "Information about xyzzy can be found here: https://www.orangestar.dev/xyzzy/"
        )

    @command(aliases=["join"], has_site_help=False)
    async def invite(self, ctx):
        """Gives the bot"s invite link."""
        await ctx.send(
            "This bot can be invited through the following URL: <https://www.orangestar.dev/xyzzy/invite>"
        )

    @command(has_site_help=False)
    async def list(self, ctx):
        """Sends you a direct message containing all games in xyzzy's library."""
        msg = """```md
# Here are all of the games I have available: #
{}
```
Alternatively, an up-to-date list can be found here: https://www.orangestar.dev/xyzzy/list""".format(
            "\n".join(sorted(self.xyzzy.games))
        )

        if ctx.args and ctx.args[0] == "here":
            await ctx.send(msg)
        else:
            try:
                await ctx.send(msg, dest="author")
            except:
                await ctx.send(
                    "I cannot PM you, as you seem to have private messages disabled. However, an up-to-date list is available at: https://www.orangestar.dev/xyzzy/list"
                )

    @command(has_site_help=False, hidden=True)
    async def backticks(self, ctx):
        await ctx.send(
            "Unfortunately the backtick rule is no longer able to be used, due to using a mention prefix now."
        )

    @command(has_site_help=False, hidden=True)
    async def unprefixed(self, ctx):
        await ctx.send(
            "Unfortunately the unprefixed option is no longner possible due to restrictions from Discord on getting message content."
        )

    @command(usage="[ game ]")
    async def play(self, ctx):
        """
        Tells xyzzy to start playing the [game] in the current channel.
        If no game is found with that name, xyzzy will show you all games with the [game] in their name.
        If only one game is found with that text in it's name, it will start that game.
        If you run the command with a save file attached, xyzzy will try to load a game from it.
        """
        # Don't do DMs kids.
        if ctx.is_dm():
            return await ctx.send(
                "```accesslog\nSorry, but games cannot be played in DMs. Please try again in a server.```"
            )

        if ctx.msg.channel.id in self.xyzzy.channels:
            return await ctx.send(
                '```accesslog\nSorry, but #{} is currently playing "{}". Please try again after the game has finished.\n```'.format(
                    ctx.msg.channel.name,
                    self.xyzzy.channels[ctx.msg.channel.id].game.name,
                )
            )

        if not ctx.msg.attachments:
            if not ctx.args:
                return await ctx.send("```diff\n-Please provide a game to play.\n```")

            print("Searching for " + ctx.raw)

            games = {
                x: y
                for x, y in self.xyzzy.games.items()
                if ctx.raw.lower() in x.lower()
                or [z for z in y.aliases if ctx.raw.lower() in z.lower()]
            }
            perfect_match = None

            if games:
                perfect_match = {
                    x: y
                    for x, y in games.items()
                    if ctx.raw.lower() == x.lower()
                    or [z for z in y.aliases if ctx.raw.lower() == z.lower()]
                }

            if not games:
                return await ctx.send(
                    '```diff\n-I couldn\'t find any games matching "{}"\n```'.format(
                        ctx.raw
                    )
                )
            elif len(games) > 1 and not perfect_match:
                return await ctx.send(
                    "```accesslog\n"
                    'I couldn\'t find any games with that name, but I found "{}" in {} other games. Did you mean one of these?\n'
                    '"{}"\n'
                    "```".format(ctx.raw, len(games), '"\n"'.join(sorted(games)))
                )

            if perfect_match:
                game = list(perfect_match.items())[0][1]
            else:
                game = list(games.items())[0][1]
        else:
            # Attempt to load a game from a possible save file.
            attach = ctx.msg.attachments[0]

            if attach.width or attach.height:
                return await ctx.send("```diff\n-Images are not save files.\n```")

            async with ctx.typing():
                async with self.xyzzy.session.get(attach.url) as r:
                    res = await r.read()

                try:
                    qzl_headers = qzl.parse_quetzal(BytesIO(res))
                except Exception as e:
                    if str(e) == "Invalid file format.":
                        return await ctx.send("```diff\n-Invalid file format.\n```")
                    else:
                        return await ctx.send("```diff\n-{}\n```".format(str(e)))

                for name, stuff in self.xyzzy.games.items():
                    comp_res = qzl.compare_quetzal(qzl_headers, stuff.path)

                    if comp_res:
                        game = stuff
                        break

                if not comp_res:
                    return await ctx.send(
                        "```diff\n-No games matching your save file could be found.\n```"
                    )

                if not os.path.exists("./saves/{}".format(ctx.msg.channel.id)):
                    os.makedirs("./saves/{}".format(ctx.msg.channel.id))

                with open(
                    "./saves/{}/__UPLOADED__.qzl".format(ctx.msg.channel.id), "wb"
                ) as save:
                    save.write(res)

        if str(ctx.msg.guild.id) in self.xyzzy.server_settings:
            if (
                game.name
                in self.xyzzy.server_settings[str(ctx.msg.guild.id)]["blocked_games"]
            ):
                return await ctx.send(
                    '```diff\n- "{}" has been blocked on this server.\n```'.format(
                        game.name
                    )
                )

        print(
            "Now loading {} for #{} (Server: {})".format(
                game.name, ctx.msg.channel.name, ctx.msg.guild.name
            )
        )

        chan = GameChannel(ctx.msg, game)
        self.xyzzy.channels[ctx.msg.channel.id] = chan

        if ctx.msg.attachments:
            chan.save = "./saves/{}/__UPLOADED__.qzl".format(ctx.msg.channel.id)

        await ctx.send(
            '```py\nLoaded "{}"{}\n```'.format(
                game.name, " by " + game.author if game.author else ""
            )
        )
        await chan.init_process()
        await self.xyzzy.update_game()
        await chan.game_loop()
        await self.xyzzy.update_game()

        if ctx.msg.channel.id in self.xyzzy.channels:
            del self.xyzzy.channels[ctx.msg.channel.id]

    @command(usage="[ filename ]")
    async def debugload(self, ctx):
        """
        Tells xyzzy to load a [filename] from the test folder in the current channel.
        The game will not count towards any statistics.
        """
        # Don't do DMs kids.
        if ctx.is_dm():
            return await ctx.send(
                "```accesslog\nSorry, but games cannot be played in DMs. Please try again in a server.```"
            )

        if ctx.msg.channel.id in self.xyzzy.channels:
            return await ctx.send(
                '```accesslog\nSorry, but #{} is currently playing "{}". Please try again after the game has finished.\n```'.format(
                    ctx.msg.channel.name,
                    self.xyzzy.channels[ctx.msg.channel.id].game.name,
                )
            )

        if not ctx.args:
            return await ctx.send("```diff\n-Please provide a game to play.\n```")

        file_dir = "./tests/" + ctx.raw

        if not os.path.isfile(file_dir):
            return await ctx.send("```diff\n-File not found.\n```")

        print(
            "Now loading test file {} for #{} (Server: {})".format(
                ctx.raw, ctx.msg.channel.name, ctx.msg.guild.name
            )
        )

        chan = GameChannel(ctx.msg, Game(ctx.raw, {"path": file_dir, "debug": True}))
        self.xyzzy.channels[ctx.msg.channel.id] = chan

        await ctx.send('```py\nLoaded "{}"\n```'.format(ctx.raw))
        await chan.init_process()
        await chan.game_loop()

        if ctx.msg.channel.id in self.xyzzy.channels:
            del self.xyzzy.channels[ctx.msg.channel.id]

    @command()
    async def output(self, ctx):
        """
        Toggles whether the text being sent to this channel from a currently playing game also should be printed to the terminal.
        This is functionally useless in most cases.
        """
        if ctx.msg.channel.id not in self.xyzzy.channels:
            return await ctx.send(
                "```diff\n-Nothing is being played in this channel.\n```"
            )

        chan = self.xyzzy.channels[ctx.msg.channel.id]

        if chan.output:
            chan.output = False
            await ctx.send('```basic\n"Terminal Output" is now OFF.\n```')
        else:
            chan.output = True
            await ctx.send('```basic\n"Terminal Output" is now ON\n```')

    @command(usage="[ indent level ]")
    async def indent(self, ctx):
        """
        Will make xyzzy scrap the first nth characters for each line in his output.
        If you're noticing random spaces after each line break, use this command.
        [Indent level] must be an integer between 0 and the total console width. (Usually 80.)
        """
        if ctx.msg.channel.id not in self.xyzzy.channels:
            return await ctx.send(
                "```diff\n-Nothing is being played in this channel.\n```"
            )

        if not ctx.args:
            return await ctx.send("```diff\n-You need to supply a number.\n```")

        chan = self.xyzzy.channels[ctx.msg.channel.id]

        try:
            chan.indent = int(ctx.args[0])
            await ctx.send(
                '```basic\n"Indent Level" is now {}.\n```'.format(chan.indent)
            )
        except ValueError:
            await ctx.send("```diff\n!ERROR: Valid number not supplied.\n```")

    @command(aliases=["mortim"])
    async def forcequit(self, ctx):
        """
        After confirmation, terminates the process running the xyzzy game you are playing.
        [It is recommended to try to exit the game using an in-game method before using this command.] >quit usually works.
        This command has an alias in '@xyzzy mortim'
        """
        if ctx.msg.channel.id not in self.xyzzy.channels:
            return await ctx.send(
                "```diff\n-Nothing is being played in this channel.\n```"
            )

        channel = self.xyzzy.channels[ctx.msg.channel.id]

        if (
            not ctx.has_permission("manage_guild", "author")
            and str(ctx.msg.author.id) not in self.xyzzy.owner_ids
            and ctx.msg.author != channel.owner
            and (
                channel.mode == InputMode.DEMOCRACY or channel.mode == InputMode.DRIVER
            )
        ):
            return await ctx.send(
                '```diff\n-Only people who can manage the server, or the "owner" of the current game may force quit.\n```'
            )

        await ctx.send(
            "```diff\n"
            "Are you sure you want to quit?\n"
            "-Say Y or Yes to close the program.\n"
            "!NOTE: You will lose all unsaved progress!\n"
            "+Send any other message to continue playing.\n"
            "```"
        )

        try:
            check = (
                lambda x: x.channel == ctx.msg.channel and x.author == ctx.msg.author
            )
            msg = await self.xyzzy.wait_for("message", check=check, timeout=30)

            if re.match(r"^`?({})?y(es)?`?$", msg.content.lower()):
                chan = self.xyzzy.channels[ctx.msg.channel.id]

                await chan.force_quit()
                chan.cleanup()

                if ctx.msg.channel.id in self.xyzzy.channels:
                    del self.xyzzy.channels[ctx.msg.channel.id]
            else:
                await ctx.send("```diff\n+Continuing game.\n```")
        except asyncio.TimeoutError:
            await ctx.send("```diff\n+Message timeout expired. Continuing game.\n```")
        except ProcessLookupError:
            chan = self.xyzzy.channels[ctx.msg.channel.id]
            saves = chan.check_saves()

            if saves:
                await self.channel.send(
                    "```diff\n-The game has ended.\n+Here are your saves from the game.\n```",
                    files=saves,
                )
            else:
                await ctx.send("```diff\n-The game has ended.\n```")

            chan.cleanup()

            if ctx.msg.channel.id in self.xyzzy.channels:
                del self.xyzzy.channels[ctx.msg.channel.id]

    @command(aliases=["upload"], usage="[ Save as Attachment ]")
    async def uploadsave(self, ctx):
        """Uploads a save to be played from during a game."""
        if not ctx.msg.attachments:
            return await ctx.send("Please send a save file as an attachment.")

        attach = ctx.msg.attachments[0]

        if attach.height or attach.width:
            return await ctx.send("```diff\n-Images are not save files.\n```")

        async with ctx.typing():
            async with self.xyzzy.session.get(attach.url) as r:
                res = await r.read()

            try:
                qzl_headers = qzl.parse_quetzal(BytesIO(res))
            except Exception as e:
                if str(e) == "Invalid file format.":
                    return await ctx.send("```diff\n-Invalid file format.\n```")
                else:
                    return await ctx.send("```diff\n-{}\n```".format(str(e)))

            if not os.path.exists("./saves/{}".format(ctx.msg.channel.id)):
                os.makedirs("./saves/{}".format(ctx.msg.channel.id))

            with open(
                "./saves/{}/{}.qzl".format(
                    ctx.msg.channel.id, attach.filename.rsplit(".")[0]
                ),
                "wb",
            ) as save:
                save.write(res)

        await ctx.send(
            "```diff\n"
            "+Saved file as '{}.qzl'.\n"
            "+You can load it by playing the relevant game and using the RESTORE command.\n"
            "-Note that this will get removed during the next game played if it is not loaded, or after the next reboot.\n"
            "```".format(attach.filename.split(".")[0])
        )

    @command()
    async def modes(self, ctx):
        """
        Shows a list of all the different game input modes currently supported by xyzzy.
        """
        await ctx.send(
            "```asciidoc\n"
            ".Game Input Modes.\n"
            "A list of all the different input modes available for xyzzy.\n\n"
            "* Anarchy *default*\n"
            "  Anyone can run any command with no restrictions.\n\n"
            "* Democracy\n"
            "  Commands are voted on by players. After 15 seconds, the highest voted command is run.\n"
            "  More info: http://helixpedia.wikia.com/wiki/Democracy\n\n"
            "* Driver\n"
            "  Only one person can control the game at a time, but can transfer ownership at any time.\n"
            "```"
        )

    @command(usage="[ mode ] or list")
    async def mode(self, ctx):
        """
        Changes the input mode for the currently running session to [mode].
        If "list" is specified as the mode, a list of the supported input modes will be shown (this is also aliased to '@xyzzy modes').
        [Only users who can manage the server, or the "owner" of the current game can change the mode.]
        """
        if ctx.msg.channel.id not in self.xyzzy.channels:
            return await ctx.send(
                "```diff\n-Nothing is being played in this channel.\n```"
            )

        if (
            not ctx.has_permission("manage_guild", "author")
            and str(ctx.msg.author.id) not in self.xyzzy.owner_ids
            and ctx.msg.author != self.xyzzy.channels[ctx.msg.channel.id].owner
        ):
            return await ctx.send(
                '```diff\n-Only people who can manage the server, or the "owner" of the current game can change the mode.\n```'
            )

        if not ctx.args:
            return await ctx.send("```diff\n-Please tell me a mode to switch to.\n```")

        if ctx.args[0].lower() == "list":
            return await self.modes.run(ctx)

        if ctx.args[0].lower() not in ("democracy", "anarchy", "driver"):
            return await ctx.send(
                "```diff\n"
                "Please select a valid mode.\n"
                "You can run '@xyzzy modes' to view all the currently available modes.\n"
                "```"
            )

        res = [x for x in InputMode if ctx.args[0].lower() == x.name.lower()][0]
        channel = self.xyzzy.channels[ctx.msg.channel.id]

        if res == channel.mode:
            return await ctx.send(
                '```diff\n-The current mode is already "{}".\n```'.format(
                    ctx.args[0].lower()
                )
            )

        channel.mode = res

        if res == InputMode.ANARCHY:
            await ctx.send(
                "```glsl\n"
                "#Anarchy mode is now on.\n"
                "Any player can now submit any command with no restriction.\n"
                "```"
            )
        elif res == InputMode.DEMOCRACY:
            await ctx.send(
                "```diff\n"
                "+Democracy mode is now on.\n"
                "Players will now vote on commands. After 15 seconds, the top voted command will be input.\n"
                "On ties, the command will be scrapped and no input will be sent.\n"
                "More info: http://helixpedia.wikia.com/wiki/Democracy\n"
                "```"
            )
        else:
            await ctx.send(
                "```diff\n"
                "-Driver mode is now on.\n"
                "Only {} will be able to submit commands.\n"
                "You can transfer the \"wheel\" with '@xyzzy transfer [user]'\n"
                "```".format(channel.owner)
            )

    @command(usage="[ @User Mentions#1234 ]")
    async def transfer(self, ctx):
        """
        Passes the "wheel" to another user, letting them take control of the current game.
        NOTE: this only works in driver or democracy mode.
        [This command can only be used by the "owner" of the game.]
        """
        if ctx.msg.channel.id not in self.xyzzy.channels:
            return await ctx.send(
                "```diff\n-Nothing is being played in this channel.\n```"
            )

        if self.xyzzy.channels[ctx.msg.channel.id].mode == InputMode.ANARCHY:
            return await ctx.send(
                "```diff\n-'transfer' may only be used in driver or anarchy mode.\n```"
            )

        if (
            str(ctx.msg.author.id) not in self.xyzzy.owner_ids
            and ctx.msg.author != self.xyzzy.channels[ctx.msg.channel.id].owner
        ):
            return await ctx.send(
                "```diff\n-Only the current owner of the game can use this command.\n```"
            )

        if not ctx.msg.mentions:
            return await ctx.send(
                '```diff\n-Please give me a user to pass the "wheel" to.\n```'
            )

        self.xyzzy.channels[ctx.msg.channel.id].owner = ctx.msg.mentions[0]

        await ctx.send(
            '```diff\n+Transferred the "wheel" to {}.\n```'.format(ctx.msg.mentions[0])
        )

    @command(has_site_help=False)
    async def jump(self, ctx):
        """Wheeeeeeeeee!!!!!"""
        await ctx.send(
            random.choice(
                [
                    "Wheeeeeeeeee!!!!!",
                    "Are you enjoying yourself?",
                    "Do you expect me to applaud?",
                    "Very good. Now you can go to the second grade.",
                    "Have you tried hopping around the dungeon, too?",
                    "You jump on the spot.",
                    "You jump on the spot, fruitlessly.",
                ]
            )
        )


def setup(xyzzy):
    return Main(xyzzy)
