"""PyInstaller entry point; package imports stay absolute in frozen builds."""

from ns2pro_bridge.app import main


if __name__ == "__main__":
    main()

