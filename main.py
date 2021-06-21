import json
from collections import defaultdict
from itertools import chain
import re
from base_classes import ClassGenerator, TypeHint, NameGenerator

from additional_generators import ResultClassGenerator


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
                res_type = TypeHint.string_iter()
                code = f'map(attrgetter("text"), {code})'
            elif selector["type"] == "SelectorElementAttribute":
                res_type = TypeHint.string_iter()
                code = f'map(itemgetter("{selector["extractAttribute"]}", {code}))'
            elif selector["type"] == "SelectorElement":
                cls_name = to_class_name(selector["id"])
                res_type = TypeHint("Iterator", cls_name, True)
                code = f"map({cls_name}, {code})"
            elif selector["type"] == "SelectorLink":
                res_type = TypeHint.string_iter()
                code = f'map(itemgetter("href", {code}))'
            elif selector["type"] == "SelectorImage":
                res_type = TypeHint.string_iter()
                code = f'map(itemgetter("src", {code}))'
            else:
                raise ValueError(selector)
        else:
            if selector["selector"] == "_parent_":
                code = "self.html"
            else:
                code = f'self.html.select_one("{selector["selector"]}")'

            if selector["type"] == "SelectorText":
                res_type = TypeHint.optional_string()
                code = f"None if (element := {code}) is None else element.text"
            elif selector["type"] == "SelectorElementAttribute":
                res_type = TypeHint.optional_string()
                code += f'.get("{selector["extractAttribute"]}", None)'
            elif selector["type"] == "SelectorLink":
                res_type = TypeHint.optional_string()
                code += '.get("href", None)'
            elif selector["type"] == "SelectorImage":
                res_type = TypeHint.optional_string()
                code += '.get("src", None)'
            elif selector["type"] == "SelectorElement":
                cls_name = to_class_name(selector["id"])
                res_type = TypeHint("Optional", cls_name, True)
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


def generate(name, values):
    name_gen = NameGenerator()
    obj = ClassGenerator(to_class_name(name), name_gen, additional_generators=[ResultClassGenerator])

    for code, function_name, typing in values:
        obj.add_method(to_function_name(function_name), code, typing)

    return obj


# https://stackoverflow.com/questions/51286748/make-the-python-json-encoder-support-pythons-new-dataclasses
JSON_ENCODER = """
class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            return super().default(o)\n\n"""

IMPORTS = [
    "from typing import Optional, Iterator, List",
    "from bs4 import BeautifulSoup",
    "from operator import attrgetter",
    "from operator import methodcaller",
    "from dataclasses import dataclass",
    "import json",
    "import dataclasses"
]

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("Convert web scraper json to python classes")
    parser.add_argument("-i", help="input file")
    parser.add_argument("-o", help="output file")
    args = parser.parse_args().__dict__

    with open(args["i"], "r") as i:
        input_json = json.load(i)

        with open(args["o"], "w+") as o:
            o.write("".join([
                "\n".join(IMPORTS),
                "\n\n",
                JSON_ENCODER,
                *[generate(key, value).serialize() for key, value in process(input_json).items()],
            ]))
