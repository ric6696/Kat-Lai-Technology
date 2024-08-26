import random


def _generate_invalid_codes_from_baseChars(length: int = 15) -> list[str]:
    invalid_codes_base = ["A", "1", " ", "-", "!", "\\"]

    def concat(inputs: list[list[str]]) -> list[str | None]:
        if not inputs:
            return []
        return inputs[0] + concat(inputs[1:])

    return concat([[x * i for x in invalid_codes_base] for i in range(1, length + 1)])


def get_invalid_V1_codes(num_codes: int = 1) -> list[str]:
    ReallyGoodBadUTF8chars = (
        "!\"#$%&'()*+,-./0123456789:;<=>?@[]^_{}~çúăćĢģļľŉŖŧŵŸźžſƀƇƘƝƲ𝞄𝞎𝞲𝝲"
        + "ƳǏǓǩǬȊȎȚȞȟȤȯȶɌɭʟΒΡΣιψАКНЦкотѠѣѦѧҝҤԍԸՀդծ١٤০ႹყძᎥᏏᏔᖯᗞᵮᵲḂḆḋḞḧḿṃṚṛṮ"
        + "ṰṺṽẃẉảếềễỈừℊℕℱⅤ⤬ⱺⲘⲤⲬꓗꓡꓢꓧꓫꜱꞑꞠ𝐉𝐣𝐨𝑀𝑄𝑆𝑌𝑒𝑓𝑗𝑞𝑢𝑵𝒋𝒌𝒒𝒙𝒚𝒞𝒯𝒱𝓅𝓕𝓛𝓜𝓢𝓧𝓼𝔍𝔚𝔠𝔳𝕛"
        + "𝕟𝕢𝕣𝕤𝕯𝕵𝖘𝖠𝖢𝖤𝖴𝖼𝖿𝗀𝗂𝗋𝗏𝗓𝗗𝗙𝗤𝗱𝘅𝘆𝘈𝘋𝘝𝘞𝘢𝘱𝘲𝘴𝙅𝙉𝙕𝙜𝙝𝙩𝙱𝙴𝙼𝙿𝚈𝚣𝚭𝚸𝜈𝜡𝜥𝜶𝝔"
    )

    chars = []
    for _ in range(num_codes):
        chars.append(random.choices(ReallyGoodBadUTF8chars, k=3))

    def get_code_prefix(three_chars: list[str]) -> str:
        three_chars.insert(random.randint(0, 2), str(random.choice(range(0, 10))))
        return "".join(three_chars)

    nums = [str(x) for x in range(0, 10)]

    def get_full_code(prefix: str) -> str:
        return prefix + "01" + "".join(random.choices(nums, k=8))

    return list(map(get_full_code, map(get_code_prefix, chars)))


# def get_valid_V1_codes() -> Iterable[str]:


def get_invalid_V1_code() -> str:
    return get_invalid_V1_codes(1)[0]


def reserved_serial() -> str:
    return "TEST0100000000"


def main():
    codes = _generate_invalid_codes_from_baseChars(15) + list(get_invalid_V1_codes())
    with open("invalid_serial_codes.txt", "w") as file:
        file.write("\n".join(codes))


if __name__ == "__main__":
    main()
