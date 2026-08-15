from pathlib import Path
from tempfile import NamedTemporaryFile

from qgis.PyQt.QtCore import QUrl, QVariant
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QRadioButton, QComboBox, QPushButton, QLabel, QFileDialog,
    QCheckBox, QMessageBox
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsVectorFileWriter, QgsField, QgsFeature,
    QgsCoordinateTransformContext, QgsWkbTypes
)

from .engine.core import analyse, analyse_dwz, _extract_strefy


class POGAnalizaDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Analiza POG")
        self.setMinimumWidth(760)
        self._build_ui()
        self._refresh_all()
        self._set_mode("MPZP")

    def _build_ui(self):
        root = QVBoxLayout(self)

        mode_box = QGroupBox("Tryb analizy")
        mode_l = QHBoxLayout(mode_box)
        self.rb_mpzp = QRadioButton("MPZP")
        self.rb_dwz = QRadioButton("DWZ")
        self.rb_mpzp.setChecked(True)
        mode_l.addWidget(self.rb_mpzp)
        mode_l.addWidget(self.rb_dwz)
        mode_l.addStretch()
        root.addWidget(mode_box)

        pog_box = QGroupBox("GML POG")
        pog_l = QVBoxLayout(pog_box)

        src_l = QHBoxLayout()
        self.rb_file = QRadioButton("Plik GML z dysku")
        self.rb_project = QRadioButton("Warstwy POG w bieżącym projekcie QGIS")
        self.rb_file.setChecked(True)
        src_l.addWidget(self.rb_file)
        src_l.addWidget(self.rb_project)
        src_l.addStretch()
        pog_l.addLayout(src_l)

        file_row = QHBoxLayout()
        self.file_path = QLabel("")
        self.file_path.setToolTip("")
        self.file_button = QPushButton("Wybierz plik...")
        file_row.addWidget(self.file_path, 1)
        file_row.addWidget(self.file_button)
        pog_l.addLayout(file_row)

        self.file_status = QLabel("")
        pog_l.addWidget(self.file_status)

        self.project_group = QGroupBox()
        project_form = QFormLayout(self.project_group)
        self.pog_strefy_combo = QComboBox()
        self.pog_ouz_combo = QComboBox()
        project_form.addRow("Strefy planistyczne:", self.pog_strefy_combo)
        project_form.addRow("OUZ:", self.pog_ouz_combo)
        pog_l.addWidget(self.project_group)
        root.addWidget(pog_box)

        self.mode_box = QGroupBox()
        self.mode_form = QFormLayout(self.mode_box)
        root.addWidget(self.mode_box)

        self.status = QLabel("Gotowe do analizy")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.run_btn = QPushButton("GENERUJ RAPORT")
        self.run_btn.setDefault(True)
        buttons.addWidget(self.run_btn)
        self.close_btn = QPushButton("Zamknij")
        buttons.addWidget(self.close_btn)
        root.addLayout(buttons)

        self.rb_mpzp.toggled.connect(lambda checked: checked and self._set_mode("MPZP"))
        self.rb_dwz.toggled.connect(lambda checked: checked and self._set_mode("DWZ"))
        self.rb_file.toggled.connect(self._update_pog_source)
        self.rb_project.toggled.connect(self._update_pog_source)
        self.file_button.clicked.connect(self._browse_gml)
        self.run_btn.clicked.connect(self._run)
        self.close_btn.clicked.connect(self.close)

    def _vector_layers(self):
        layers = [l for l in QgsProject.instance().mapLayers().values()
                  if isinstance(l, QgsVectorLayer)]
        return sorted(layers, key=lambda l: l.name().casefold())

    def _refresh_all(self):
        self._refresh_project_pog_layers()
        if hasattr(self, "mpzp_combo"):
            self._fill_vector_combo(self.mpzp_combo)
        if hasattr(self, "dwz_combo"):
            self._fill_vector_combo(self.dwz_combo)

    def _refresh_project_pog_layers(self):
        self.pog_strefy_combo.clear()
        self.pog_ouz_combo.clear()
        for layer in self._vector_layers():
            n = layer.name().casefold()
            if n.startswith("strefy planistyczne"):
                self.pog_strefy_combo.addItem(layer.name(), layer.id())
            if n.startswith("ouz"):
                self.pog_ouz_combo.addItem(layer.name(), layer.id())

    def _clear_form(self):
        while self.mode_form.count():
            item = self.mode_form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _set_mode(self, mode):
        self._clear_form()
        if mode == "MPZP":
            self.mode_box.setTitle("Granice MPZP")
            self.mpzp_combo = QComboBox()
            self._fill_vector_combo(self.mpzp_combo)
            self.group_field = QComboBox()
            self.group_label = QLabel("Pole grupujące MPZP:")
            self.mode_form.addRow("Warstwa granic MPZP:", self.mpzp_combo)
            self.mode_form.addRow(self.group_label, self.group_field)
            self.mpzp_combo.currentIndexChanged.connect(self._refresh_group_field)
            self._refresh_group_field()
        else:
            self.mode_box.setTitle("Tereny inwestycji DWZ")
            self.dwz_combo = QComboBox()
            self._fill_vector_combo(self.dwz_combo)
            self.id_field = QComboBox()
            self.selected_only = QCheckBox("Analizuj tylko zaznaczone obiekty")
            self.mode_form.addRow("Warstwa terenów inwestycji:", self.dwz_combo)
            self.mode_form.addRow("Pole identyfikujące teren:", self.id_field)
            self.mode_form.addRow("", self.selected_only)
            self.dwz_combo.currentIndexChanged.connect(self._refresh_id_field)
            self._refresh_id_field()
        self._update_pog_source()

    def _fill_vector_combo(self, combo):
        combo.clear()
        for layer in self._vector_layers():
            combo.addItem(layer.name(), layer.id())

    def _layer_from_combo(self, combo):
        return QgsProject.instance().mapLayer(combo.currentData())

    def _refresh_group_field(self):
        if not hasattr(self, "group_field"):
            return
        self.group_field.clear()
        layer = self._layer_from_combo(self.mpzp_combo)
        if not layer:
            return
        fields = [f.name() for f in layer.fields()]
        candidates = [f for f in fields if "mpzp" in f.casefold()]
        self.group_field.addItems(fields)
        if len(candidates) == 1:
            self.group_field.setCurrentText(candidates[0])
            self.group_field.setEnabled(False)
        else:
            self.group_field.setEnabled(True)
            if len(candidates) == 0:
                self.group_label.setToolTip(
                    f"Warstwa zawiera {layer.featureCount()} obiektów. "
                    "Nie znaleziono pola z nazwą MPZP. Wybierz pole, według którego obiekty mają zostać pogrupowane."
                )
            else:
                self.group_label.setToolTip(
                    "Znaleziono więcej niż jedno pole z nazwą MPZP. Wybierz pole ręcznie."
                )

    def _refresh_id_field(self):
        if not hasattr(self, "id_field"):
            return
        self.id_field.clear()
        layer = self._layer_from_combo(self.dwz_combo)
        if layer:
            self.id_field.addItems([f.name() for f in layer.fields()])

    def _update_pog_source(self):
        project = self.rb_project.isChecked()
        self.project_group.setVisible(project)
        self.file_path.setVisible(not project)
        self.file_button.setVisible(not project)
        self.file_status.setVisible(not project)
        if project:
            self.status.setText("Wskaż warstwy Strefy planistyczne i OUZ z bieżącego projektu.")
        else:
            if self.file_path.text():
                self.status.setText("Plik dodany. Przed analizą zostanie zweryfikowany jako GML POG.")
            else:
                self.status.setText("Wskaż plik GML POG.")

    def _browse_gml(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik GML POG", "", "Pliki GML (*.gml);;Wszystkie pliki (*)"
        )
        if not path:
            return
        if not path.casefold().endswith(".gml"):
            self.file_path.setText("")
            self.file_status.setText("Wskaż prawidłowy plik .gml")
            self.file_status.setStyleSheet("color: #b00020;")
            self.status.setText("Wskaż prawidłowy plik .gml")
            return
        self.file_path.setText(path)
        self.file_path.setToolTip(path)
        self.file_status.setText("✓ Plik dodany")
        self.file_status.setStyleSheet("color: #2e7d32;")
        self.status.setText("Plik dodany. Przed analizą zostanie zweryfikowany jako GML POG.")

    def _validate(self):
        if self.rb_file.isChecked() and not self.file_path.text():
            return "Nie wskazano pliku GML POG."
        if self.rb_project.isChecked():
            if not self.pog_strefy_combo.currentData():
                return "Nie wskazano warstwy Strefy planistyczne."
            if self.rb_dwz.isChecked() and not self.pog_ouz_combo.currentData():
                return "Nie wskazano warstwy OUZ. W trybie DWZ wybór OUZ jest obowiązkowy."

        if self.rb_mpzp.isChecked():
            if not self.mpzp_combo.currentData():
                return "Nie wskazano warstwy granic MPZP."
            if not self.group_field.currentText():
                return "Nie wskazano pola grupującego MPZP."
        else:
            if not self.dwz_combo.currentData():
                return "Nie wskazano warstwy terenów inwestycji."
            if not self.id_field.currentText():
                return "Nie wskazano pola identyfikującego teren."
            if self.selected_only.isChecked() and not self._layer_from_combo(self.dwz_combo).selectedFeatureIds():
                return "Zaznaczono opcję „Analizuj tylko zaznaczone obiekty”, ale nie zaznaczono żadnego obiektu."
        return None

    def _qgis_to_gpkg(self, layer, layer_name="mpzp_boundary", selected_fids=None):
        tmp = NamedTemporaryFile(suffix=".gpkg", delete=False)
        tmp.close()
        path = tmp.name

        source = layer

        # For DWZ preserve the original QGIS feature id in a dedicated field.
        # The GPKG writer is allowed to assign a new FID, so relying on the
        # exported GPKG FID breaks "selected only" when source FIDs are sparse.
        if layer_name == "dwz_terrain":
            selected_set = None if selected_fids is None else {int(v) for v in selected_fids}

            geometry_uri = (
                f"{QgsWkbTypes.displayString(layer.wkbType())}"
                f"?crs={layer.crs().authid()}"
            )
            mem = QgsVectorLayer(
                geometry_uri,
                "dwz_export",
                "memory"
            )
            if not mem.isValid():
                raise RuntimeError(
                    "Nie udało się utworzyć tymczasowej warstwy terenów DWZ."
                )
            prov = mem.dataProvider()

            fields = layer.fields()
            fields.append(QgsField("_source_fid", QVariant.LongLong))
            prov.addAttributes(fields)
            mem.updateFields()

            features = []
            for feat in layer.getFeatures():
                fid = int(feat.id())
                if selected_set is not None and fid not in selected_set:
                    continue

                new_feat = QgsFeature(mem.fields())
                new_feat.setGeometry(feat.geometry())
                attrs = list(feat.attributes())
                attrs.append(fid)
                new_feat.setAttributes(attrs)
                features.append(new_feat)

            if selected_set is not None and not features:
                raise ValueError("Nie znaleziono zaznaczonych obiektów w warstwie terenów inwestycji.")

            prov.addFeatures(features)
            mem.updateExtents()
            source = mem

        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName = "GPKG"
        opts.layerName = layer_name
        opts.fileEncoding = "UTF-8"

        res = QgsVectorFileWriter.writeAsVectorFormatV3(
            source, path, QgsCoordinateTransformContext(), opts
        )
        if res[0] != QgsVectorFileWriter.NoError:
            detail = str(res[1]) if len(res) > 1 else ""
            raise RuntimeError(
                "Nie udało się przygotować warstwy do analizy."
                + (f"\n{detail}" if detail else "")
            )
        return path


    def _run_dwz(self):
        self.run_btn.setEnabled(False)
        try:
            if self.rb_file.isChecked():
                gml_path=self.file_path.text()
                if not gml_path:
                    raise ValueError("Nie wskazano pliku GML POG.")
            else:
                raise ValueError(
                    "Dla trybu DWZ w tej wersji wybierz GML POG z dysku. "
                    "Obsługa warstw POG z projektu zostanie podłączona w kolejnym kroku."
                )

            terrain_layer=self._layer_from_combo(self.dwz_combo)
            if not terrain_layer:
                raise ValueError("Nie wskazano warstwy terenów inwestycji.")

            # GML validation and mandatory OUZ check.
            self.status.setText("Weryfikacja GML POG i OUZ…")
            strefy, ouz, profiles = _extract_strefy(gml_path)
            if strefy is None or len(strefy)==0:
                raise ValueError(
                    "Wybrany plik GML nie zawiera wymaganych danych POG. Wskaż prawidłowy plik GML POG."
                )
            if ouz is None or len(ouz)==0:
                raise ValueError(
                    "W POG nie wyznaczono OUZ. W trybie DWZ nie można wygenerować raportu."
                )

            selected = (
                terrain_layer.selectedFeatureIds()
                if self.selected_only.isChecked() else None
            )
            terrain_path=self._qgis_to_gpkg(
                terrain_layer,
                "dwz_terrain",
                selected_fids=selected
            )

            self.status.setText("GML POG zweryfikowany. Analizowanie terenów DWZ…")

            st_df, prof_df, ouz_df, ctrl_df = analyse_dwz(
                gml_path,
                terrain_path,
                layer="dwz_terrain",
                id_field=self.id_field.currentText(),
                selected_fids=selected
            )

            default_name=f"Analiza_POG_DWZ_{terrain_layer.name()}.xlsx"
            default_name="".join(
                ch if ch.isalnum() or ch in " _-." else "_"
                for ch in default_name
            )
            output_path,_=QFileDialog.getSaveFileName(
                self,
                "Wybierz miejsce zapisu raportu",
                str(Path.home()/"Documents"/default_name),
                "Pliki Excel (*.xlsx)"
            )
            if not output_path:
                self.status.setText("Anulowano zapis raportu.")
                return

            from .report import write_report
            out=write_report(
                st_df, prof_df, ouz_df, ctrl_df, output_path
            )

            self.status.setText(f"Raport wygenerowany: {out}")
            self._show_report_ready(out)
        except Exception as e:
            QMessageBox.critical(self,"Błąd analizy",str(e))
            self.status.setText(str(e))
        finally:
            self.run_btn.setEnabled(True)

    def _show_report_ready(self, path):
        msg = QMessageBox(self)
        msg.setWindowTitle("Analiza zakończona")
        msg.setIcon(QMessageBox.Information)
        msg.setText("Raport został wygenerowany i zapisany we wskazanym miejscu.")

        link = QUrl.fromLocalFile(str(Path(path).resolve())).toString()
        label = QLabel(
            f'<a href="{link}">Otwórz raport</a><br>'
            f'<span style="color:#666;">{Path(path).resolve()}</span>'
        )
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(
            label.textInteractionFlags()
        )
        label.linkActivated.connect(
            lambda url: QDesktopServices.openUrl(QUrl(url))
        )
        msg.layout().addWidget(label)

        open_btn = msg.addButton("Otwórz raport", QMessageBox.AcceptRole)
        msg.addButton("Zamknij", QMessageBox.RejectRole)

        msg.exec()

        if msg.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))

    def _run(self):
        err = self._validate()
        if err:
            QMessageBox.warning(self, "Nie można rozpocząć analizy", err)
            self.status.setText(err)
            return

        if not self.rb_mpzp.isChecked():
            self._run_dwz()
            return

        self.run_btn.setEnabled(False)
        try:
            self.status.setText("Weryfikacja GML POG…")
            gml_path = self.file_path.text() if self.rb_file.isChecked() else None

            if not gml_path:
                QMessageBox.information(
                    self, "Źródło POG",
                    "Na tym etapie generowanie raportu MPZP jest podłączone dla GML POG z dysku. "
                    "Obsługa warstw POG z projektu zostanie podłączona w kolejnym etapie."
                )
                return

            # Validate the selected GML as a POG before analysis.
            strefy, ouz, profiles = _extract_strefy(gml_path)
            if strefy is None or len(strefy) == 0:
                raise ValueError(
                    "Wybrany plik GML nie zawiera wymaganych danych POG. Wskaż prawidłowy plik GML POG."
                )

            self.status.setText("GML POG zweryfikowany. Analizowanie granic MPZP…")

            mpzp_layer = self._layer_from_combo(self.mpzp_combo)
            mpzp_path = self._qgis_to_gpkg(mpzp_layer)

            st_df, prof_df, ouz_df, ctrl_df, grouping_decision, _ = analyse(
                gml_path,
                mpzp_path,
                layer="mpzp_boundary",
                group_field=self.group_field.currentText()
            )

            default_name = f"Analiza_POG_{mpzp_layer.name()}.xlsx"
            default_name = "".join(
                ch if ch.isalnum() or ch in " _-." else "_"
                for ch in default_name
            )
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "Wybierz miejsce zapisu raportu",
                str(Path.home() / "Documents" / default_name),
                "Pliki Excel (*.xlsx)"
            )
            if not output_path:
                self.status.setText("Anulowano zapis raportu.")
                return

            from .report import write_report
            out = write_report(
                st_df, prof_df, ouz_df, ctrl_df,
                output_path
            )

            self.status.setText(f"Raport wygenerowany: {out}")
            self._show_report_ready(out)
        except Exception as e:
            msg = str(e)
            if "wymaganych danych POG" in msg:
                self.file_status.setText(
                    "Wybrany plik GML nie zawiera wymaganych danych POG. Wskaż prawidłowy plik GML POG."
                )
                self.file_status.setStyleSheet("color: #b00020;")
            QMessageBox.critical(self, "Błąd analizy", msg)
            self.status.setText(msg)
        finally:
            self.run_btn.setEnabled(True)
