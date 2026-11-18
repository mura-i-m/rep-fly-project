"""Python 標準ライブラリから、コメントと docstring を除いたコードを集めて corpus/train.py, test.py を作る"""
import io, sys, tokenize, random, sysconfig
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ["json/encoder.py", "json/decoder.py", "csv.py", "textwrap.py", "string/__init__.py", "shlex.py",
           "fnmatch.py", "glob.py", "queue.py", "bisect.py", "heapq.py", "colorsys.py", "keyword.py",
           "operator.py", "copy.py", "dataclasses.py", "functools.py", "pprint.py", "random.py", "statistics.py",
           "fractions.py", "calendar.py", "ipaddress.py", "argparse.py", "configparser.py", "difflib.py"]


def strip(src):
    out, prev = [], tokenize.INDENT
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.STRING and prev in (tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE, tokenize.NL):
            out.append((tokenize.STRING, '""'))  # docstring は空文字に
        else:
            out.append((tok.type, tok.string))
        if tok.type not in (tokenize.COMMENT,):
            prev = tok.type
    code = tokenize.untokenize(out)
    lines = [l.rstrip() for l in code.splitlines()]
    lines = [l for l in lines if l.strip() and l.strip() != '""']
    return "\n".join(lines) + "\n"


def main():
    lib = Path(sysconfig.get_paths()["stdlib"])
    files = []
    for m in MODULES:
        p = lib / m
        if p.exists():
            try:
                files.append((m, strip(p.read_text(encoding="utf-8"))))
            except Exception as e:
                print("skip", m, e)
    random.Random(0).shuffle(files)
    n = max(2, len(files) // 6)
    test, train = files[:n], files[n:]
    (ROOT / "corpus" / "train.py").write_text("".join(c for _, c in train), encoding="utf-8")
    (ROOT / "corpus" / "test.py").write_text("".join(c for _, c in test), encoding="utf-8")
    print("train:", [m for m, _ in train]); print("test:", [m for m, _ in test])
    for f in ["train.py", "test.py"]:
        print(f, len((ROOT / "corpus" / f).read_text()), "文字")


if __name__ == "__main__":
    main()
