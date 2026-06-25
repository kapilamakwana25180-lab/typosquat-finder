"""
generator.py
Generates likely typo-squatting variants of a given domain name.
"""

HOMOGLYPHS = {
    "o": ["0"], "l": ["1", "i"], "i": ["1", "l"], "e": ["3"],
    "a": ["4", "@"], "s": ["5"], "m": ["rn"], "w": ["vv"],
    "g": ["q"], "b": ["d"],
}

COMMON_TLDS = ["com", "net", "org", "info", "biz", "co", "online", "site", "xyz"]


def split_domain(domain: str):
    domain = domain.lower().strip()
    if "." in domain:
        name, tld = domain.rsplit(".", 1)
    else:
        name, tld = domain, "com"
    return name, tld


def omission_variants(name: str):
    return {name[:i] + name[i+1:] for i in range(len(name))}


def swap_variants(name: str):
    variants = set()
    for i in range(len(name) - 1):
        chars = list(name)
        chars[i], chars[i+1] = chars[i+1], chars[i]
        variants.add("".join(chars))
    return variants


def insertion_variants(name: str):
    return {name[:i+1] + name[i] + name[i+1:] for i in range(len(name))}


def replacement_variants(name: str):
    variants = set()
    for i, ch in enumerate(name):
        if ch in HOMOGLYPHS:
            for sub in HOMOGLYPHS[ch]:
                variants.add(name[:i] + sub + name[i+1:])
    return variants


def hyphenation_variants(name: str):
    if len(name) < 4:
        return set()
    return {name[:i] + "-" + name[i:] for i in range(1, len(name))}


def tld_variants(name: str, original_tld: str):
    return {f"{name}.{tld}" for tld in COMMON_TLDS if tld != original_tld}


def generate_variants(domain: str):
    name, tld = split_domain(domain)
    original = f"{name}.{tld}"

    name_variants = set()
    name_variants |= omission_variants(name)
    name_variants |= swap_variants(name)
    name_variants |= insertion_variants(name)
    name_variants |= replacement_variants(name)
    name_variants |= hyphenation_variants(name)

    full_variants = {f"{v}.{tld}" for v in name_variants if v}
    full_variants |= tld_variants(name, tld)
    full_variants.discard(original)

    # Filter out anything that isn't a structurally valid domain
    # (e.g. double dots from a duplicated "." character, or leading/trailing dots)
    valid = {
        v for v in full_variants
        if ".." not in v and not v.startswith(".") and not v.endswith(".")
        and all(part for part in v.split("."))
    }

    return sorted(valid)


if __name__ == "__main__":
    test_domain = "example.com"
    results = generate_variants(test_domain)
    print(f"Generated {len(results)} variants for '{test_domain}':\n")
    for v in results:
        print(" -", v)
