import sys
import os
import main

# Oculta console em Windows se rodando como .pyw nativamente
if sys.platform.startswith('win'):
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

if __name__ == "__main__":
    main.main()