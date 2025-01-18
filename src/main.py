#!/usr/bin/env python3
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

# Adicionar o diretório src ao PYTHONPATH
src_dir = Path(__file__).resolve().parent
sys.path.append(str(src_dir))

from gui.main_window import MainWindow

def setup_app_style(app):
    """Configura o estilo global da aplicação"""
    app.setStyle('Fusion')
    
    # Estilo global da aplicação
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f0f0;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding: 10px;
        }
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QLineEdit {
            padding: 5px;
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        QComboBox {
            padding: 5px;
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        QListWidget {
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        QStatusBar {
            background-color: #f8f8f8;
        }
    """)

def setup_app_settings():
    """Configura as informações básicas da aplicação"""
    QSettings.setDefaultFormat(QSettings.IniFormat)
    settings = QSettings("config.ini", QSettings.IniFormat)
    settings.setFallbacksEnabled(False)
    return settings

def main():
    # Criar aplicação
    app = QApplication(sys.argv)
    
    # Configurar estilo e settings
    setup_app_style(app)
    settings = setup_app_settings()
    
    # Criar e mostrar a janela principal
    window = MainWindow(settings)
    window.show()
    
    # Executar aplicação
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())