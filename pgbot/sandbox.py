import asyncio
import builtins
import cmath
import itertools
import math
import random
import re
import string
import sys
import multiprocessing
import time
import traceback

import psutil
import pygame.freetype
import pygame.gfxdraw

from . import common


class Output:
    """
    Output class for posting relevent data through discord
    """
    def __init__(self):
        self.text = ""
        self.img = None
        self.exc = None
        self.duration = -1  # The script execution time


class SandboxFunctionsObject:
    """
    Wrap custom functions for use in pg!exec
    """
    public_functions = (
        "print",
    )

    def __init__(self):
        self.output = Output()

    def print(self, *values, sep=" ", end="\n"):
        self.output.text = str(self.output.text)
        self.output.text += sep.join(map(str, values)) + end


class PgExecBot(Exception):
    """
    Base class for pg!exec exceptions
    """
    pass


filtered_builtins = {}
disallowed_builtins = (
    "__debug__",
    "__doc__",
    "__import__",
    "__loader__",
    "__package__",
    "__spec__",
    "copyright",
    "credits",
    "exit",
    "type",
    "help",
    "input",
    "license",
    "print",
    "open",
    "quit",
    "compile",
    "exec",
    "eval",
    "getattr",
    "setattr",
    "delattr",
    "globals",
    "locals",
    "vars",
)

for key in dir(builtins):
    if key not in disallowed_builtins:
        filtered_builtins[key] = getattr(builtins, key)


class FilteredPygame:
    """
    pygame module in a sandbox
    """
    Surface = pygame.Surface
    Rect = pygame.Rect
    Color = pygame.Color
    PixelArray = pygame.PixelArray
    draw = pygame.draw
    gfxdraw = pygame.gfxdraw
    transform = pygame.transform
    mask = pygame.mask
    math = pygame.math
    version = pygame.version

    class freetype:
        get_error = pygame.freetype.get_error
        get_version = pygame.freetype.get_version
        get_cache_size = pygame.freetype.get_cache_size
        get_default_resolution = pygame.freetype.get_default_resolution
        set_default_resolution = pygame.freetype.set_default_resolution
        SysFont = pygame.freetype.SysFont
        get_default_font = pygame.freetype.get_default_font
        Font = pygame.freetype.Font

    class image:
        fromstring = pygame.image.fromstring
        tostring = pygame.image.tostring
        frombuffer = pygame.image.frombuffer

    class font:
        get_default_font = pygame.font.get_default_font
        get_fonts = pygame.font.get_fonts
        match_font = pygame.font.match_font
        SysFont = pygame.font.SysFont
        Font = pygame.font.Font

    class constants:
        pass


del FilteredPygame.mask.__loader__
del FilteredPygame.math.__loader__
del FilteredPygame.transform.__loader__
del FilteredPygame.draw.__loader__
del FilteredPygame.gfxdraw.__loader__
del FilteredPygame.version.__loader__

del FilteredPygame.mask.__spec__
del FilteredPygame.math.__spec__
del FilteredPygame.transform.__spec__
del FilteredPygame.draw.__spec__
del FilteredPygame.gfxdraw.__spec__
del FilteredPygame.version.__spec__

for const in pygame.constants.__all__:
    setattr(FilteredPygame.constants, const, pygame.constants.__dict__[const])
    setattr(FilteredPygame, const, pygame.constants.__dict__[const])


def pg_exec(code: str, tstamp: int, allowed_builtins: dict, q: multiprocessing.Queue):
    """
    exec wrapper used for pg!exec, runs in a seperate process. Since this
    function runs in a seperate Process, keep that in mind if you want to make
    any changes to this function (that is, do not touch this shit if you don't 
    know what you are doing)
    """
    sandbox_funcs = SandboxFunctionsObject()
    output = sandbox_funcs.output

    allowed_globals = {
        "math": math,
        "cmath": cmath,
        "random": random,
        "re": re,
        "time": time,
        "string": string,
        "itertools": itertools,
    }

    for module in allowed_globals:
        del allowed_globals[module].__loader__, allowed_globals[module].__spec__

    allowed_globals["__builtins__"] = allowed_builtins
    allowed_globals["pygame"] = FilteredPygame
    allowed_globals["output"] = output

    allowed_globals.update(allowed_builtins)

    for func_name in sandbox_funcs.public_functions:
        allowed_globals[func_name] = getattr(sandbox_funcs, func_name)

    for ill_attr in common.ILLEGAL_ATTRIBUTES:
        if ill_attr in code:
            output.exc = PgExecBot("Suspicious Pattern")
            break
    else:
        try:
            script_start = time.perf_counter()
            exec(code, allowed_globals)
            output.duration = time.perf_counter() - script_start

        except ImportError:
            output.exc = PgExecBot(
                "Oopsies! The bot's exec function doesn't support importing " +
                "external modules. Don't worry, many modules are pre-" +
                "imported for you already! Just re-run your code, without " +
                "the import statements"
            )

        except SyntaxError as e:
            offsetarrow = " " * e.offset + "^\n"
            output.exc = PgExecBot(f"SyntaxError at line {e.lineno}\n  " +
                            e.text + '\n' + offsetarrow + e.msg)

        except Exception as err:
            ename = err.__class__.__name__
            details = err.args[0]
            # Don't try to replace this, otherwise we may get wrong line numbers
            lineno = traceback.extract_tb(sys.exc_info()[-1])[-1][1]
            output.exc = PgExecBot(f"{ename} at line {lineno}: {details}")
    
    # Because output needs to go through queue, we need to sanitize it first
    # Any random data that gets put in the queue will likely crash the entire bot
    sanitized_output = Output()
    if isinstance(output.text, str):
        sanitized_output.text = output.text
    
    if isinstance(output.duration, float):
        sanitized_output.duration = output.duration

    if isinstance(output.exc, PgExecBot):
        sanitized_output.exc = output.exc
    
    if isinstance(output.img, pygame.Surface):
        # A surface is not picklable, so handle differently
        sanitized_output.img = True
        pygame.image.save(output.img, f"temp{tstamp}.png")

    q.put(sanitized_output)


async def exec_sandbox(code: str, tstamp: int, timeout=5, max_memory=2 ** 28):
    """
    Helper to run pg!exec code in a sandbox, manages the seperate process that
    runs to execute user code.
    """
    q = multiprocessing.Queue(1)
    proc = multiprocessing.Process(
        target=pg_exec, 
        args=(code, tstamp, filtered_builtins, q),
        daemon=True  # the process must die when the main process dies
    )
    proc.start()
    psproc = psutil.Process(proc.pid)

    start = time.time()
    while proc.is_alive():
        if start + timeout < time.time():
            output = Output()
            output.exc = PgExecBot(f"Hit timeout of {timeout} seconds!")
            proc.kill()
            return output
            
        if psproc.memory_info().rss > max_memory:
            output = Output()
            output.exc = PgExecBot(
                f"The bot's memory has taken up to {max_memory} bytes!"
            )
            proc.kill()
            return output
        await asyncio.sleep(0.05)  # Let the bot do other async things

    return q.get()
