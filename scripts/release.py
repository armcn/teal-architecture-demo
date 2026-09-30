"""Build a release snapshot or verify its installation. Start reading here."""

import argparse

from release_tools.build import ROOT, build_snapshot
from release_tools.files import read_json
from release_tools.restore import verify_restore


def main():
    arguments = parse_arguments()
    if arguments.command == "build":
        build_snapshot(
            arguments.out,
            arguments.snapshot,
            arguments.base_url,
            arguments.source_sha,
            arguments.existing_site,
        )
    else:
        verify_restore(arguments.snapshot, online=arguments.online)


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Build and check a new snapshot")
    build.add_argument("--out", required=True)
    build.add_argument("--snapshot", required=True)
    build.add_argument("--source-sha", required=True)
    build.add_argument("--existing-site")
    build.add_argument(
        "--base-url", default=read_json(ROOT / "config.json")["depository_url"]
    )
    verify = commands.add_parser("verify", help="Restore and test a saved snapshot")
    verify.add_argument("snapshot")
    verify.add_argument("--online", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
