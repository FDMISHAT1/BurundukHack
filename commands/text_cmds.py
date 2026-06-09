"""Text processing utilities for pipes: sort, uniq, cut, tr, sed, awk, tee, xargs, rev, seq."""
import re
import random as rnd
from commands.registry import register
from commands.linux_cmds import _get_input, _require_host, _wants_help
from ui.console import console


# -----------------------------------------------------------------------
# sort
# -----------------------------------------------------------------------
@register("sort", "cmd.sort.help", required_tool="sort")
def handle_sort(game, args):
    if _wants_help(args):
        console.print("Usage: sort [OPTION]... [FILE]...\n")
        console.print("  sort file         sort lines alphabetically")
        console.print("  sort -r           reverse order")
        console.print("  sort -n           numeric sort")
        console.print("  sort -u           unique (remove duplicates)")
        console.print("  sort -k 2         sort by field 2")
        console.print("  sort -t:          use : as delimiter")
        console.print("  sort -R           random order")
        return
    if not _require_host(game):
        return
    content = _get_input(game, args, "sort")
    if content is None:
        return

    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    # Parse combined flags like -rn, -nu, -Ruf
    _flags = "".join(a[1:] for a in args if a.startswith("-") and not a[1:].isdigit() and a not in ("-k", "-t"))
    reverse = "r" in _flags
    numeric = "n" in _flags
    unique = "u" in _flags
    rand_sort = "R" in _flags
    case_fold = "f" in _flags

    # Key field
    key_field = None
    if "-k" in args:
        idx = args.index("-k")
        if idx + 1 < len(args):
            try:
                key_field = int(args[idx + 1]) - 1
            except ValueError:
                pass

    # Delimiter
    delim = None
    if "-t" in args:
        idx = args.index("-t")
        if idx + 1 < len(args):
            delim = args[idx + 1]
    # Also support -t: as single arg
    for a in args:
        if a.startswith("-t") and len(a) > 2:
            delim = a[2:]

    def sort_key(line):
        if key_field is not None:
            parts = line.split(delim) if delim else line.split()
            if key_field < len(parts):
                val = parts[key_field]
            else:
                val = ""
        else:
            val = line
        if numeric:
            try:
                return float(re.match(r'-?[\d.]+', val).group()) if re.match(r'-?[\d.]+', val) else 0
            except (ValueError, AttributeError):
                return 0
        return val.lower() if case_fold else val

    if rand_sort:
        rnd.shuffle(lines)
    else:
        lines.sort(key=sort_key, reverse=reverse)

    if unique:
        seen = set()
        deduped = []
        for l in lines:
            if l not in seen:
                seen.add(l)
                deduped.append(l)
        lines = deduped

    console.print("\n".join(lines))


# -----------------------------------------------------------------------
# uniq
# -----------------------------------------------------------------------
@register("uniq", "cmd.uniq.help", required_tool="uniq")
def handle_uniq(game, args):
    if _wants_help(args):
        console.print("Usage: uniq [OPTION]... [INPUT [OUTPUT]]\n")
        console.print("  uniq              remove adjacent duplicates")
        console.print("  uniq -c           prefix lines with count")
        console.print("  uniq -d           only show duplicates")
        console.print("  uniq -u           only show unique lines")
        console.print("  uniq -i           case-insensitive")
        return
    if not _require_host(game):
        return
    content = _get_input(game, args, "uniq")
    if content is None:
        return

    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    count_mode = "-c" in args
    dup_only = "-d" in args
    unique_only = "-u" in args
    case_insensitive = "-i" in args

    # Group adjacent duplicates
    groups = []
    for line in lines:
        cmp = line.lower() if case_insensitive else line
        if groups and groups[-1][1] == cmp:
            groups[-1] = (groups[-1][0] + 1, cmp, line)
        else:
            groups.append((1, cmp, line))

    for count, _, orig in groups:
        if dup_only and count < 2:
            continue
        if unique_only and count > 1:
            continue
        if count_mode:
            console.print(f"{count:>7d} {orig}")
        else:
            console.print(orig)


# -----------------------------------------------------------------------
# cut
# -----------------------------------------------------------------------
@register("cut", "cmd.cut.help", required_tool="cut")
def handle_cut(game, args):
    if _wants_help(args):
        console.print("Usage: cut OPTION... [FILE]...\n")
        console.print("  cut -d: -f1       first field with : delimiter")
        console.print("  cut -d: -f1,3     fields 1 and 3")
        console.print("  cut -d: -f1-3     fields 1 to 3")
        console.print("  cut -c1-5         characters 1 to 5")
        return
    if not _require_host(game):
        return
    content = _get_input(game, args, "cut")
    if content is None:
        return

    # Parse delimiter
    delim = "\t"
    for i, a in enumerate(args):
        if a == "-d" and i + 1 < len(args):
            delim = args[i + 1]
            break
        if a.startswith("-d") and len(a) > 2:
            delim = a[2:]
            break

    # Parse fields -f or characters -c
    fields = None
    chars = None
    for i, a in enumerate(args):
        if a == "-f" and i + 1 < len(args):
            fields = _parse_range(args[i + 1])
            break
        if a.startswith("-f") and len(a) > 2:
            fields = _parse_range(a[2:])
            break
        if a == "-c" and i + 1 < len(args):
            chars = _parse_range(args[i + 1])
            break
        if a.startswith("-c") and len(a) > 2:
            chars = _parse_range(a[2:])
            break

    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    for line in lines:
        if chars:
            result = "".join(line[c] for c in chars if c < len(line))
        elif fields:
            parts = line.split(delim)
            result = delim.join(parts[f] for f in fields if f < len(parts))
        else:
            result = line
        console.print(result)


def _parse_range(spec: str) -> list[int]:
    """Parse '1,3,5-7' into [0,2,4,5,6] (0-indexed)."""
    indices = []
    for part in spec.split(","):
        if "-" in part:
            start, end = part.split("-", 1)
            s = int(start) - 1 if start else 0
            e = int(end) - 1 if end else 999
            indices.extend(range(s, e + 1))
        else:
            indices.append(int(part) - 1)
    return sorted(set(indices))


# -----------------------------------------------------------------------
# tr
# -----------------------------------------------------------------------
@register("tr", "cmd.tr.help", required_tool="tr")
def handle_tr(game, args):
    if _wants_help(args):
        console.print("Usage: tr [OPTION]... SET1 [SET2]\n")
        console.print("  tr 'a-z' 'A-Z'    translate lowercase to uppercase")
        console.print("  tr -d '\\n'        delete newlines")
        console.print("  tr -s ' '         squeeze repeated spaces")
        return
    if not _require_host(game):
        return

    # tr reads from stdin only
    content = game.stdin
    if not content:
        console.print_error("tr: missing operand (use with pipe)")
        return

    # Parse combined flags: -d, -s, -c, -cd, -cs, -ds
    _flags = "".join(a[1:] for a in args if a.startswith("-"))
    delete = "d" in _flags
    squeeze = "s" in _flags
    complement = "c" in _flags
    non_flag = [a for a in args if not a.startswith("-")]

    if delete and non_flag:
        charset = set(_expand_tr_set(non_flag[0]))
        if complement:
            result = "".join(c for c in content if c in charset)
        else:
            result = "".join(c for c in content if c not in charset)
    elif squeeze and non_flag:
        chars_to_squeeze = _expand_tr_set(non_flag[0])
        result = []
        prev = None
        for c in content:
            if c in chars_to_squeeze and c == prev:
                continue
            result.append(c)
            prev = c
        result = "".join(result)
    elif len(non_flag) >= 2:
        set1 = _expand_tr_set(non_flag[0])
        set2 = _expand_tr_set(non_flag[1])
        # Pad set2 to match set1
        if len(set2) < len(set1):
            set2 = set2 + set2[-1] * (len(set1) - len(set2))
        table = str.maketrans(set1, set2[:len(set1)])
        result = content.translate(table)
    else:
        result = content

    console.print(result, end="")


def _expand_tr_set(s: str) -> str:
    """Expand 'a-z', '[:upper:]', etc."""
    import string
    # POSIX character classes
    posix_classes = {
        "[:upper:]": string.ascii_uppercase,
        "[:lower:]": string.ascii_lowercase,
        "[:alpha:]": string.ascii_letters,
        "[:digit:]": string.digits,
        "[:alnum:]": string.ascii_letters + string.digits,
        "[:space:]": string.whitespace,
        "[:blank:]": " \t",
        "[:punct:]": string.punctuation,
        "[:print:]": string.printable.replace(string.whitespace, " "),
    }
    for cls_name, cls_chars in posix_classes.items():
        s = s.replace(cls_name, cls_chars)

    s = s.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
    s = s.replace("\\0", "\0")
    result = []
    i = 0
    while i < len(s):
        if i + 2 < len(s) and s[i + 1] == "-" and s[i] != "[":
            start, end = ord(s[i]), ord(s[i + 2])
            if start <= end:
                result.extend(chr(c) for c in range(start, end + 1))
            else:
                result.extend(chr(c) for c in range(start, end - 1, -1))
            i += 3
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


# -----------------------------------------------------------------------
# sed
# -----------------------------------------------------------------------
@register("sed", "cmd.sed.help", required_tool="sed")
def handle_sed(game, args):
    if _wants_help(args):
        console.print("Usage: sed [OPTION]... 'SCRIPT' [FILE]...\n")
        console.print("  sed 's/old/new/'     substitute first on each line")
        console.print("  sed 's/old/new/g'    substitute all")
        console.print("  sed '3d'             delete line 3")
        console.print("  sed -n '5p'          print only line 5")
        console.print("  sed '1,3s/^/#/'      comment lines 1-3")
        return
    if not _require_host(game):
        return

    # Parse args: sed [-n] [-i] [-e 'script']... 'script' [file]
    suppress = "-n" in args
    inplace = "-i" in args
    scripts = []
    file_args = []
    i = 0
    while i < len(args):
        if args[i] == "-e" and i + 1 < len(args):
            scripts.append(args[i + 1])
            i += 2
        elif args[i] in ("-n", "-i"):
            i += 1
        elif not scripts and not args[i].startswith("-"):
            # First non-flag non-script arg: could be script or file
            scripts.append(args[i])
            i += 1
        elif not args[i].startswith("-"):
            file_args.append(args[i])
            i += 1
        else:
            i += 1

    if not scripts:
        console.print_error("sed: missing script")
        return

    # Get content
    if file_args:
        from commands.filesystem_cmds import _resolve_path
        filepath = file_args[0]
        if not filepath.startswith("/"):
            filepath = _resolve_path(game.current_host.cwd, filepath)
        if filepath not in game.current_host.files:
            console.print_error(f"sed: {filepath}: No such file or directory")
            return
        content = game.current_host.files[filepath]
    elif game.stdin:
        content = game.stdin
        filepath = None
    else:
        console.print_error("sed: missing input")
        return

    lines = content.split("\n")
    # Remove trailing empty line from final \n
    if lines and lines[-1] == "":
        lines = lines[:-1]
    output = lines
    for script in scripts:
        output = _apply_sed_script(script, output, suppress)

    result = "\n".join(output)
    if inplace and filepath:
        game.current_host.files[filepath] = result
        game.current_host.user_files[filepath] = result
    else:
        console.print(result)


def _apply_sed_script(script: str, lines: list[str], suppress: bool) -> list[str]:
    """Apply a single sed script to lines."""
    output = []

    # Parse transliterate: y/abc/xyz/
    y_match = re.match(r'y(.)(.+?)\1(.+?)\1', script)
    if y_match:
        src = y_match.group(2)
        dst = y_match.group(3)
        if len(src) == len(dst):
            table = str.maketrans(src, dst)
            return [line.translate(table) for line in lines]
        return lines

    def _sed_bre_to_ere(pattern, replacement):
        """Convert BRE (sed default) to ERE (Python re): \\( → (, \\) → )"""
        pattern = pattern.replace("\\(", "(").replace("\\)", ")")
        pattern = pattern.replace("\\+", "+").replace("\\?", "?")
        pattern = pattern.replace("\\{", "{").replace("\\}", "}")
        return pattern, replacement

    # Parse substitution: s/pattern/replacement/flags
    sub_match = re.match(r's(.)(.+?)\1(.*?)\1(\w*)', script)
    # Delete: Nd or N,Md or $d
    del_match = re.match(r'(\d+|\$)(?:,(\d+|\$))?d', script)
    # Print: Np or N,Mp (with -n)
    print_match = re.match(r'(\d+|\$)(?:,(\d+|\$))?p', script)
    # Address + substitution: N,Ms/old/new/flags
    addr_sub = re.match(r'(\d+)(?:,(\d+))?s(.)(.+?)\3(.*?)\3(\w*)', script)

    for i, line in enumerate(lines):
        lineno = i + 1
        deleted = False

        if del_match:
            _total = len(lines)
            start = _total if del_match.group(1) == "$" else int(del_match.group(1))
            end_raw = del_match.group(2)
            end = (_total if end_raw == "$" else int(end_raw)) if end_raw else start
            if start <= lineno <= end:
                deleted = True

        if addr_sub and not deleted:
            start = int(addr_sub.group(1))
            end = int(addr_sub.group(2)) if addr_sub.group(2) else start
            if start <= lineno <= end:
                pattern = addr_sub.group(4)
                replacement = addr_sub.group(5)
                flags = addr_sub.group(6)
                count = 0 if "g" in flags else 1
                line = re.sub(pattern, replacement, line, count=count)
        elif sub_match and not deleted:
            pattern = sub_match.group(2)
            replacement = sub_match.group(3)
            flags = sub_match.group(4)
            pattern, replacement = _sed_bre_to_ere(pattern, replacement)
            count = 0 if "g" in flags else 1
            try:
                line = re.sub(pattern, replacement, line, count=count)
            except re.error:
                pass  # invalid regex, skip

        if not deleted:
            if suppress:
                if print_match:
                    start = int(print_match.group(1))
                    end = int(print_match.group(2)) if print_match.group(2) else start
                    if start <= lineno <= end:
                        output.append(line)
            else:
                output.append(line)

    return output


# -----------------------------------------------------------------------
# awk
# -----------------------------------------------------------------------
@register("awk", "cmd.awk.help", required_tool="awk")
def handle_awk(game, args):
    if _wants_help(args):
        console.print("Usage: awk [OPTIONS] 'PROGRAM' [FILE]...\n")
        console.print("  awk '{print $1}'          print first field")
        console.print("  awk -F: '{print $1}'      set delimiter to :")
        console.print("  awk '$3 > 100'            condition")
        console.print("  awk '{sum+=$1} END {print sum}'  accumulate")
        console.print("  awk 'NR==5'               print line 5")
        return
    if not _require_host(game):
        return

    # Parse -F separator
    sep = None
    non_flag = []
    i = 0
    while i < len(args):
        if args[i] == "-F" and i + 1 < len(args):
            sep = args[i + 1]
            i += 2
        elif args[i].startswith("-F"):
            sep = args[i][2:]
            i += 1
        elif not args[i].startswith("-"):
            non_flag.append(args[i])
            i += 1
        else:
            i += 1

    if not non_flag:
        console.print_error("awk: missing program")
        return

    program = non_flag[0]
    file_args = non_flag[1:]

    # Get content
    if file_args:
        from commands.filesystem_cmds import _resolve_path
        filepath = file_args[0]
        if not filepath.startswith("/"):
            filepath = _resolve_path(game.current_host.cwd, filepath)
        if filepath not in game.current_host.files:
            console.print_error(f"awk: {filepath}: No such file or directory")
            return
        content = game.current_host.files[filepath]
    elif game.stdin:
        content = game.stdin
    elif "BEGIN" in program:
        # BEGIN block can run without input
        content = ""
    else:
        console.print_error("awk: missing input")
        return

    _run_awk(content, program, sep)


def _run_awk(content: str, program: str, sep: str | None):
    """Simple awk interpreter supporting common patterns."""
    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    # Parse BEGIN/END blocks
    begin_action = ""
    end_action = ""
    main_program = program

    begin_m = re.search(r'BEGIN\s*\{([^}]*)\}', program)
    if begin_m:
        begin_action = begin_m.group(1)
        main_program = program[:begin_m.start()] + program[begin_m.end():]

    end_m = re.search(r'END\s*\{([^}]*)\}', main_program)
    if end_m:
        end_action = end_m.group(1)
        main_program = main_program[:end_m.start()] + main_program[end_m.end():]

    main_program = main_program.strip()

    # Variables
    awk_vars = {"NR": 0, "NF": 0, "FS": sep or " ", "OFS": " ", "ORS": "\n"}
    user_vars = {}

    # Execute BEGIN
    if begin_action:
        _awk_exec_action(begin_action, [], awk_vars, user_vars, sep)

    # Process lines
    for i, line in enumerate(lines):
        fields = line.split(sep) if sep else line.split()
        awk_vars["NR"] = i + 1
        awk_vars["NF"] = len(fields)

        if not main_program or main_program == "":
            continue

        # Parse: condition { action } or just { action }
        m = re.match(r'\{([^}]*)\}', main_program)
        cond_m = re.match(r'([^{]+)\{([^}]*)\}', main_program)
        bare_cond = re.match(r'^/([^/]+)/$', main_program)
        nr_cond = re.match(r'^NR\s*==\s*(\d+)$', main_program)

        if nr_cond:
            if awk_vars["NR"] == int(nr_cond.group(1)):
                console.print(line)
        elif bare_cond:
            if bare_cond.group(1) in line:
                console.print(line)
        elif cond_m:
            condition = cond_m.group(1).strip()
            action = cond_m.group(2).strip()
            if _awk_eval_condition(condition, fields, awk_vars, user_vars):
                _awk_exec_action(action, fields, awk_vars, user_vars, sep)
        elif m:
            action = m.group(1).strip()
            _awk_exec_action(action, fields, awk_vars, user_vars, sep)
        elif main_program and not main_program.startswith("{"):
            # Bare condition without action — print line if matches
            if _awk_eval_condition(main_program.strip(), fields, awk_vars, user_vars):
                console.print(line)

    # Execute END
    if end_action:
        _awk_exec_action(end_action, [], awk_vars, user_vars, sep)


def _awk_exec_action(action: str, fields: list[str], awk_vars: dict, user_vars: dict, sep: str | None):
    """Execute an awk action (simplified)."""
    # Handle multiple statements separated by ;
    for stmt in action.split(";"):
        stmt = stmt.strip()
        if not stmt:
            continue

        # print
        print_m = re.match(r'print\s*(.*)', stmt)
        if print_m:
            expr = print_m.group(1).strip()
            if not expr:
                console.print(" ".join(fields) if fields else "")
            else:
                result = _awk_eval_expr(expr, fields, awk_vars, user_vars, sep)
                console.print(result)
            continue

        # Assignment: var = expr or var += expr
        assign_m = re.match(r'(\w+)\s*(\+?=)\s*(.*)', stmt)
        if assign_m:
            var = assign_m.group(1)
            op = assign_m.group(2)
            val_expr = assign_m.group(3).strip()
            # String assignment (quoted value)
            if val_expr.startswith('"') and val_expr.endswith('"'):
                str_val = val_expr[1:-1].replace("\\t", "\t").replace("\\n", "\n")
                if var in awk_vars:
                    awk_vars[var] = str_val
                else:
                    user_vars[var] = str_val
            else:
                val = _awk_eval_numeric(val_expr, fields, awk_vars, user_vars)
                if op == "+=":
                    prev = user_vars.get(var, awk_vars.get(var, 0))
                    try: prev = float(prev)
                    except (ValueError, TypeError): prev = 0
                    user_vars[var] = prev + val
                elif var in awk_vars:
                    awk_vars[var] = val
                else:
                    user_vars[var] = val
            continue


def _awk_format_val(val) -> str:
    """Format awk value: integers without .0, floats with decimals."""
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val)


def _awk_eval_expr(expr: str, fields: list[str], awk_vars: dict, user_vars: dict, sep: str | None) -> str:
    """Evaluate an awk print expression."""
    ofs = str(awk_vars.get("OFS", " "))
    parts = []
    # Split by commas (print $1, $2) — commas use OFS
    # But handle string concatenation (space without comma) differently
    for part in expr.split(","):
        part = part.strip()
        val = _awk_resolve_value(part, fields, awk_vars, user_vars)
        parts.append(_awk_format_val(val))
    return ofs.join(parts)


def _awk_resolve_value(token: str, fields: list[str], awk_vars: dict, user_vars: dict):
    """Resolve a single value: $0, $1, $NF, NR, "string", variable."""
    token = token.strip()

    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]

    if token == "$0":
        return " ".join(fields)
    if token == "$NF":
        return fields[-1] if fields else ""
    if token == "$(NF-1)":
        return fields[-2] if len(fields) > 1 else ""

    m = re.match(r'^\$(\d+)$', token)
    if m:
        idx = int(m.group(1))
        if idx == 0:
            return " ".join(fields)
        return fields[idx - 1] if idx <= len(fields) else ""

    if token in awk_vars:
        return awk_vars[token]
    if token in user_vars:
        return user_vars[token]
    try:
        return float(token)
    except ValueError:
        pass

    # Try arithmetic evaluation: 1+2, NR*2, $1+$2, etc.
    if any(op in token for op in "+-*/%"):
        def _sub_val(m):
            v = m.group(0)
            if v.startswith("$"):
                idx = int(v[1:]) if v[1:].isdigit() else 0
                return str(fields[idx - 1] if 0 < idx <= len(fields) else 0)
            if v in awk_vars:
                return str(awk_vars[v])
            if v in user_vars:
                return str(user_vars[v])
            return v
        resolved = re.sub(r'\$\d+|\b[A-Za-z_]\w*\b', _sub_val, token)
        sanitized = re.sub(r'[^0-9+\-*/%.()\s]', '', resolved)
        try:
            result = eval(sanitized)
            return float(result) if isinstance(result, (int, float)) else result
        except Exception:
            pass

    return token


def _awk_eval_numeric(expr: str, fields: list[str], awk_vars: dict, user_vars: dict) -> float:
    """Evaluate numeric expression."""
    val = _awk_resolve_value(expr, fields, awk_vars, user_vars)
    try:
        return float(val)
    except (ValueError, TypeError):
        # Try direct arithmetic eval if resolve returned string with operators
        if isinstance(val, str) and any(op in val for op in "+-*/%"):
            sanitized = re.sub(r'[^0-9+\-*/%.()\s]', '', val)
            try:
                return float(eval(sanitized))
            except Exception:
                pass
        return 0


def _awk_eval_condition(condition: str, fields: list[str], awk_vars: dict, user_vars: dict) -> bool:
    """Evaluate awk condition like '$3 > 100'."""
    # /pattern/ match
    m = re.match(r'/(.+)/', condition)
    if m:
        return m.group(1) in " ".join(fields)

    # Comparison: $N op value
    m = re.match(r'(\$?\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)', condition)
    if m:
        left = _awk_resolve_value(m.group(1), fields, awk_vars, user_vars)
        op = m.group(2)
        right = _awk_resolve_value(m.group(3).strip(), fields, awk_vars, user_vars)
        try:
            left, right = float(left), float(right)
        except (ValueError, TypeError):
            left, right = str(left), str(right)
        if op == "==": return left == right
        if op == "!=": return left != right
        if op == ">": return left > right
        if op == "<": return left < right
        if op == ">=": return left >= right
        if op == "<=": return left <= right

    return True


# -----------------------------------------------------------------------
# tee
# -----------------------------------------------------------------------
@register("tee", "cmd.tee.help", required_tool="tee")
def handle_tee(game, args):
    if _wants_help(args):
        console.print("Usage: tee [OPTION]... [FILE]...\n")
        console.print("  cmd | tee file     write to file AND stdout")
        console.print("  cmd | tee -a file  append instead of overwrite")
        return
    if not _require_host(game):
        return

    content = game.stdin
    if not content:
        console.print_error("tee: missing input (use with pipe)")
        return

    append = "-a" in args
    files = [a for a in args if not a.startswith("-")]

    from commands.filesystem_cmds import _resolve_path
    host = game.current_host
    for f in files:
        filepath = f if f.startswith("/") else _resolve_path(host.cwd, f)
        if append and filepath in host.files:
            host.files[filepath] += content
        else:
            host.files[filepath] = content
        host.user_files[filepath] = host.files[filepath]

    # Also output to stdout
    console.print(content, end="")


# -----------------------------------------------------------------------
# xargs
# -----------------------------------------------------------------------
@register("xargs", "cmd.xargs.help", required_tool="xargs")
def handle_xargs(game, args):
    if _wants_help(args):
        console.print("Usage: xargs [OPTION]... COMMAND\n")
        console.print("  cat list | xargs rm        pass stdin as args to cmd")
        console.print("  xargs -n 1 cmd             one arg per invocation")
        console.print("  xargs -I {} cmd {}         placeholder")
        return
    if not _require_host(game):
        return

    content = game.stdin
    if not content:
        console.print_error("xargs: missing input (use with pipe)")
        return

    from engine.shell import process_line

    # Parse options
    placeholder = None
    max_args = 0  # 0 = all at once
    cmd_parts = []

    i = 0
    while i < len(args):
        if args[i] == "-I" and i + 1 < len(args):
            placeholder = args[i + 1]
            i += 2
        elif args[i] == "-n" and i + 1 < len(args):
            try:
                max_args = int(args[i + 1])
            except ValueError:
                max_args = 1
            i += 2
        elif args[i].startswith("-n") and args[i][2:].isdigit():
            max_args = int(args[i][2:])
            i += 1
        elif not args[i].startswith("-"):
            cmd_parts = args[i:]
            break
        else:
            i += 1

    if not cmd_parts:
        cmd_parts = ["echo"]

    # Split input into individual items (by whitespace, like real xargs)
    items = content.strip().split()

    if placeholder:
        for item in items:
            cmd_str = " ".join(cmd_parts).replace(placeholder, item)
            process_line(cmd_str)
    elif max_args > 0:
        # Process N items at a time
        for j in range(0, len(items), max_args):
            batch = items[j:j + max_args]
            cmd_str = " ".join(cmd_parts) + " " + " ".join(batch)
            process_line(cmd_str)
    else:
        cmd_str = " ".join(cmd_parts) + " " + " ".join(items)
        process_line(cmd_str)


# -----------------------------------------------------------------------
# rev
# -----------------------------------------------------------------------
@register("rev", "cmd.rev.help", required_tool="rev")
def handle_rev(game, args):
    if _wants_help(args):
        console.print("Usage: rev [FILE]...\n")
        console.print("  rev file      reverse each line")
        console.print("  cmd | rev     reverse stdin")
        return
    if not _require_host(game):
        return
    content = _get_input(game, args, "rev")
    if content is None:
        return
    lines = content.split("\n")
    console.print("\n".join(line[::-1] for line in lines))


# -----------------------------------------------------------------------
# seq
# -----------------------------------------------------------------------
@register("seq", "cmd.seq.help", required_tool="seq")
def handle_seq(game, args):
    if _wants_help(args):
        console.print("Usage: seq [OPTION]... LAST\n       seq FIRST LAST\n       seq FIRST INCREMENT LAST\n")
        console.print("  seq 5           1 2 3 4 5")
        console.print("  seq 2 10        2 3 4 ... 10")
        console.print("  seq 1 2 10      1 3 5 7 9")
        console.print("  seq -s, 1 5     1,2,3,4,5")
        return

    sep = "\n"
    fmt = None
    new_args = []
    i = 0
    while i < len(args):
        if args[i] == "-s" and i + 1 < len(args):
            sep = args[i + 1]
            i += 2
        elif args[i].startswith("-s") and len(args[i]) > 2:
            sep = args[i][2:]
            i += 1
        elif args[i] == "-f" and i + 1 < len(args):
            fmt = args[i + 1]
            i += 2
        elif args[i].startswith("-w"):
            fmt = "padded"
            i += 1
        elif not args[i].startswith("-"):
            new_args.append(args[i])
            i += 1
        else:
            i += 1

    nums = new_args
    try:
        if len(nums) == 1:
            start, step, end = 1, 1, int(nums[0])
        elif len(nums) == 2:
            start, step, end = int(nums[0]), 1, int(nums[1])
        elif len(nums) >= 3:
            start, step, end = int(nums[0]), int(nums[1]), int(nums[2])
        else:
            console.print_error("seq: missing operand")
            return
    except ValueError:
        console.print_error("seq: invalid argument")
        return

    values = []
    i = start
    while (step > 0 and i <= end) or (step < 0 and i >= end):
        values.append(str(i))
        i += step
        if len(values) > 10000:
            break

    console.print(sep.join(values))
