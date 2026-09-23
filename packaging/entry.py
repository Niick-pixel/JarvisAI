"""PyInstaller's entry script. Everything real is in server/desktop.py, which is linted and typed."""

from server.desktop import main

raise SystemExit(main())
