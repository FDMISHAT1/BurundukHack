"""
Shell preprocessor — pipes, redirects, chaining, globbing, variable expansion, tilde, command substitution.
Called from game loop INSTEAD of direct dispatch.
"""
import re
import shlex
import fnmatch
import random
from ui.console import console

# Will be set by game.py after imports
_game = None
_dispatch_fn = None
_last_exit_code = 0


def init_shell(game, dispatch_fn):
    global _game, _dispatch_fn
    _game = game
    _dispatch_fn = dispatch_fn


def get_exit_code() -> int:
    return _last_exit_code


def process_line(raw: str):
    """Main entry point. Process a full input line with all shell features."""
    global _last_exit_code

    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return

    # Expand history: !!, !$, !N, ^old^new
    from ui.prompt import expand_history
    raw = expand_history(raw)

    # Handle shell constructs: for, while, if
    # These may be followed by more commands: for...done; echo
    remainder = _handle_shell_construct(raw)
    if remainder is not None:
        # Shell construct was handled; process any remainder
        if remainder.strip():
            process_line(remainder)
        return

    # Split by chaining operators ; && ||
    segments = _split_chain(raw)

    for operator, command in segments:
        # Check chaining logic
        if operator == "&&" and _last_exit_code != 0:
            continue
        if operator == "||" and _last_exit_code == 0:
            continue

        # Process pipe chain
        _last_exit_code = _process_pipe_chain(command.strip())


def _execute_body(body: str):
    """Execute a shell body that may contain ; && || chaining."""
    global _last_exit_code
    segments = _split_chain(body)
    for operator, command in segments:
        if operator == "&&" and _last_exit_code != 0:
            continue
        if operator == "||" and _last_exit_code == 0:
            continue
        _last_exit_code = _process_pipe_chain(command.strip())


def _handle_shell_construct(raw: str):
    """Handle for/while/if constructs. Returns None if not handled,
    or a string with the remaining command after the construct."""
    global _last_exit_code

    # for VAR in LIST; do BODY; done [; more commands]
    m = re.match(
        r'for\s+(\w+)\s+in\s+(.+?)\s*;\s*do\s+(.+)\s*;\s*done\s*(.*)', raw)
    if m:
        var_name = m.group(1)
        list_expr = m.group(2)
        body = m.group(3)

        # Expand the list (could be $(cmd), glob, or literal)
        expanded_list = _expand_arithmetic(list_expr)
        expanded_list = _expand_variables(expanded_list)
        expanded_list = _expand_command_substitution(expanded_list)
        try:
            items = shlex.split(expanded_list)
        except ValueError:
            items = expanded_list.split()

        # Expand braces and globs in items
        final_items = []
        for item in items:
            for braced in _expand_brace(item):
                final_items.extend(_expand_glob(braced))

        for item in final_items:
            # Set loop variable
            if _game:
                _game.shell_vars[var_name] = item
                _game.current_host.env[var_name] = item
            # Execute body (may contain ; && ||)
            _execute_body(body)

        # Clean up loop variable
        if _game:
            _game.shell_vars.pop(var_name, None)
            _game.current_host.env.pop(var_name, None)
        remainder = m.group(4).lstrip(";").strip() if m.lastindex >= 4 else ""
        return remainder

    # while CONDITION; do BODY; done [; more]
    m = re.match(
        r'while\s+(.+?)\s*;\s*do\s+(.+)\s*;\s*done\s*(.*)', raw)
    if m:
        condition = m.group(1)
        body = m.group(2)
        max_iter = 100  # prevent infinite loops
        for _ in range(max_iter):
            _last_exit_code = _process_pipe_chain(condition.strip())
            if _last_exit_code != 0:
                break
            _execute_body(body)
        remainder = m.group(3).lstrip(";").strip() if m.lastindex >= 3 else ""
        return remainder

    # if CONDITION; then BODY; else ELSE_BODY; fi [; more]
    m = re.match(
        r'if\s+(.+?)\s*;\s*then\s+(.+)\s*;\s*else\s+(.+)\s*;\s*fi\s*(.*)', raw)
    if m:
        condition = m.group(1)
        then_body = m.group(2)
        else_body = m.group(3)
        _last_exit_code = _process_pipe_chain(condition.strip())
        if _last_exit_code == 0:
            _execute_body(then_body)
        else:
            _execute_body(else_body)
        remainder = m.group(4).lstrip(";").strip() if m.lastindex >= 4 else ""
        return remainder

    # if CONDITION; then BODY; fi [; more]
    m = re.match(
        r'if\s+(.+?)\s*;\s*then\s+(.+)\s*;\s*fi\s*(.*)', raw)
    if m:
        condition = m.group(1)
        then_body = m.group(2)
        _last_exit_code = _process_pipe_chain(condition.strip())
        if _last_exit_code == 0:
            _execute_body(then_body)
        remainder = m.group(3).lstrip(";").strip() if m.lastindex >= 3 else ""
        return remainder

    return None


def _split_chain(raw: str) -> list[tuple[str, str]]:
    """
    Split 'cmd1 ; cmd2 && cmd3 || cmd4' into
    [("", "cmd1"), (";", "cmd2"), ("&&", "cmd3"), ("||", "cmd4")]
    Respects quotes.
    """
    segments = []
    current = []
    i = 0
    in_single = False
    in_double = False
    pending_op = ""

    while i < len(raw):
        c = raw[i]

        if c == "'" and not in_double:
            in_single = not in_single
            current.append(c)
        elif c == '"' and not in_single:
            in_double = not in_double
            current.append(c)
        elif not in_single and not in_double:
            if c == ";" and (i == 0 or raw[i-1] != "\\"):
                segments.append((pending_op, "".join(current)))
                current = []
                pending_op = ";"
            elif c == "&" and i + 1 < len(raw) and raw[i + 1] == "&":
                segments.append((pending_op, "".join(current)))
                current = []
                pending_op = "&&"
                i += 1
            elif c == "&" and (i + 1 >= len(raw) or raw[i + 1] != "&"):
                # Background & — strip it, just run normally (simulation)
                pass
            elif c == "|" and i + 1 < len(raw) and raw[i + 1] == "|":
                segments.append((pending_op, "".join(current)))
                current = []
                pending_op = "||"
                i += 1
            else:
                current.append(c)
        else:
            current.append(c)
        i += 1

    rest = "".join(current).strip()
    if rest:
        segments.append((pending_op, rest))

    return segments


def _process_pipe_chain(command: str) -> int:
    """
    Process 'cmd1 | cmd2 | cmd3'. Returns exit code of last command.
    """
    parts = _split_pipes(command)

    if len(parts) == 1:
        # No pipes — handle redirects and execute
        return _execute_with_redirects(parts[0].strip())

    # Pipe chain: capture output of each, feed as stdin to next
    stdin_data = None
    exit_code = 0

    for i, part in enumerate(parts):
        part = part.strip()
        is_last = (i == len(parts) - 1)

        if is_last:
            # Last command in pipe — output to terminal, but with stdin
            exit_code = _execute_with_redirects(part, stdin=stdin_data)
        else:
            # Intermediate — capture output, but still handle redirects (e.g. 2>&1)
            console.start_capture()
            exit_code = _execute_with_redirects(part, stdin=stdin_data)
            stdin_data = console.stop_capture()

    return exit_code


def _split_pipes(command: str) -> list[str]:
    """Split by | but not || (which is chaining, already handled).
    Respects quotes, backticks, and $() to avoid splitting inside them."""
    parts = []
    current = []
    i = 0
    in_single = False
    in_double = False
    in_backtick = False
    paren_depth = 0  # for $()

    while i < len(command):
        c = command[i]
        if c == "`" and not in_single:
            in_backtick = not in_backtick
            current.append(c)
        elif c == "'" and not in_double and not in_backtick:
            in_single = not in_single
            current.append(c)
        elif c == '"' and not in_single and not in_backtick:
            in_double = not in_double
            current.append(c)
        elif c == "$" and i + 1 < len(command) and command[i + 1] == "(" and not in_single and not in_backtick:
            paren_depth += 1
            current.append(c)
        elif c == "(" and paren_depth > 0:
            paren_depth += 1
            current.append(c)
        elif c == ")" and paren_depth > 0:
            paren_depth -= 1
            current.append(c)
        elif c == "|" and not in_single and not in_double and not in_backtick and paren_depth == 0:
            # Make sure it's not ||
            if i + 1 < len(command) and command[i + 1] == "|":
                current.append(c)  # part of ||, keep it
            else:
                parts.append("".join(current))
                current = []
                i += 1
                continue
        else:
            current.append(c)
        i += 1

    rest = "".join(current)
    if rest.strip():
        parts.append(rest)
    return parts


def _is_outside_quotes(text: str, pos: int) -> bool:
    """Check if position pos in text is outside single and double quotes."""
    in_sq = False
    in_dq = False
    for i in range(pos):
        if text[i] == "'" and not in_dq:
            in_sq = not in_sq
        elif text[i] == '"' and not in_sq:
            in_dq = not in_dq
    return not in_sq and not in_dq


def _execute_with_redirects(command: str, stdin: str | None = None) -> int:
    """Parse redirects > >> 2> < from command, execute, handle output."""
    redirect_out = None       # (filepath, mode) where mode is "w" or "a"

    # Parse redirects from the end of the command
    # Only match redirects outside of quotes
    cmd = command

    # 2>&1 — merge stderr into stdout (noop for simulation)
    for m in re.finditer(r'2>&1', cmd):
        if _is_outside_quotes(cmd, m.start()):
            cmd = cmd[:m.start()] + cmd[m.end():]
            cmd = cmd.strip()
            break

    # &>/dev/null or &> file
    for m in re.finditer(r'&>\s*(\S+)', cmd):
        if _is_outside_quotes(cmd, m.start()):
            target = m.group(1)
            redirect_out = ("/dev/null", "w") if target == "/dev/null" else (_expand_path(target), "w")
            cmd = cmd[:m.start()].strip()
            break

    # 2>/dev/null
    for m in re.finditer(r'2>\s*(/dev/null|\S+)', cmd):
        if _is_outside_quotes(cmd, m.start()):
            cmd = cmd[:m.start()].strip()
            break

    # >> append
    if not redirect_out:
        for m in re.finditer(r'>>\s*(\S+)', cmd):
            if _is_outside_quotes(cmd, m.start()):
                redirect_out = (_expand_path(m.group(1)), "a")
                cmd = cmd[:m.start()].strip()
                break

    # > overwrite (but not >>)
    if not redirect_out:
        for m in re.finditer(r'(?<!>)>\s*(\S+)', cmd):
            if _is_outside_quotes(cmd, m.start()):
                redirect_out = (_expand_path(m.group(1)), "w")
                cmd = cmd[:m.start()].strip()
                break

    # < input redirect
    m = re.search(r'<\s*(\S+)', cmd)
    if m and _is_outside_quotes(cmd, m.start()):
        filepath = _expand_path(m.group(1))
        host = _game.current_host if _game else None
        if host and filepath in host.files:
            stdin = host.files[filepath]
        cmd = cmd[:m.start()].strip()

    # Execute
    if redirect_out and redirect_out[0] == "/dev/null":
        # Suppress all output
        console.start_capture()
        exit_code = _execute_single(cmd.strip(), stdin=stdin)
        console.stop_capture()  # discard
        return exit_code

    if redirect_out:
        # Capture output and write to file
        console.start_capture()
        exit_code = _execute_single(cmd.strip(), stdin=stdin)
        output = console.stop_capture()

        host = _game.current_host if _game else None
        if host:
            filepath = redirect_out[0]
            mode = redirect_out[1]
            if mode == "a" and filepath in host.files:
                host.files[filepath] += output
            else:
                host.files[filepath] = output
            host.user_files[filepath] = host.files[filepath]
        return exit_code

    return _execute_single(cmd.strip(), stdin=stdin)


def _execute_single(command: str, stdin: str | None = None) -> int:
    """Expand aliases, variables, globs, tilde, then dispatch."""
    if not command:
        return 0

    # Handle variable assignments: VAR=value [VAR2=val2 ...] [CMD ...]
    if _game and _game.current_host:
        while True:
            m = re.match(r'^([A-Za-z_]\w*)=(\S*)\s*(.*)', command)
            if not m:
                break
            var_name = m.group(1)
            raw_val = m.group(2)
            rest = m.group(3)
            # Unquote value
            try:
                val_parts = shlex.split(raw_val) if raw_val else [""]
                value = val_parts[0] if val_parts else ""
            except ValueError:
                value = raw_val
            _game.shell_vars[var_name] = value
            _game.current_host.env[var_name] = value
            command = rest.strip()
            if not command:
                return 0  # bare assignment(s), no command after
        # If we assigned and there's still a command, continue to execute it

    # Expand aliases (first word only)
    if _game and _game.aliases:
        parts = command.split(None, 1)
        if parts and parts[0] in _game.aliases:
            alias_val = _game.aliases[parts[0]]
            command = alias_val + (" " + parts[1] if len(parts) > 1 else "")

    # Expand arithmetic $(( )) before other expansions
    command = _expand_arithmetic(command)

    # Expand variables $VAR ${VAR}
    command = _expand_variables(command)

    # Handle command substitution $(cmd)
    command = _expand_command_substitution(command)

    # Tokenize — track which tokens were quoted (to skip glob on those)
    # Protect glob chars inside quotes by replacing with placeholders
    _GLOB_PLACEHOLDER = {
        "*": "\x10", "?": "\x11", "[": "\x12", "]": "\x13"
    }
    protected = command
    in_sq = False
    in_dq = False
    chars = []
    for c in command:
        if c == "'" and not in_dq:
            in_sq = not in_sq
            chars.append(c)
        elif c == '"' and not in_sq:
            in_dq = not in_dq
            chars.append(c)
        elif (in_sq or in_dq) and c in _GLOB_PLACEHOLDER:
            chars.append(_GLOB_PLACEHOLDER[c])
        else:
            chars.append(c)
    protected = "".join(chars)

    try:
        tokens = shlex.split(protected)
    except ValueError:
        tokens = protected.split()

    if not tokens:
        return 0

    # Comment check
    if tokens[0].startswith("#"):
        return 0

    # Expand tilde in all tokens
    tokens = [_expand_tilde(t) for t in tokens]

    # Expand braces and globs in unquoted tokens
    _GLOB_RESTORE = {v: k for k, v in _GLOB_PLACEHOLDER.items()}
    expanded = [tokens[0]]
    for t in tokens[1:]:
        # If token has placeholder chars, it was quoted — restore and skip expansion
        if any(c in t for c in _GLOB_PLACEHOLDER.values()):
            restored = t
            for ph, orig in _GLOB_RESTORE.items():
                restored = restored.replace(ph, orig)
            expanded.append(restored)
        else:
            # Brace expansion first, then glob each result
            braced = _expand_brace(t)
            for bt in braced:
                globbed = _expand_glob(bt)
                expanded.extend(globbed)
    tokens = expanded

    # Dispatch with stdin — pass tokens directly to avoid re-parsing
    if _dispatch_fn:
        try:
            return _dispatch_fn(_game, tokens, stdin=stdin)
        except SystemExit:
            return 0
        except Exception:
            return 1
    return 127


def _expand_variables(text: str) -> str:
    """Expand $VAR and ${VAR} from host.env.  Single-quoted segments are protected."""
    if "$" not in text:
        return text

    env = {}
    if _game and _game.current_host:
        env = _game.current_host.env

    # Special variables
    env["?"] = str(_last_exit_code)
    env["RANDOM"] = str(random.randint(0, 32767))
    env["0"] = "bash"

    # Split text into segments: single-quoted (no expansion) vs the rest
    # Pattern matches 'anything' or non-quote text
    segments = re.split(r"('(?:[^'\\]|\\.)*')", text)
    result = []
    for seg in segments:
        if seg.startswith("'") and seg.endswith("'"):
            # Single-quoted — no expansion
            result.append(seg)
            continue

        # Protect escaped \$ by replacing with placeholder
        seg = seg.replace("\\$", "\x02")

        # ${VAR} first
        def replace_braced(m):
            name = m.group(1)
            return env.get(name, "")

        seg = re.sub(r'\$\{(\w+)\}', replace_braced, seg)

        # $VAR (longest match, word chars)
        def replace_dollar(m):
            name = m.group(1)
            return env.get(name, "")

        seg = re.sub(r'\$(\w+)', replace_dollar, seg)

        # Special variables: $?, $$, $!, $#
        seg = seg.replace("$?", str(_last_exit_code))
        seg = seg.replace("$$", str(random.randint(1000, 9999)))
        seg = seg.replace("$!", str(random.randint(1000, 9999)))
        seg = seg.replace("$#", "0")

        # Restore escaped $
        seg = seg.replace("\x02", "$")

        result.append(seg)

    return "".join(result)


def _expand_arithmetic(text: str) -> str:
    """Expand $((expr)) — simple integer arithmetic."""
    if "$((" not in text:
        return text

    def replace_arith(m):
        expr = m.group(1)
        # Allow: digits, operators, spaces, parens, variable names
        # Replace variable references in the expression
        env = {}
        if _game and _game.current_host:
            env = _game.current_host.env
        if _game:
            env.update(_game.shell_vars)
        # Replace bare variable names with their values
        import re as _re
        def sub_var(vm):
            name = vm.group(1)
            return env.get(name, "0")
        expr = _re.sub(r'\b([A-Za-z_]\w*)\b', sub_var, expr)
        # Sanitize: only allow digits, operators, spaces, parens
        sanitized = re.sub(r'[^0-9+\-*/%() \t]', '', expr)
        try:
            result = int(eval(sanitized))  # safe: only digits and operators
            return str(result)
        except Exception:
            return "0"

    text = re.sub(r'\$\(\((.+?)\)\)', replace_arith, text)
    return text


def _expand_command_substitution(text: str) -> str:
    """Expand $(cmd) and `cmd` by executing cmd and capturing output."""
    # First handle backticks `cmd`
    if "`" in text:
        def replace_backtick(m):
            inner_cmd = m.group(1)
            console.start_capture()
            _process_pipe_chain(inner_cmd)
            output = console.stop_capture().strip()
            return output
        text = re.sub(r'`([^`]+)`', replace_backtick, text)

    if "$(" not in text:
        return text

    # Handle nested parens: find matching closing paren
    result = []
    i = 0
    while i < len(text):
        if text[i:i+2] == "$(" and (i < 2 or text[i-1:i+1] != "(("):
            # Find matching )
            depth = 1
            j = i + 2
            while j < len(text) and depth > 0:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                j += 1
            inner_cmd = text[i+2:j-1]
            # Execute inner command with full pipe support
            console.start_capture()
            _process_pipe_chain(inner_cmd)
            output = console.stop_capture().strip()
            result.append(output)
            i = j
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def _expand_tilde(token: str) -> str:
    """Expand ~ to $HOME."""
    if not token.startswith("~"):
        return token

    if _game and _game.current_host:
        home = _game.current_host.env.get("HOME", "/root")
        if token == "~":
            return home
        if token.startswith("~/"):
            return home + token[1:]
        # ~user
        m = re.match(r'^~(\w+)(.*)', token)
        if m:
            return f"/home/{m.group(1)}{m.group(2)}"
    return token


def _expand_brace(token: str) -> list[str]:
    """Expand brace expressions: {1..5}, {a..z}, {a,b,c}, prefix{x,y}suffix."""
    if "{" not in token or "}" not in token:
        return [token]

    # Find the first { and matching }
    start = token.index("{")
    depth = 0
    end = -1
    for i in range(start, len(token)):
        if token[i] == "{":
            depth += 1
        elif token[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return [token]

    prefix = token[:start]
    suffix = token[end + 1:]
    inner = token[start + 1:end]

    # Range: {1..5} or {a..e} or {1..10..2}
    range_m = re.match(r'^(-?\d+)\.\.(-?\d+)(?:\.\.(-?\d+))?$', inner)
    if range_m:
        a, b = int(range_m.group(1)), int(range_m.group(2))
        step = int(range_m.group(3)) if range_m.group(3) else (1 if a <= b else -1)
        if step == 0:
            step = 1
        if a <= b:
            items = [str(i) for i in range(a, b + 1, abs(step))]
        else:
            items = [str(i) for i in range(a, b - 1, -abs(step))]
        result = []
        for item in items:
            result.extend(_expand_brace(f"{prefix}{item}{suffix}"))
        return result

    # Char range: {a..z}
    char_m = re.match(r'^([a-zA-Z])\.\.([a-zA-Z])$', inner)
    if char_m:
        a, b = ord(char_m.group(1)), ord(char_m.group(2))
        step = 1 if a <= b else -1
        items = [chr(i) for i in range(a, b + step, step)]
        result = []
        for item in items:
            result.extend(_expand_brace(f"{prefix}{item}{suffix}"))
        return result

    # Comma-separated: {a,b,c} — only if no spaces around commas (bash behavior)
    if "," in inner and " " not in inner:
        items = inner.split(",")
        result = []
        for item in items:
            result.extend(_expand_brace(f"{prefix}{item}{suffix}"))
        return result

    return [token]


def _expand_glob(token: str) -> list[str]:
    """Expand wildcards * ? [abc] against current host's filesystem."""
    if not any(c in token for c in "*?["):
        return [token]

    if not _game or not _game.current_host:
        return [token]

    host = _game.current_host

    # Resolve relative to cwd
    if not token.startswith("/"):
        from commands.filesystem_cmds import _resolve_path
        pattern = _resolve_path(host.cwd, token)
    else:
        pattern = token

    matches = [f for f in host.files if fnmatch.fnmatch(f, pattern)]
    matches.sort()

    if not matches:
        return [token]  # No matches — return pattern as-is (bash default)
    return matches


def _expand_path(token: str) -> str:
    """Expand tilde and resolve relative path."""
    token = _expand_tilde(token)
    if not token.startswith("/") and _game and _game.current_host:
        from commands.filesystem_cmds import _resolve_path
        token = _resolve_path(_game.current_host.cwd, token)
    return token


def _quote_if_needed(token: str) -> str:
    """Re-quote a token if it contains shell-special chars."""
    if token.startswith('"') or token.startswith("'"):
        return token
    if any(c in token for c in ' |><;&$'):
        # Use single quotes to prevent any further expansion
        escaped = token.replace("'", "'\"'\"'")
        return f"'{escaped}'"
    return token
