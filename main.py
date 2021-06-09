import json
from collections import defaultdict
from itertools import chain
import re


def split_name(name):
    chunks = re.split("[ \t\n,_\.-]", name)

    return map(
        lambda x: x.lower(),
        chain(
            *[
                re.sub(
                    "([A-Z][a-z]+)", r" \1", re.sub("([A-Z]+)", r" \1", chunk)
                ).split()
                for chunk in filter(lambda x: x != "", chunks)
            ]
        ),
    )


def to_function_name(name):
    return "_".join(split_name(name))


def to_class_name(name):
    return "".join(map(lambda x: x.title(), split_name(name)))


def process(input_dict):
    result = defaultdict(list)
    root_name = input_dict["_id"]

    for selector in input_dict["selectors"]:
        if selector["selector"] == "":
            continue

        if selector["multiple"]:
            assert selector["selector"] != "_parent_"
            code = f'self.html.select("{selector["selector"]}")'

            if selector["type"] == "SelectorText":
                res_type = "Iterator[str]"
                code = f'map(attrgetter("text"), {code})'
            elif selector["type"] == "SelectorElementAttribute":
                res_type = "Generator[str, None, None]"
                code = f'map(itemgetter("{selector["extractAttribute"]}", {code}))'
            elif selector["type"] == "SelectorElement":
                cls_name = to_class_name(selector["id"])
                res_type = f"Iterator['{cls_name}']"
                code = f"map({cls_name}, {code})"
            else:
                raise ValueError(selector)
        else:
            if selector["selector"] == "_parent_":
                code = "self.html"
            else:
                code = f'self.html.select_one("{selector["selector"]}")'

            if selector["type"] == "SelectorText":
                res_type = "Optional[str]"
                code += ".text"
            elif selector["type"] == "SelectorElementAttribute":
                res_type = "Optional[str]"
                code += f'.get("{selector["extractAttribute"]}", None)'
            elif selector["type"] == "SelectorElement":
                cls_name = to_class_name(selector["id"])
                res_type = f"Optional['{cls_name}']"
                code = f"None if (element := {code}) is None else {cls_name}(element)"
            else:
                raise ValueError(selector)

        assert len(selector["parentSelectors"]) == 1
        if selector["id"] == "_id":
            result[selector["parentSelectors"][0]].append((code, root_name, res_type))
        else:
            result[selector["parentSelectors"][0]].append(
                (code, selector["id"], res_type)
            )

    return result


class ClassGenerator:
    def __init__(self, name):
        self.text = f"""class {name}:\n\tdef __init__(self, html: BeautifulSoup):\n\t\tself.html = html\n"""

    def add_method(self, name, code, type_hint=None):
        type_hint = "" if type_hint is None else f" -> {type_hint}"
        self.text += f"\tdef {name}(self){type_hint}:\n\t\treturn {code}\n\n"


def generate(name, values):
    obj = ClassGenerator(to_class_name(name))

    for code, function_name, typing in values:
        obj.add_method(to_function_name(function_name), code, typing)

    return obj


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("Convert web scraper json to python classes")
    parser.add_argument("-i", help="input file")
    parser.add_argument("-o", help="output file")
    args = parser.parse_args().__dict__

    with open(args["i"], "r") as i:
        input_json = json.load(i)

        with open(args["o"], "w+") as o:
            o.write("\n\n\n".join([
                "from typing import Optional, Iterator\nfrom bs4 import BeautifulSoup\nfrom operator import attrgetter",
                *[generate(key, value).text for key, value in process(input_json).items()],
            ]))