from dataclasses import dataclass, field
from operator import methodcaller
from typing import List


class NameGenerator:
    @staticmethod
    def generate_result_class_name(name):
        return name + "FullResult"

    @staticmethod
    def generate_result_method_name():
        return "get_full_result"


@dataclass
class TypeHint:
    base_type: str
    type: str
    is_custom_class: bool

    @classmethod
    def string_iter(cls):
        return cls("Iterator", "str", False)

    @classmethod
    def optional_string(cls):
        return cls("Optional", "str", False)

    def serialize(self, as_list=False):
        type_hint = self.type if not self.is_custom_class else f"'{self.type}'"

        if as_list and self.base_type == "Iterator":
            return f"List[{type_hint}]"

        if self.base_type:
            return f"{self.base_type}[{type_hint}]"
        return type_hint


@dataclass
class Method:
    name: str
    code: str
    type_hint: TypeHint

    def serialize(self):
        return f"\tdef {self.name}(self) -> {self.type_hint.serialize()}:\n\t\treturn {self.code}\n\n"


@dataclass
class ClassGenerator:
    name: str
    name_generator: NameGenerator
    methods: List[Method] = field(default_factory=list)
    additional_generators: List[any] = field(default_factory=list)

    def __post_init__(self):
        self.methods.append(
            Method("to_json", "json.dumps(self.get_full_result(), cls=EnhancedJSONEncoder)",
                   TypeHint(None, "str", False)))

    def serialize(self):
        additional_classes = []

        for additional_content in map(lambda x: x(self.methods, self.name_generator, self.name).serialize(),
                                      self.additional_generators):
            self.methods.extend(additional_content.additional_methods)
            additional_classes.extend(additional_content.additional_classes)

        return "\n\n".join([*additional_classes,
                            f"class {self.name}:\n\tdef __init__(self, html: BeautifulSoup):\n\t\tself.html = html\n\n" + "".join(
                                map(methodcaller("serialize"), self.methods)), ])

    def add_method(self, name, code, type_hint):
        self.methods.append(Method(name, code, type_hint))
