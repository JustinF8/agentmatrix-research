from __future__ import annotations


def trace(factor_name: str, index: dict, max_depth: int = 12):
    edges, order, seen = {}, [], set()

    def visit(name, depth):
        if depth > max_depth or name not in index:
            return
        rec = index[name]
        children = [c for c in rec["calls"] if c in index and c != name]
        edges[name] = children
        for c in children:
            if c not in seen:
                seen.add(c)
                visit(c, depth + 1)
        if name not in order:
            order.append(name)

    seen.add(factor_name)
    visit(factor_name, 0)
    deps = [n for n in order if n != factor_name]
    return deps, edges


def reference_text(factor_name: str, index: dict, deps: list[str]) -> str:
    blocks = []
    for name in [factor_name] + deps:
        if name not in index:
            continue
        r = index[name]
        blocks.append(f"# Function: {r['name']}\n"
                      f"# File: {r['file']}:{r['start_line']}-{r['end_line']}\n"
                      f"{r['source']}")
    return "\n\n".join(blocks)


def helper_sources(index: dict, deps: list[str]) -> str:
    return "\n\n".join(index[n]["source"] for n in deps if n in index)


def ascii_tree(factor_name: str, edges: dict) -> str:
    lines = [factor_name]
    visited = set()

    def walk(name, prefix):
        children = edges.get(name, [])
        for i, c in enumerate(children):
            last = i == len(children) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{c}")
            if c not in visited:
                visited.add(c)
                walk(c, prefix + ("    " if last else "│   "))

    visited.add(factor_name)
    walk(factor_name, "")
    return "\n".join(lines)
