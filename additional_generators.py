from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List
from base_classes import Method, TypeHint


@dataclass
class AdditionalGeneratorOutput:
    additional_methods: List['Method'] = field(default_factory=list)
    additional_classes: List[str] = field(default_factory=list)


class AdditionalGenerator(ABC):
    def __init__(self, methods, name_generator, name):
        self.methods = methods
        self.name_generator = name_generator
        self.name = name

    @abstractmethod
    def serialize(self) -> AdditionalGeneratorOutput:
        pass


class ResultClassGenerator(AdditionalGenerator):
    def serialize(self):
        class_name = self.name_generator.generate_result_class_name(self.name)

        result = []
        result_class = [f"\n@dataclass\nclass {class_name}:"]
        for name, type_hint in map(lambda x: (x.name, x.type_hint), self.methods):
            if name == "to_json":
                continue
            result.append(
                self._handle_custom_type(
                    name, type_hint) if type_hint.is_custom_class else self._handle_standard_type(
                    name, type_hint))
            result_class.append(f"\t{name}: {type_hint.serialize(True)}")

        creation_code = f'{class_name}({", ".join(result)})'
        return AdditionalGeneratorOutput(
            [Method(self.name_generator.generate_result_method_name(), creation_code,
                    TypeHint(None, class_name, True))], ["\n".join(result_class) + "\n"])

    @staticmethod
    def _handle_standard_type(name, type_hint):
        if type_hint.base_type == "Iterator":
            return f"list(self.{name}())"
        return f"self.{name}()"

    def _handle_custom_type(self, name, type_hint):
        if type_hint.base_type == "Iterator":
            return f"list(map(methodcaller('{self.name_generator.generate_result_method_name()}'), self.{name}()))"
        if type_hint.base_type == "Optional":
            return f"None if (element := self.{name}()) is None else {name}.{self.name_generator.generate_result_method_name(name)}()"
        raise ValueError(type_hint)
