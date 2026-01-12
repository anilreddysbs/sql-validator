# validator/parser.py
"""
Robust SQL/PLSQL splitter.

Key design decisions:
- Remove block and line comments (safe inside quotes).
- Tokenize on top-level semicolons while preserving quoted strings.
- EARLY: group COMMIT tokens with the previous statement (so COMMIT is never treated as a standalone next-statement).
- Split tokens into smaller chunks when safe using newline/keyword heuristics (but avoid splitting inside PL/SQL).
- Merge PL/SQL blocks using a BEGIN/END counting approach; attach trailing "/" if present.
- Final pass ensures any leftover standalone "/" is merged with the preceding END; block.
"""
import re

NEW_STMT_KEYWORD_RE = re.compile(
    r'^\s*(insert|update|delete|create|alter|drop|truncate|grant|revoke|begin|declare)\b',
    re.IGNORECASE
)

_SLASH_RE = re.compile(r'^\s*/\s*$', re.IGNORECASE)


# -------------------------
# Comment removal
# -------------------------
def _remove_block_comments(text: str) -> str:
    # Replace block comment with same number of newline chars to preserve line numbers
    return re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)


def _remove_line_comments(text: str) -> str:
    # Remove -- comments unless inside single or double quotes
    out_lines = []
    for line in text.splitlines():
        i = 0
        in_single = False
        in_double = False
        keep_pos = len(line)
        while i < len(line):
            ch = line[i]
            if ch == "'" and not in_double:
                # toggle single quote state (handle doubled '' escapes later in tokenizer)
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            # detect start of a comment
            if not in_single and not in_double and ch == '-' and i + 1 < len(line) and line[i+1] == '-':
                keep_pos = i
                break
            i += 1
        out_lines.append(line[:keep_pos])
    return "\n".join(out_lines)


# -------------------------
# Top-level tokenizer (split on semicolons, respect quoted strings)
# -------------------------
def _tokenize_top_level(text: str):
    tokens = []
    buf = []
    i = 0
    L = len(text)
    while i < L:
        ch = text[i]
        # single-quoted string
        if ch == "'":
            buf.append(ch)
            i += 1
            while i < L:
                buf.append(text[i])
                # handle escaped '' inside SQL (two single quotes)
                if text[i] == "'" and i + 1 < L and text[i+1] == "'":
                    i += 2
                    continue
                if text[i] == "'":
                    i += 1
                    break
                i += 1
            continue

        # double-quoted identifier
        if ch == '"':
            buf.append(ch)
            i += 1
            while i < L:
                buf.append(text[i])
                # "" escapes inside identifiers
                if text[i] == '"' and i + 1 < L and text[i+1] == '"':
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            continue

        # semicolon → end a top-level token (we keep the semicolon)
        if ch == ';':
            buf.append(ch)
            tokens.append(''.join(buf))
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    leftover = ''.join(buf)
    if leftover.strip():
        tokens.append(leftover)
    return tokens


# -------------------------
# Group commits with previous (EARLY)
# -------------------------
def _group_commits_with_previous(chunks):
    """
    Always attach COMMIT (or COMMIT <opts>) to previous chunk.
    This must run early so later PL/SQL merges won't separate commit.
    """
    out = []
    for st in chunks:
        if not st or not st.strip():
            out.append(st)
            continue
        s = st.strip()
        s_norm = re.sub(r'\s+', ' ', s).lower()
        # treat "commit" or "commit work" or "commit;" etc.
        if s_norm.startswith("commit"):
            if out:
                # attach commit to previous chunk with newline separation
                out[-1] = out[-1].rstrip() + "\n" + s
            else:
                # no previous; keep as-is (edge-case)
                out.append(s)
        else:
            out.append(st)
    return out

def _extract_slash_lines(chunk):
    """Extract standalone slash '/' lines into separate tokens."""
    lines = chunk.splitlines()
    out = []
    buf = []
    for ln in lines:
        if re.fullmatch(r"\s*/\s*", ln):
            if buf:
                out.append("\n".join(buf))
                buf = []
            out.append("/")  # standalone slash token
        else:
            buf.append(ln)
    if buf:
        out.append("\n".join(buf))
    return out


# -------------------------
# Keyword-based splitting (safe): split on new statements when not inside PL/SQL
# -------------------------
def _split_on_newline_keyword(chunks):
    out = []
    for st in chunks:
        if st is None:
            continue
        if '\n' not in st:
            out.append(st.strip())
            continue

        lines = st.splitlines(True)  # keep newline chars
        buf = ""
        in_plsql = False
        for ln in lines:
            # detect start of plsql block (declare/begin)
            if re.match(r'^\s*(declare|begin)\b', ln, re.IGNORECASE):
                in_plsql = True

            # Only split when we're not inside a plsql block and the new line starts with a top-level keyword
            if (not in_plsql and NEW_STMT_KEYWORD_RE.match(ln)
                    and buf.strip() and not buf.rstrip().endswith(';')):
                subchunks = _extract_slash_lines(buf.strip())
                out.extend([s.strip() for s in subchunks if s.strip()])

                buf = ln
            else:
                buf += ln

            # If an END; appears we may exit plsql mode (but block-merger will do strict checks)
            if re.search(r'\bend\b\s*;', ln, re.IGNORECASE):
                in_plsql = False

        if buf.strip():
            subchunks = _extract_slash_lines(buf.strip())
            out.extend([s.strip() for s in subchunks if s.strip()])

    return out


# -------------------------
# Merge PL/SQL blocks using counter of BEGIN/END occurrences
# -------------------------
def _merge_plsql_blocks(chunks):
    merged = []
    i = 0
    L = len(chunks)
    # patterns to detect PL/SQL start tokens
    start_re = re.compile(r'^\s*(declare|begin)\b', re.IGNORECASE)
    # count begin tokens and end; tokens inside a token
    begin_word_re = re.compile(r'\bbegin\b', re.IGNORECASE)
    end_stmt_re = re.compile(r'\bend\b\s*;', re.IGNORECASE)

    while i < L:
        token = chunks[i]
        if not token:
            i += 1
            continue
        tok_strip = token.strip()

        if start_re.match(tok_strip):
            # we believe we've found a PL/SQL block start — collect until counts balance and optionally attach slash
            parts = [token]
            combined = token
            begin_count = len(begin_word_re.findall(combined))
            end_count = len(end_stmt_re.findall(combined))
            j = i + 1
            # gather tokens until end_count >= begin_count and begin_count > 0
            while j < L:
                nxt = chunks[j]
                if nxt is None:
                    j += 1
                    continue
                nxt_strip = nxt.strip()

                # If the next token is purely a slash, don't include here — break and allow attach later
                if _SLASH_RE.match(nxt_strip):
                    break

                parts.append(nxt)
                combined += '\n' + nxt
                begin_count += len(begin_word_re.findall(nxt))
                end_count += len(end_stmt_re.findall(nxt))

                # balanced and we had at least one begin -> stop
                if begin_count > 0 and end_count >= begin_count:
                    j += 1
                    break
                j += 1

            block = "\n".join(parts).strip()

            # Attach slash if present as next token
            if j < L and chunks[j] and _SLASH_RE.match(chunks[j].strip()):
                block = block.rstrip() + "\n/"
                j += 1

            merged.append(block)
            i = j
            continue

        merged.append(token)
        i += 1
    return merged


# -------------------------
# Final pass: ensure standalone "/" merges with previous END; if any leftover
# -------------------------
def _attach_trailing_slashes(chunks):
    final = []
    i = 0
    L = len(chunks)
    while i < L:
        t = chunks[i]
        if t is None:
            i += 1
            continue
        ts = t.strip()
        # if token is just a slash, attach to previous
        if _SLASH_RE.match(ts):
            if final:
                final[-1] = final[-1].rstrip() + "\n/"
            else:
                # nothing to attach to; keep as-is
                final.append('/')
            i += 1
            continue

        # if token ends with END; and next token is slash, merge them
        if re.search(r'\bend\b\s*;$', ts, re.IGNORECASE) and i + 1 < L and chunks[i+1] and _SLASH_RE.match(chunks[i+1].strip()):
            final.append(ts + "\n/")
            i += 2
            continue

        final.append(t.strip())
        i += 1
    return final


# -------------------------
# Public API
# -------------------------
def split_sql_queries(text: str):
    if not text:
        return []

    txt = text.replace('\r\n', '\n').replace('\r', '\n')
    txt = _remove_block_comments(txt)
    txt = _remove_line_comments(txt)

    # 1) Tokenize on semicolons (top-level)
    tokens = _tokenize_top_level(txt)

    # 2) Early: group COMMIT tokens with previous statement (critical)
    tokens = _group_commits_with_previous(tokens)

    # 3) Split on newline keywords (safe splitting)
    tokens = _split_on_newline_keyword(tokens)

    # 4) Merge PL/SQL blocks strictly (BEGIN/END counting), attach "/" if next token is slash
    tokens = _merge_plsql_blocks(tokens)

    # 5) Final attach: ensure any leftover '/' is merged with preceding END;
    tokens = _attach_trailing_slashes(tokens)

    # cleanup and strip each token
    tokens = [t.strip() for t in tokens if t and t.strip()]

    return tokens
