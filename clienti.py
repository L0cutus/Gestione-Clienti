#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future_builtins import *

import os
import sys
import subprocess

from PyQt4.QtCore import PYQT_VERSION_STR, QDate, QFile
from PyQt4.QtCore import QRegExp, QString, QVariant, Qt
from PyQt4.QtCore import SIGNAL, QModelIndex, QSettings
from PyQt4.QtCore import QSize, QPoint

from PyQt4.QtGui  import QApplication, QCursor, QDateEdit
from PyQt4.QtGui  import QDialog, QMainWindow, QHBoxLayout
from PyQt4.QtGui  import QLabel, QLineEdit, QMessageBox, QPixmap
from PyQt4.QtGui  import QTabWidget, QPushButton, QRegExpValidator
from PyQt4.QtGui  import QStyleOptionViewItem, QTableView, QVBoxLayout
from PyQt4.QtGui  import QDataWidgetMapper, QTextDocument, QStyle
from PyQt4.QtGui  import QColor, QBrush, QTextOption
from PyQt4.QtGui  import QItemSelectionModel,QStandardItemModel
from PyQt4.QtGui  import QAbstractItemView, QIntValidator
from PyQt4.QtGui  import QDoubleValidator, QIcon, QFileDialog

from PyQt4.QtSql  import QSqlDatabase, QSqlQuery, QSqlRelation
from PyQt4.QtSql  import QSqlRelationalDelegate, QSqlRelationalTableModel
from PyQt4.QtSql  import QSqlTableModel

from clienti_ui import Ui_MainWindow
import aboutcli

# Definizione degli 'id' usati poi come colonne nelle tabelle ecc...
CID, CRAGSOC, CIND, CPIVA, CCF, CTEL, CFAX, CCELL, CEMAIL, CNOTE = range(10)

DATEFORMAT = "dd/MM/yyyy"

__version__ = '0.2.0'

# usate per il salvataggio dei settings dell'applicazione
CLIORG = "TIME di Stefano Z."
CLIAPP = "Gestione Clienti"
CLIDOMAIN = "zamprogno.it"

class MyQSqlRelationalDelegate(QSqlRelationalDelegate):
    def __init__(self, parent=None):
        super(MyQSqlRelationalDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        if index.column() == CPIVA:
            editor = QLineEdit(parent)
            validator = QRegExpValidator(QRegExp(r"\d{11}"), self)
            editor.setValidator(validator)
            editor.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
            return editor
        else:
            return QSqlRelationalDelegate.createEditor(self, parent,
                                                    option, index)


class MainWindow(QMainWindow, Ui_MainWindow):
    '''
    Gestione Clienti v.0.2.0
    by TIME di Stefano Zamprogno
    @2009
    '''
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.setupUi(self)

        self.setupMenu()
        self.restoreWinSettings()

        self.filename = None
        self.filtered = False
        self.db = QSqlDatabase.addDatabase("QSQLITE")

        self.loadInitialFile()
        self.setupUiSignals()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            self.addCliRecord()
        elif event.key() == Qt.Key_Escape:
            self.cModel.revertAll()
            self.cModel.select()
        else:
            QMainWindow.keyPressEvent(self, event)

    def setupMenu(self):
        # AboutBox
        self.connect(self.action_About, SIGNAL("triggered()"),
                    self.showAboutBox)
        # FileNew
        self.connect(self.action_New_File, SIGNAL("triggered()"),
                    self.newFile)

        # FileLoad
        self.connect(self.action_Load_File, SIGNAL("triggered()"),
                    self.openFile)


    def showAboutBox(self):
        dlg = aboutcli.AboutBox(self)
        dlg.exec_()

    def creaStrutturaDB(self):
        query = QSqlQuery()
        if not ("clienti" in self.db.tables()):
            if not query.exec_("""CREATE TABLE clienti (
                                id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                                ragsoc VARCHAR(200) NOT NULL,
                                indirizzo VARCHAR(200) NOT NULL,
                                piva VARCHAR(15),
                                cf VARCHAR(15),
                                tel VARCHAR(30),
                                fax VARCHAR(30),
                                cell VARCHAR(30),
                                email VARCHAR(50),
                                note VARCHAR(100))"""):
                QMessageBox.warning(self, "Gestione Clienti",
                                QString("Creazione tabella clienti fallita!"))
                return False
            QMessageBox.information(self, "Gestione Clienti",
                                QString("Database Creato!"))
        return True

    def loadFile(self, fname=None):
        if fname is None:
            return
        if self.db.isOpen():
            self.db.close()
        self.db.setDatabaseName(QString(fname))
        if not self.db.open():
            QMessageBox.warning(self, "Gestione Clienti",
                                QString("Database Error: %1")
                                .arg(db.lastError().text()))
        else:
            if not self.creaStrutturaDB():
                return
            self.filename = unicode(fname)
            self.setWindowTitle("Gestione Clienti - %s" % self.filename)
            self.setupModels()
            self.setupTables()
            self.restoreTablesSettings()


    def loadInitialFile(self):
        settings = QSettings()
        fname = unicode(settings.value("Settings/lastFile").toString())
        if fname and QFile.exists(fname):
            self.loadFile(fname)


    def openFile(self):
        dir = os.path.dirname(self.filename) \
                if self.filename is not None else "."
        fname = QFileDialog.getOpenFileName(self,
                    "Gestione Clienti - Scegli database",
                    dir, "*.db")
        if fname:
            self.loadFile(fname)


    def newFile(self):
        dir = os.path.dirname(self.filename) \
                if self.filename is not None else "."
        fname = QFileDialog.getSaveFileName(self,
                    "Gestione DDT - Scegli database",
                    dir, "*.db")
        if fname:
            self.loadFile(fname)

    def restoreWinSettings(self):
        settings = QSettings()
        self.restoreGeometry(
                settings.value("MainWindow/Geometry").toByteArray())

    def restoreTablesSettings(self):
        settings = QSettings(self)
        # per la tablelview
        for column in range(1, self.cModel.columnCount()-1):
            width = settings.value("Settings/cTableView/%s" % column,
                                    QVariant(60)).toInt()[0]
            self.cTableView.setColumnWidth(column,
                                        width if width > 0 else 60)

    def closeEvent(self, event):
        settings = QSettings()
        settings.setValue("MainWindow/Geometry", QVariant(
                          self.saveGeometry()))
        if self.filename is not None:
            settings.setValue("Settings/lastFile", QVariant(self.filename))
        if self.db.isOpen():
            # salva larghezza colonne tabella
            for column in range(1, self.cModel.columnCount()-1):
                width = self.cTableView.columnWidth(column)
                if width:
                    settings.setValue("Settings/cTableView/%s" % column,
                                        QVariant(width))
            self.db.close()
            del self.db

    def setupModels(self):
        """
            Initialize all the application models
        """
        # setup clientiModel
        self.cModel = QSqlTableModel(self)
        self.cModel.setTable(QString("clienti"))
        self.cModel.setHeaderData(CID, Qt.Horizontal, QVariant("ID"))
        self.cModel.setHeaderData(CRAGSOC, Qt.Horizontal, QVariant("RagSoc"))
        self.cModel.setHeaderData(CIND, Qt.Horizontal, QVariant("Indirizzo"))
        self.cModel.setHeaderData(CPIVA, Qt.Horizontal, QVariant("PIva"))
        self.cModel.setHeaderData(CCF, Qt.Horizontal, QVariant("CF"))
        self.cModel.setHeaderData(CTEL, Qt.Horizontal, QVariant("Tel"))
        self.cModel.setHeaderData(CFAX, Qt.Horizontal, QVariant("Fax"))
        self.cModel.setHeaderData(CCELL, Qt.Horizontal, QVariant("Cell"))
        self.cModel.setHeaderData(CEMAIL, Qt.Horizontal, QVariant("Email"))
        self.cModel.setHeaderData(CNOTE, Qt.Horizontal, QVariant("Note"))
        self.cModel.select()

    def setupTables(self):
        """
            Initialize all the application tablesview
        """
        self.cTableView.setModel(self.cModel)
        self.cTableView.setItemDelegate(MyQSqlRelationalDelegate(self))
        self.cTableView.setColumnHidden(CID, True)
        self.cTableView.setWordWrap(True)
        self.cTableView.resizeRowsToContents()
        self.cTableView.setAlternatingRowColors(True)
        self.cItmSelModel = QItemSelectionModel(self.cModel)
        self.cTableView.setSelectionModel(self.cItmSelModel)
        self.cTableView.setSelectionBehavior(QTableView.SelectRows)
        self.cTableView.setSortingEnabled(True)

    def updateFilter(self):
        self.cModel.select()
        self.cTableView.setColumnHidden(CID, True)

    def applyFilter(self):
        if not self.db.isOpen():
            self.statusbar.showMessage(
                "Database non aperto...",
                5000)
            return
        filter = (  "ragsoc LIKE '%s' OR "
                    "indirizzo LIKE '%s' OR "
                    "note LIKE '%s'" %
                    ((self.filterLineEdit.text(),)*3))
        self.cModel.setFilter(filter)
        self.filtered = True
        self.updateFilter()

    def resetFilter(self):
        if not self.db.isOpen():
            self.statusbar.showMessage(
                "Database non aperto...",
                5000)
            return
        self.filtered = False
        self.filterLineEdit.setText("")
        self.cModel.setFilter("")
        self.updateFilter()

    def addCliRecord(self):
        if not self.db.isOpen():
            self.statusbar.showMessage(
                "Database non aperto...",
                5000)
            return
        customerIndex = self.cTableView.currentIndex()
        if self.filtered:
            self.resetFilter()
        self.cModel.submitAll()
        self.cModel.select()
        row = self.cModel.rowCount()
        self.cModel.insertRow(row)
        self.editindex = self.cModel.index(row, CRAGSOC)
        self.cTableView.setCurrentIndex(self.editindex)
        self.cTableView.edit(self.editindex)

    def delCliRecord(self):
        if not self.db.isOpen():
            self.statusbar.showMessage(
                "Database non aperto...",
                5000)
            return
        selrows = self.cItmSelModel.selectedRows()
        if not selrows:
            self.statusbar.showMessage(
                "No selected customers to delete...",
                5000)
            return
        if(QMessageBox.question(self, "Delete Customers",
                "Do you want to delete: {0} customer(s)?".format(len(selrows)),
                QMessageBox.Yes|QMessageBox.No) ==
                QMessageBox.No):
            return
        QSqlDatabase.database().transaction()
        query = QSqlQuery()
        query.prepare("DELETE FROM clienti WHERE id = :val")
        for i in selrows:
            if i.isValid():
                query.bindValue(":val", QVariant(i.data().toInt()[0]))
                query.exec_()
        QSqlDatabase.database().commit()
        self.cModel.select()

    def setupUiSignals(self):
        self.connect(self.addPushButton, SIGNAL("clicked()"),
                    self.addCliRecord)
        self.connect(self.delPushButton, SIGNAL("clicked()"),
                    self.delCliRecord)
        self.connect(self.filterPushButton, SIGNAL("clicked()"),
                    self.applyFilter)
        self.connect(self.resetPushButton, SIGNAL("clicked()"),
                    self.resetFilter)
        self.connect(self.filterLineEdit, SIGNAL("returnPressed()"),
                    self.applyFilter)

def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(CLIORG)
    app.setOrganizationDomain(CLIDOMAIN)
    app.setApplicationName(CLIAPP)

    form = MainWindow()
    form.show()
    app.exec_()
    del form

main()

