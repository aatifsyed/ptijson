import argparse
import json
import shlex
import sys
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, TextIO, Union

import argcomplete
import jmespath
from jmespath.exceptions import EmptyExpressionError, ParseError, JMESPathError
from prompt_toolkit import prompt
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_input

JSONType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]


class JSONCompleter(Completer):
    def __init__(self, json_data: JSONType) -> None:
        self.json_data = json_data

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        try:
            current: JSONType = jmespath.search(
                expression=document.text_before_cursor,
                data=self.json_data,
                options=jmespath.Options(dict_cls=OrderedDict),
            )
            if isinstance(current, Dict):
                for k, v in current.items():
                    yield Completion(text=f".{shlex.quote(k)}", display_meta=str(v))
            elif isinstance(current, List):
                for i, v in enumerate(current):
                    yield Completion(text=f"[{i}]", display_meta=str(v))
        except ParseError:
            return
        except EmptyExpressionError:
            current = self.json_data

            if isinstance(current, Dict):
                for k, v in current.items():
                    yield Completion(text=f"{shlex.quote(k)}", display_meta=str(v))
            elif isinstance(current, List):
                for i, v in enumerate(current):
                    yield Completion(text=f"[{i}]", display_meta=str(v))


class QueryValidator(Validator):
    def validate(self, document: Document) -> None:
        try:
            jmespath.compile(document.text)
        except JMESPathError as e:
            raise ValidationError(message=f"Invalid jmespath query: {e}") from e


def main() -> int:
    parser = argparse.ArgumentParser(description="Iteractive JMESPath query")
    parser.add_argument("-i", "--input", type=argparse.FileType("r"), default=sys.stdin)
    parser.add_argument(
        "-o", "--output", type=argparse.FileType("w"), default=sys.stdout
    )
    parser.add_argument("-q", "--query", default=None)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    input_: TextIO = args.input
    output: TextIO = args.output
    query: Optional[str] = args.query

    try:
        json_data: JSONType = json.load(input_)
    except Exception as e:
        print(f"Couldn't load JSON: {e}", file=sys.stderr)
        return 1

    with create_app_session(input=create_input(always_prefer_tty=True)):
        expression = prompt(
            "ijson> ",
            completer=JSONCompleter(json_data=json_data),
            validator=QueryValidator(),
            complete_while_typing=True,
            placeholder=query,
        )

    result = jmespath.search(expression=expression, data=json_data)
    json.dump(result, output)
    return 0


def _main():
    sys.exit(main())
