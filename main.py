import argparse
import re
import sys
from typing import Optional

verbose = False

property = re.compile(r"^[a-z][a-z-]* = (.*)")
whitespace = re.compile(r"^\s*$")
name_property = re.compile(r'^name = "(.*)"$')
sdist_property = re.compile(r'^sdist = { url = "([^"]*)", hash = "sha256:([^"]*)", .*}')


def debug(message):
    if verbose:
        print(f" 🐞 {message}", file=sys.stderr)


# Wrapper for sys.stdin that has a peek() functionality.
class StdinReader:
    def __init__(self):
        # Store initial line to state
        self.current_line: int = 0
        self.update_buffer()

    # Updates the buffer by reading the next line from stdin. The buffer will
    # be set to None if EOF is reached.
    def update_buffer(self) -> None:
        buffer = sys.stdin.readline()
        if buffer == "":
            self.buffer: Optional[str] = None
            debug(f"EOL reached after {self.current_line} lines.")
        else:
            # Trailing newline already removed from buffer.
            self.buffer = buffer.rstrip("\n")
            self.current_line = self.current_line + 1
            debug(f"{self.current_line}: {self.buffer}")

    def has_next(self) -> bool:
        return self.buffer is not None

    # Returns the next line and advances in stdin.
    def next(self) -> str:
        if not self.has_next():
            raise EOFError("End of input reached")

        result = self.buffer
        self.update_buffer()
        assert result is not None
        return result

    # Allows to check the next line without advancing stdin.
    def peek(self) -> str:
        if not self.has_next():
            raise EOFError("Cannot peek past EOF.")
        assert self.buffer is not None
        return self.buffer

    # Returns the current line.
    def line(self) -> int:
        return self.current_line


def skip_initial_fields(reader):
    while True:
        if not reader.has_next():
            debug("EOF reached while skipping initial fields.")
            # End of file reached, no packages.
            break
        if whitespace.match(reader.peek()) or property.match(reader.peek()):
            # Line is part of the initial fields, consume and continue.
            debug(f"Skipping initial line '{reader.peek()}'")
            reader.next()
            continue
        # Line is not part of the initial fields. Must be a package.
        debug(f"Line '{reader.peek()}' not an initial field, stopping.")
        break


def parse_name(reader) -> str:
    while True:
        if not reader.has_next():
            raise ValueError("Unexpected while parsing name.")
        line = reader.next()
        if not property.match(line):
            raise ValueError(
                f"Expected property, found '{line}' at line {reader.line}."
            )
        match = name_property.match(line)
        if not match:
            # Skip other properties.
            continue

        # Found our name!
        return match.group(1).replace("-", "_")


def parse_sdist(reader: StdinReader) -> Optional[tuple[str, str]]:
    debug("Parsing sdist entry.")
    while True:
        if not reader.has_next():
            raise ValueError("Unexpected EOF while parsing sdist.")
        if reader.peek() == "[[package]]":
            debug("New package found, aborting processing of current entry.")
            return None

        line = reader.next()
        match = sdist_property.match(line)
        if not match:
            # Other property, continue
            continue

        return (match.group(1), match.group(2))


def parse_dependency_details(reader: StdinReader) -> None:
    debug("Parsing dependency details.")
    name = parse_name(reader)
    sdist = parse_sdist(reader)
    if sdist is None:
        return

    (url, hash) = sdist
    print(f"""\
  resource "{name}" do
    url "{url}"
    sha256 "{hash}"
  end
""")

    # Skip anything else that is part of this dependency. We do this the simple
    # way here. In practice, we would have to parse things like brackets that
    # span multiple lines.
    debug("Skipping rest of dependency fields.")
    while reader.has_next() and (not reader.peek() == "[[package]]"):
        debug(f"Skipping line '{reader.peek()}'.")
        reader.next()


def parse_dependency(reader: StdinReader) -> None:
    header = reader.next()
    if not header == "[[package]]":
        raise ValueError(
            f"Expected package header at line {reader.line()}, found '{header}'."
        )
    parse_dependency_details(reader)


def read_lockfile(reader: StdinReader) -> None:
    debug("Parsing lockfile from stdin.")
    skip_initial_fields(reader)
    while reader.has_next():
        parse_dependency(reader)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert dependencies in a uv.lock files to Homebrew Formula format."
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        required=False,
        help="Print debug output to stderr.",
    )
    args = parser.parse_args()
    global verbose
    verbose = args.verbose
    read_lockfile(StdinReader())


if __name__ == "__main__":
    main()
