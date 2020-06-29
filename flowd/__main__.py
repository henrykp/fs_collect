import logging

from flowd.supervisor import Supervisor


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    s = Supervisor()
    s.configure()
    s.run()


if __name__ == "__main__":
    main()
