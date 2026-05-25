from bidi_harness.daemon import *  # noqa: F401,F403

if __name__ == "__main__":
    import asyncio
    import sys

    from bidi_harness.daemon import main_async, already_running, ipc, NAME

    if already_running():
        print(f"daemon already running on {ipc.sock_addr(NAME)}", file=sys.stderr)
        sys.exit(0)
    asyncio.run(main_async())
