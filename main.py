import sys


def main():
    for line in sys.stdin:
        line = line.rstrip("\n")
        print(f"* {line}")


if __name__ == "__main__":
    main()
