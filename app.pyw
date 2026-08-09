import sys

# Oculta console em Windows se rodando como .pyw nativamente
if sys.platform == 'win32':
    try:
        import ctypes
        # Usa flag 0 (SW_HIDE) para esconder a janela do console
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

if __name__ == "__main__":
    import main
    main.main()