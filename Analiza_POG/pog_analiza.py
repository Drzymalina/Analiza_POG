from qgis.PyQt.QtWidgets import QAction
from .dialog import POGAnalizaDialog

class POGAnaliza:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction("Analiza POG", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&Analiza POG", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&Analiza POG", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dialog is None:
            self.dialog = POGAnalizaDialog(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
