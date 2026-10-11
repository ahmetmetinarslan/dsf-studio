from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
import uuid
from PySide6.QtCore import Qt, QTimer, QUrl, QSize, QStandardPaths, Signal
from PySide6.QtGui import QAction, QIcon, QImage, QPixmap, QKeySequence, QColor
from PySide6.QtWidgets import (QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,
    QListWidget,QListWidgetItem,QAbstractItemView,QSplitter,QFormLayout,QDoubleSpinBox,QComboBox,
    QCheckBox,QGroupBox,QSlider,QProgressBar,QFileDialog,QMessageBox,QDialog,QDialogButtonBox,
    QScrollArea,QStackedWidget,QColorDialog,QToolBar)
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from .canvas import Canvas, MotionIndicator
from .model import Project, Clip, duration_frames
from .motion import MOTIONS
from .safety import SafeArea
from .workers import ImportWorker, ImageWorker, CapabilityWorker
from .jobs import RenderJob
from .persistence import save_project, load_project

STYLE="""
QMainWindow,QDialog {background:#111821;color:#e4ebf5;}
QWidget {font-family:'Segoe UI';font-size:13px;color:#e4ebf5;}
QToolBar {background:#1b2635;spacing:9px;padding:10px;border:0;}
QToolButton,QPushButton {background:#27364b;border:1px solid #354962;border-radius:6px;padding:7px 10px;}
QToolButton:hover,QPushButton:hover {background:#344a65;}
QPushButton:checked {background:#236a67;}
QPushButton:disabled,QToolButton:disabled {color:#6e7b8e;background:#202b3b;}
QPushButton#primary {background:#208a79;color:white;border:0;font-weight:600;padding:10px;}
QListWidget {background:#17212e;border:1px solid #2b3a4e;border-radius:8px;outline:0;}
QListWidget::item {padding:9px;border-bottom:1px solid #29384c;}
QListWidget::item:selected {background:#244d5c;}
QGroupBox {border:1px solid #304156;border-radius:8px;margin-top:18px;padding:15px 10px 8px;}
QGroupBox::title {subcontrol-origin:margin;left:12px;color:#9eafc6;font-weight:600;}
QComboBox,QDoubleSpinBox {background:#202d3e;border:1px solid #3b506c;border-radius:5px;padding:6px;}
QComboBox QAbstractItemView {background:#202d3e;selection-background-color:#266f77;}
QScrollArea {background:transparent;border:0;}
QScrollArea>QWidget>QWidget {background:#111821;}
QLabel#muted {color:#98a9bf;}
QProgressBar {border:0;background:#223047;border-radius:5px;text-align:center;height:20px;}
QProgressBar::chunk {background:#249e8a;border-radius:5px;}
QSlider::groove:horizontal {height:5px;background:#34475f;border-radius:2px;}
QSlider::handle:horizontal {background:#48c9b0;width:14px;margin:-5px 0;border-radius:7px;}
QStatusBar {background:#1b2635;color:#adbed0;}
QMenu {background:#202d3e;}
QMessageBox {background:#17212e;}
"""


def button(text,callback,primary=False):
    w=QPushButton(text)
    if primary:w.setObjectName("primary")
    w.clicked.connect(callback)
    return w


def spin(low,high,value,step=1,decimals=2):
    w=QDoubleSpinBox();w.setRange(low,high);w.setDecimals(decimals);w.setSingleStep(step);w.setValue(value)
    return w


class ClipList(QListWidget):
    filesDropped=Signal(list)
    beforeReorder=Signal()
    reordered=Signal()

    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setIconSize(QSize(112,63));self.setSpacing(2)

    def dragEnterEvent(self,e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
        else: super().dragEnterEvent(e)

    def dragMoveEvent(self,e):
        if e.mimeData().hasUrls():e.acceptProposedAction()
        else:super().dragMoveEvent(e)

    def dropEvent(self,e):
        if e.mimeData().hasUrls():
            self.filesDropped.emit([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]);e.acceptProposedAction()
        else:
            self.beforeReorder.emit();super().dropEvent(e);self.reordered.emit()


class SettingsDialog(QDialog):
    def __init__(self,project,parent=None):
        super().__init__(parent);self.setWindowTitle("Proje ayarları");self.resize(430,610)
        self.project=project.snapshot();layout=QVBoxLayout(self);form=QFormLayout();layout.addLayout(form)
        self.fps=QComboBox();self.fps.addItems(["25","50"]);self.fps.setCurrentText(str(project.fps));form.addRow("Kare hızı",self.fps)
        self.zoom=spin(100,125,project.maxZoom*100);self.zoom.setSuffix(" %");form.addRow("Azami büyütme",self.zoom)
        self.profile=QComboBox();self.profile.addItems(["EBU grafik · %5","EBU aksiyon · %3,5","Özel"])
        self.profile.setCurrentIndex({"ebu_graphics":0,"ebu_action":1}.get(project.safeArea.preset,2));form.addRow("Güvenli alan",self.profile)
        self.margins=[]
        for label,value in zip(("Sol pay","Sağ pay","Üst pay","Alt pay"),(project.safeArea.left,project.safeArea.right,project.safeArea.top,project.safeArea.bottom)):
            w=spin(0,44,value*100,.5);w.setSuffix(" %");self.margins.append(w);form.addRow(label,w)
        self.profile.currentIndexChanged.connect(self.profile_changed)
        self.profile_changed(self.profile.currentIndex(),False)
        self.color=button(project.background,self.pick_color);form.addRow("Saydam görsel zemini",self.color)
        note=QLabel("Her kenarın payı ayrı uygulanır. Hesapta ayrıca 2 piksel yuvarlama payı kullanılır.");note.setWordWrap(True);note.setObjectName("muted");layout.addWidget(note)
        box=QGroupBox("Otomatik dağıtımda izin verilen hareketler");b=QVBoxLayout(box);self.allowed={}
        for k,label in MOTIONS.items():
            w=QCheckBox(label);w.setChecked(k in project.allowedMotions);self.allowed[k]=w;b.addWidget(w)
        layout.addWidget(box)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Uygula");buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Vazgeç")
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

    def profile_changed(self,index,reset=True):
        for w in self.margins:
            w.setEnabled(index==2)
            if index<2 and reset:w.setValue(5 if index==0 else 3.5)

    def pick_color(self):
        c=QColorDialog.getColor(QColor(self.color.text()),self,"Opak zemin rengi")
        if c.isValid():self.color.setText(c.name())

    def values(self):
        return (int(self.fps.currentText()),self.zoom.value()/100,self.color.text(),
                SafeArea(["ebu_graphics","ebu_action","custom"][self.profile.currentIndex()],*[w.value()/100 for w in self.margins]),
                [k for k,w in self.allowed.items() if w.isChecked()])


class MainWindow(QMainWindow):
    def __init__(self,data_dir=None,check_tools=True):
        super().__init__();self.setWindowTitle("DSF Studio");self.resize(1480,900);self.setMinimumSize(1100,720)
        self.setStyleSheet(STYLE);self.setAcceptDrops(True)
        self.project=Project();self.path=None;self.dirty=False;self.revision=0
        self.undo_stack=[];self.redo_stack=[];self.thumbs={};self.images=OrderedDict()
        self.importer=None;self.loader=None;self.job=None;self.close_pending=False;self.capability_ok=False
        self.data_dir=Path(data_dir or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
        self.data_dir.mkdir(parents=True,exist_ok=True);self.recovery=self.data_dir/"recovery.dsfproj"
        self.build_ui()
        self.autosave=QTimer(self);self.autosave.setInterval(30000);self.autosave.timeout.connect(self.save_recovery);self.autosave.start()
        if check_tools:
            self.checker=CapabilityWorker(self);self.checker.checked.connect(self.tools_checked);self.checker.start()
        else:self.capability_ok=True

    def build_ui(self):
        bar=QToolBar();bar.setMovable(False);self.addToolBar(bar)
        for title,callback,key in [("Yeni",self.new_project,"Ctrl+N"),("Aç",self.open_project,"Ctrl+O"),("Kaydet",self.save,"Ctrl+S"),
            ("Görsel Ekle",self.choose_images,"Ctrl+I"),("Geri al",self.undo,"Ctrl+Z"),("Yinele",self.redo,"Ctrl+Y"),("Proje ayarları",self.settings,"")]:
            action=QAction(title,self);action.triggered.connect(callback)
            if key:action.setShortcut(QKeySequence(key))
            bar.addAction(action)
        save_as=QAction("Farklı kaydet",self);save_as.setShortcut(QKeySequence("Ctrl+Shift+S"));save_as.triggered.connect(lambda:self.save(True));self.addAction(save_as)
        bar.addSeparator();self.export_button=button("MP4 Oluştur",self.export,True);bar.addWidget(self.export_button)
        container=QWidget();self.setCentralWidget(container);outer=QVBoxLayout(container);outer.setContentsMargins(16,12,16,12)
        heading=QHBoxLayout();title=QLabel("DSF STUDIO");title.setStyleSheet("font-size:22px;font-weight:700;letter-spacing:2px;");heading.addWidget(title)
        tagline=QLabel("Haber görsellerine kontrollü hareket");tagline.setObjectName("muted");heading.addWidget(tagline);heading.addStretch()
        self.summary=QLabel("1920 × 1080  •  25 fps  •  Sessiz MP4");heading.addWidget(self.summary);outer.addLayout(heading)
        splitter=QSplitter(Qt.Orientation.Horizontal);outer.addWidget(splitter,1)
        left=QWidget();lv=QVBoxLayout(left);lv.setContentsMargins(0,8,10,0)
        self.count_label=QLabel("GÖRSELLER · 0");lv.addWidget(self.count_label)
        self.list=ClipList();lv.addWidget(self.list,1)
        self.list.currentItemChanged.connect(lambda *_:self.selection_changed())
        self.list.itemSelectionChanged.connect(self.selection_count)
        self.list.filesDropped.connect(self.import_paths);self.list.beforeReorder.connect(self.begin_change);self.list.reordered.connect(self.reorder)
        row=QHBoxLayout()
        for label,fn in [("↑",lambda:self.move(-1)),("↓",lambda:self.move(1)),("Çoğalt",self.duplicate),("Sil",self.remove)]:row.addWidget(button(label,fn))
        lv.addLayout(row);lv.addWidget(button("Yeniden dağıt",self.redistribute));lv.addWidget(button("Seçili kilitlerini değiştir",self.toggle_lock))
        hint=QLabel("Ctrl / Shift ile çoklu seçim.\nSıralamak için kartları sürükleyin.");hint.setObjectName("muted");lv.addWidget(hint);splitter.addWidget(left)
        center=QWidget();cv=QVBoxLayout(center);cv.setContentsMargins(8,8,8,0)
        top=QHBoxLayout();self.view_mode=QComboBox();self.view_mode.addItems(["Hareket kadrajı","Korunacak alan çiz","Odak noktası seç"])
        self.view_mode.currentIndexChanged.connect(self.set_mode);top.addWidget(self.view_mode)
        self.guides=QCheckBox("Kılavuzlar");self.guides.setChecked(True);self.guides.toggled.connect(self.toggle_guides);top.addWidget(self.guides);top.addStretch();cv.addLayout(top)
        self.canvas=Canvas();self.canvas.regionAdded.connect(self.add_region);self.canvas.focusPicked.connect(self.pick_focus)
        self.video=QVideoWidget();self.stack=QStackedWidget();self.stack.addWidget(self.canvas);self.stack.addWidget(self.video);cv.addWidget(self.stack,1)
        self.player=QMediaPlayer(self);self.player.setVideoOutput(self.video)
        self.player.positionChanged.connect(self.play_position);self.player.errorOccurred.connect(lambda *_:self.statusBar().showMessage("Önizleme oynatılamadı: "+self.player.errorString()))
        self.slider=QSlider(Qt.Orientation.Horizontal);self.slider.setRange(0,199);self.slider.valueChanged.connect(self.scrub);cv.addWidget(self.slider)
        row=QHBoxLayout();self.time_label=QLabel("00:00 / 00:00");row.addWidget(self.time_label);row.addStretch()
        row.addWidget(button("Kadraj",self.show_canvas));row.addWidget(button("Duraklat / sürdür",self.pause_play));cv.addLayout(row)
        row=QHBoxLayout();row.addWidget(button("▶ Seçili önizle",lambda:self.preview(False,False)));row.addWidget(button("1080p kontrol",lambda:self.preview(False,True)));row.addWidget(button("▶ Tüm proje",lambda:self.preview(True,False)));cv.addLayout(row)
        self.result=QLabel("Görselleri ekleyerek başlayın.");self.result.setWordWrap(True);self.result.setMinimumHeight(52);cv.addWidget(self.result)
        caption=QLabel("Alan çizme ve odak seçiminde kaynak görsel gösterilir. Kılavuzlar videoya eklenmez.");caption.setWordWrap(True);caption.setObjectName("muted");cv.addWidget(caption);splitter.addWidget(center)
        scroll=QScrollArea();scroll.setWidgetResizable(True);right=QWidget();rv=QVBoxLayout(right);rv.setContentsMargins(10,8,0,0)
        self.selection_label=QLabel("KLİP AYARLARI");rv.addWidget(self.selection_label)
        group=QGroupBox("Süre ve hareket");form=QFormLayout(group)
        self.duration=spin(1,120,8,.04);self.duration.setSuffix(" sn");form.addRow("Süre",self.duration)
        self.motion=QComboBox()
        for k,v in MOTIONS.items():self.motion.addItem(v,k)
        self.motion.addItem("Otomatik","auto");form.addRow("Hareket",self.motion)
        self.motion_demo=MotionIndicator();form.addRow(self.motion_demo)
        self.motion.currentIndexChanged.connect(lambda:self.motion_demo.set_kind(self.motion.currentData()))
        self.amount=spin(0,25,8,.5);self.amount.setSuffix(" %");form.addRow("Hareket miktarı",self.amount)
        self.easing=QComboBox();self.easing.addItem("Doğrusal","linear");self.easing.addItem("Yumuşak","smoothstep");form.addRow("Hareket eğrisi",self.easing)
        self.locked=QCheckBox("Otomatik dağıtımda kilitle");form.addRow(self.locked);rv.addWidget(group)
        self.direction_hint=QLabel("Kamera sola giderken görüntü sağa akar. Miktar hareket mesafesidir; süre hareketin zamanını belirler.");self.direction_hint.setWordWrap(True);self.direction_hint.setObjectName("muted");rv.addWidget(self.direction_hint)
        group=QGroupBox("Odak ve içerik koruması");form=QFormLayout(group)
        self.fx=spin(0,100,50);self.fy=spin(0,100,50);self.fx.setSuffix(" %");self.fy.setSuffix(" %")
        form.addRow("Odak X",self.fx);form.addRow("Odak Y",self.fy)
        self.protect=QCheckBox("İşaretli alanları koru");self.protect.setChecked(True);form.addRow(self.protect)
        self.regions_label=QLabel("0 korunacak alan");form.addRow(self.regions_label)
        form.addRow(button("+ Kaynakta alan çiz",lambda:self.view_mode.setCurrentIndex(1)))
        form.addRow(button("Son alanı kaldır",self.pop_region));form.addRow(button("Tüm alanları temizle",self.clear_regions));rv.addWidget(group)
        rv.addWidget(button("Seçili klibe uygula",lambda:self.apply(False),True));rv.addWidget(button("Seçililere uygula",lambda:self.apply(True)))
        rv.addWidget(button("Korunan alanları seçililere kopyala",self.copy_regions));rv.addWidget(button("Dosyayı yeniden bağla",self.relink))
        self.source_info=QLabel("");self.source_info.setWordWrap(True);self.source_info.setObjectName("muted");rv.addWidget(self.source_info);rv.addStretch()
        scroll.setWidget(right);splitter.addWidget(scroll);splitter.setSizes([290,800,310]);splitter.setCollapsible(0,False);splitter.setCollapsible(1,False);splitter.setCollapsible(2,False)
        row=QHBoxLayout();self.progress=QProgressBar();self.progress.setValue(0);row.addWidget(self.progress,1);self.cancel_button=button("İşlemi iptal et",self.cancel_job);self.cancel_button.setEnabled(False);row.addWidget(self.cancel_button);outer.addLayout(row)
        self.statusBar().showMessage("Video araçları denetleniyor…")

    def tools_checked(self,ok,text):
        self.capability_ok=ok;self.statusBar().showMessage("Hazır · yerel ve çevrimdışı" if ok else text)

    def current(self):
        item=self.list.currentItem()
        return next((c for c in self.project.clips if item and c.id==item.data(Qt.ItemDataRole.UserRole)),None)

    def selected(self):
        ids={x.data(Qt.ItemDataRole.UserRole) for x in self.list.selectedItems()}
        return [c for c in self.project.clips if c.id in ids]

    def invalidate(self):
        self.revision+=1;self.dirty=True;self.player.stop();self.player.setSource(QUrl());self.stack.setCurrentWidget(self.canvas)
        self.setWindowTitle("DSF Studio · "+self.project.name+" *")

    def begin_change(self):
        self.undo_stack.append(self.project.snapshot());self.undo_stack=self.undo_stack[-40:];self.redo_stack.clear();self.invalidate()

    def undo(self):
        if self.importer and self.importer.isRunning():self.statusBar().showMessage("Önce görsel eklemenin bitmesini bekleyin.");return
        if not self.undo_stack:return
        self.redo_stack.append(self.project.snapshot());self.project=self.undo_stack.pop();self.invalidate();self.refresh()

    def redo(self):
        if self.importer and self.importer.isRunning():self.statusBar().showMessage("Önce görsel eklemenin bitmesini bekleyin.");return
        if not self.redo_stack:return
        self.undo_stack.append(self.project.snapshot());self.project=self.redo_stack.pop();self.invalidate();self.refresh()

    def refresh(self,select_id=None):
        selected={c.id for c in self.selected()};old=self.current();select_id=select_id or (old.id if old else None)
        self.list.blockSignals(True);self.list.clear()
        for i,c in enumerate(self.project.clips):
            plan=c.motionResolved;status=c.mediaError or (plan.message if plan else "Hareket atanmadı")
            motion=MOTIONS.get(plan.kind if plan else c.motionRequested,"Otomatik")
            text=f"{i+1:02d}   {Path(c.sourcePath).name}\n{c.durationFrames/self.project.fps:g} sn · {motion}{' · KİLİTLİ' if c.locked else ''}\n{status}"
            item=QListWidgetItem(text);item.setData(Qt.ItemDataRole.UserRole,c.id);item.setToolTip(text)
            if c.id in self.thumbs:item.setIcon(self.thumbs[c.id])
            self.list.addItem(item)
            if c.id in selected:item.setSelected(True)
        # setCurrentRow with NoUpdate preserves multi-selection.
        row=next((i for i,c in enumerate(self.project.clips) if c.id==select_id),0 if self.project.clips else -1)
        from PySide6.QtCore import QItemSelectionModel
        self.list.setCurrentRow(row,QItemSelectionModel.SelectionFlag.NoUpdate)
        if not selected and row>=0:self.list.item(row).setSelected(True)
        self.list.blockSignals(False)
        self.count_label.setText(f"GÖRSELLER · {len(self.project.clips)}")
        self.summary.setText(f"1920 × 1080  •  {self.project.fps} fps  •  {self.project.total_frames/self.project.fps:g} sn  •  Sessiz")
        self.selection_changed();self.selection_count()

    def selection_count(self):
        self.selection_label.setText(f"KLİP AYARLARI · {len(self.list.selectedItems())} seçili")

    def selection_changed(self):
        c=self.current();self.canvas.clip=c;self.canvas.safe=self.project.safeArea;self.canvas.frame=0
        self.show_canvas();self.slider.blockSignals(True);self.slider.setRange(0,c.durationFrames-1 if c else 0);self.slider.setValue(0);self.slider.blockSignals(False)
        if c:
            self.duration.setValue(c.durationFrames/self.project.fps);self.duration.setSingleStep(1/self.project.fps)
            self.motion.setCurrentIndex(self.motion.findData(c.motionRequested));self.amount.setValue(c.amount*100)
            self.easing.setCurrentIndex(self.easing.findData(c.easing));self.locked.setChecked(c.locked);self.protect.setChecked(c.protectContent)
            self.fx.setValue(c.focus[0]*100);self.fy.setValue(c.focus[1]*100)
            self.regions_label.setText(f"{len(c.protectedRegions)} korunacak alan")
            self.result.setText(c.mediaError or (c.motionResolved.message if c.motionResolved else "Hareket atanmadı"))
            self.source_info.setText(f"{c.sourceWidth} × {c.sourceHeight}\n"+"\n".join(c.notes))
            self.load_canvas()
        else:self.canvas.image=QImage();self.result.setText("Görselleri ekleyerek başlayın.")
        self.update_time();self.canvas.update()

    def load_canvas(self):
        c=self.current()
        if not c:return
        if c.id in self.images:
            self.canvas.image=self.images[c.id];self.images.move_to_end(c.id);self.canvas.update();return
        self.canvas.image=QImage();self.canvas.update()
        if self.loader and self.loader.isRunning():return
        self.loader=ImageWorker(c.id,c.sourcePath,self.project.background,self)
        self.loader.loaded.connect(self.image_loaded);self.loader.finished.connect(self.load_pending);self.loader.start()

    def load_pending(self):
        c=self.current()
        if c and c.id not in self.images and not c.mediaError:QTimer.singleShot(0,self.load_canvas)

    def image_loaded(self,clip_id,data,error):
        if data:
            im=QImage.fromData(data);self.images[clip_id]=im
            while len(self.images)>8:self.images.popitem(last=False)
            self.thumbs[clip_id]=QIcon(QPixmap.fromImage(im.scaled(160,90,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)))
        c=next((c for c in self.project.clips if c.id==clip_id),None)
        if error and c:c.mediaError=error
        if self.current() and self.current().id==clip_id:
            self.canvas.image=self.images.get(clip_id,QImage());self.canvas.update()
            if error:self.result.setText(error)

    def choose_images(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Görselleri ekle","","Görseller (*.jpg *.jpeg *.png)")
        if paths:self.import_paths(paths)

    def import_paths(self,paths):
        if self.importer and self.importer.isRunning():self.statusBar().showMessage("Görsel ekleme işleminin bitmesini bekleyin.");return
        paths=[p for p in paths if Path(p).suffix.lower() in (".jpg",".jpeg",".png")]
        if not paths:return
        self.begin_change();self.importer=ImportWorker(paths,self.project.fps,self.project.background,self)
        self.importer.item.connect(self.import_item);self.importer.done.connect(lambda:self.statusBar().showMessage("Görseller eklendi; korunan alanları kontrol edin."));self.importer.start()

    def import_item(self,c,thumb,preview):
        self.invalidate()
        self.project.resolve(c);self.project.clips.append(c)
        if thumb:self.thumbs[c.id]=QIcon(QPixmap.fromImage(QImage.fromData(thumb)))
        if preview:
            self.images[c.id]=QImage.fromData(preview)
            while len(self.images)>8:self.images.popitem(last=False)
        self.refresh(self.current().id if self.current() else c.id)

    def dragEnterEvent(self,e):
        if e.mimeData().hasUrls():e.acceptProposedAction()

    def dropEvent(self,e):
        self.import_paths([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]);e.acceptProposedAction()

    def reorder(self):
        by_id={c.id:c for c in self.project.clips};self.project.clips=[by_id[self.list.item(i).data(Qt.ItemDataRole.UserRole)] for i in range(self.list.count())];self.refresh()

    def move(self,direction):
        selected={c.id for c in self.selected()}
        if not selected:return
        self.begin_change();indices=range(len(self.project.clips)) if direction<0 else range(len(self.project.clips)-1,-1,-1)
        for i in indices:
            j=i+direction
            if self.project.clips[i].id in selected and 0<=j<len(self.project.clips) and self.project.clips[j].id not in selected:
                self.project.clips[i],self.project.clips[j]=self.project.clips[j],self.project.clips[i]
        self.refresh()

    def duplicate(self):
        ids={c.id for c in self.selected()}
        if not ids:return
        self.begin_change();clips=[]
        for c in self.project.clips:
            clips.append(c)
            if c.id in ids:
                other=deepcopy(c);other.id=uuid.uuid4().hex;clips.append(other)
                if c.id in self.thumbs:self.thumbs[other.id]=self.thumbs[c.id]
        self.project.clips=clips;self.refresh()

    def remove(self):
        ids={c.id for c in self.selected()}
        if ids:self.begin_change();self.project.clips=[c for c in self.project.clips if c.id not in ids];self.refresh()

    def apply(self,batch=False):
        clips=self.selected() if batch else [self.current()]
        if not clips or clips[0] is None:return
        backup=self.project.snapshot();self.begin_change()
        try:
            auto=[]
            for c in clips:
                c.durationFrames=duration_frames(self.duration.value(),self.project.fps);c.amount=self.amount.value()/100
                c.motionRequested=self.motion.currentData();c.easing=self.easing.currentData();c.focus=(self.fx.value()/100,self.fy.value()/100)
                c.locked=self.locked.isChecked();c.protectContent=self.protect.isChecked()
                if c.motionRequested=="auto":
                    if c.locked and c.motionResolved:self.project.resolve(c)
                    else:auto.append(c.id)
                else:self.project.resolve(c)
            if auto:self.project.redistribute(set(auto))
        except Exception as e:self.project=backup;self.error(str(e))
        self.refresh()

    def redistribute(self):
        if not self.project.clips:return
        self.begin_change()
        try:self.project.redistribute({c.id for c in self.selected()} if len(self.selected())>1 else None)
        except Exception as e:self.error(str(e))
        self.refresh()

    def toggle_lock(self):
        if not self.selected():return
        self.begin_change()
        for c in self.selected():c.locked=not c.locked
        self.refresh()

    def set_mode(self,index):
        self.canvas.mode=["frame","region","focus"][index];self.show_canvas();self.canvas.update()

    def toggle_guides(self,checked):self.canvas.guides=checked;self.canvas.update()

    def add_region(self,region):
        c=self.current()
        if c:self.begin_change();c.protectedRegions.append(region);self.project.resolve(c);self.refresh()

    def pick_focus(self,x,y):
        c=self.current()
        if c:self.begin_change();c.focus=(x,y);self.project.resolve(c);self.refresh()

    def pop_region(self):
        c=self.current()
        if c and c.protectedRegions:self.begin_change();c.protectedRegions.pop();self.project.resolve(c);self.refresh()

    def clear_regions(self):
        c=self.current()
        if c and c.protectedRegions:self.begin_change();c.protectedRegions=[];self.project.resolve(c);self.refresh()

    def copy_regions(self):
        current=self.current()
        if not current:return
        self.begin_change()
        for c in self.selected():c.protectedRegions=deepcopy(current.protectedRegions);self.project.resolve(c)
        self.refresh()

    def settings(self):
        if self.importer and self.importer.isRunning():self.statusBar().showMessage("Önce görsel eklemenin bitmesini bekleyin.");return
        dialog=SettingsDialog(self.project,self)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        self.begin_change();fps,zoom,bg,safe,allowed=dialog.values();old_fps=self.project.fps
        self.project.fps=fps;self.project.maxZoom=zoom;self.project.background=bg;self.project.safeArea=safe;self.project.allowedMotions=allowed
        for c in self.project.clips:c.durationFrames=duration_frames(c.durationFrames/old_fps,fps);self.project.resolve(c)
        self.images.clear();self.refresh()

    def scrub(self,k):
        if self.stack.currentWidget()==self.video:
            self.player.setPosition(round(k/self.project.fps*1000))
        else:self.canvas.frame=k;self.canvas.update()
        self.update_time()

    def update_time(self):
        fps=self.project.fps;self.time_label.setText(f"{self.slider.value()/fps:.2f} / {(self.slider.maximum()+1)/fps:.2f} sn · kare {self.slider.value()+1}")

    def play_position(self,ms):
        if self.stack.currentWidget()!=self.video:return
        self.slider.blockSignals(True);self.slider.setValue(round(ms*self.project.fps/1000));self.slider.blockSignals(False);self.update_time()

    def show_canvas(self):
        self.player.pause();self.stack.setCurrentWidget(self.canvas)
        if hasattr(self,"slider"):
            c=self.current()
            if c:self.slider.setRange(0,c.durationFrames-1)

    def pause_play(self):
        if self.player.source().isEmpty():return
        self.stack.setCurrentWidget(self.video)
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.player.pause()
        else:self.player.play()

    def preview(self,all_clips,full):
        p=self.project.snapshot()
        if not all_clips:
            if not self.current():return
            p.clips=[deepcopy(self.current())]
        self.start_job(p,self.data_dir/"previews"/"preview.mp4",1920 if full else 960,1080 if full else 540,True)

    def export(self):
        if self.job and self.job.isRunning():return
        if not self.project.clips:return
        path,_=QFileDialog.getSaveFileName(self,"Tek MP4 oluştur",str(Path(self.path).with_suffix(".mp4")) if self.path else "Haber DSF.mp4","MP4 video (*.mp4)")
        if path:self.start_job(self.project,Path(path),1920,1080,False)

    def start_job(self,project,path,width,height,preview):
        if self.importer and self.importer.isRunning():self.statusBar().showMessage("Önce görsellerin hazırlanmasını bekleyin.");return
        if self.job and self.job.isRunning():self.statusBar().showMessage("Bir video işi zaten çalışıyor.");return
        if not self.capability_ok:self.error("Video araçları hazır değil. Durum çubuğundaki hatayı kontrol edin.");return
        self.player.stop();self.player.setSource(QUrl());self.stack.setCurrentWidget(self.canvas)
        revision=self.revision;self.job=RenderJob(project,path,width,height,preview,self)
        self.job.progress.connect(self.job_progress);self.job.failed.connect(self.error);self.job.cancelled.connect(lambda:self.statusBar().showMessage("İşlem iptal edildi. Önceki çıktı korundu."))
        self.job.succeeded.connect(lambda path,data:self.job_success(path,data,preview,revision,project.total_frames))
        self.job.finished.connect(self.job_finished);self.cancel_button.setEnabled(True);self.export_button.setEnabled(False);self.progress.setValue(0);self.job.start()

    def job_progress(self,value,text):self.progress.setValue(value);self.statusBar().showMessage(text)

    def job_success(self,path,data,preview,revision,frames):
        if preview:
            if revision!=self.revision:self.statusBar().showMessage("Ayarlar değişti; güncel önizlemeyi yeniden oluşturun.");return
            self.slider.setRange(0,frames-1);self.player.setSource(QUrl.fromLocalFile(path));self.stack.setCurrentWidget(self.video);self.player.play()
            self.statusBar().showMessage("Önizleme oynatılıyor · kılavuzlar videoda yok")
        else:self.statusBar().showMessage("MP4 tamamlandı ve doğrulandı: "+path)

    def job_finished(self):
        self.cancel_button.setEnabled(False);self.export_button.setEnabled(True)
        if self.close_pending:QTimer.singleShot(0,self.close)

    def cancel_job(self):
        if self.job and self.job.isRunning():self.job.requestInterruption();self.statusBar().showMessage("İşlem durduruluyor…")

    def error(self,text):QMessageBox.warning(self,"DSF Studio",text)

    def maybe_save(self):
        if self.importer and self.importer.isRunning():self.statusBar().showMessage("Önce görsel eklemenin bitmesini bekleyin.");return False
        if not self.dirty:return True
        answer=QMessageBox.question(self,"Kaydedilmemiş proje","Değişiklikler kaydedilsin mi?",QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        if answer==QMessageBox.StandardButton.Cancel:return False
        if answer==QMessageBox.StandardButton.Save:return self.save()
        return True

    def new_project(self):
        if not self.maybe_save():return
        self.project=Project();self.path=None;self.dirty=False;self.undo_stack.clear();self.redo_stack.clear();self.images.clear();self.thumbs.clear();self.revision+=1;self.player.setSource(QUrl());self.refresh();self.clear_recovery()

    def open_project(self):
        if not self.maybe_save():return
        path,_=QFileDialog.getOpenFileName(self,"Proje aç","","DSF projesi (*.dsfproj)")
        if path:self.load_path(path)

    def load_path(self,path,recovered=False):
        try:p=load_project(path)
        except Exception as e:self.error(str(e));return
        self.project=p;self.path=None if recovered else str(path);self.dirty=recovered;self.undo_stack.clear();self.redo_stack.clear();self.images.clear();self.thumbs.clear();self.revision+=1;self.player.setSource(QUrl());self.refresh()
        self.setWindowTitle("DSF Studio · "+p.name+(" *" if recovered else ""))
        if p.clips and not (self.importer and self.importer.isRunning()):
            self.importer=ImportWorker(list(dict.fromkeys(c.sourcePath for c in p.clips)),p.fps,p.background,self)
            self.importer.item.connect(self.hydrate_item);self.importer.start()

    def hydrate_item(self,new,thumb,preview):
        for c in self.project.clips:
            if c.sourcePath!=new.sourcePath:continue
            if thumb:self.thumbs[c.id]=QIcon(QPixmap.fromImage(QImage.fromData(thumb)))
            if new.mediaError:c.mediaError=new.mediaError
            elif c.sourceFingerprint and c.sourceFingerprint.get("sha256")!=new.sourceFingerprint.get("sha256"):
                c.mediaError="Kaynak içeriği değişmiş — yeniden bağlayıp korunan alanları kontrol edin."
            if preview:
                self.images[c.id]=QImage.fromData(preview)
                while len(self.images)>8:self.images.popitem(last=False)
        self.refresh()

    def save(self,save_as=False):
        path=self.path
        if save_as or not path:
            path,_=QFileDialog.getSaveFileName(self,"Projeyi kaydet",path or "Haber DSF.dsfproj","DSF projesi (*.dsfproj)")
            if not path:return False
            if Path(path).suffix.lower()!=".dsfproj":
                self.error("Proje dosyasının adı .dsfproj uzantısıyla bitmelidir.");return False
        try:save_project(self.project,path)
        except Exception as e:self.error(str(e));return False
        self.path=path;self.dirty=False;self.setWindowTitle("DSF Studio · "+self.project.name);self.clear_recovery();self.statusBar().showMessage("Proje kaydedildi.");return True

    def save_recovery(self):
        if self.dirty and self.project.clips:
            try:save_project(self.project,self.recovery)
            except Exception as e:self.statusBar().showMessage("Kurtarma kaydı yazılamadı: "+str(e))

    def clear_recovery(self):
        try:self.recovery.unlink(missing_ok=True)
        except OSError:pass

    def offer_recovery(self):
        if self.recovery.exists():
            if QMessageBox.question(self,"Proje kurtarma","Kaydedilmemiş bir kurtarma projesi bulundu. Açılsın mı?")==QMessageBox.StandardButton.Yes:self.load_path(self.recovery,True)

    def relink(self):
        c=self.current()
        if not c:return
        path,_=QFileDialog.getOpenFileName(self,"Kaynak görseli yeniden bağla",c.sourcePath,"Görseller (*.jpg *.jpeg *.png)")
        if not path:return
        if self.importer and self.importer.isRunning():return
        self.begin_change();clip_id=c.id
        worker=ImportWorker([path],self.project.fps,self.project.background,self);self.importer=worker
        def linked(new,thumb,preview):
            target=next((c for c in self.project.clips if c.id==clip_id),None)
            if not target:return
            if new.mediaError:self.error(new.mediaError);return
            target.sourcePath=new.sourcePath;target.sourceWidth=new.sourceWidth;target.sourceHeight=new.sourceHeight
            target.sourceFingerprint=new.sourceFingerprint;target.notes=new.notes;target.mediaError=""
            self.images.pop(clip_id,None);self.image_loaded(clip_id,preview,"");self.project.resolve(target);self.refresh()
            self.statusBar().showMessage("Kaynak bağlandı. Korunan alanların yeni içerikle eşleştiğini kontrol edin.")
        worker.item.connect(linked);worker.start()

    def closeEvent(self,event):
        if self.job and self.job.isRunning():
            answer=QMessageBox.question(self,"İşlem sürüyor","Video işlemi iptal edilip uygulama kapatılsın mı?")
            if answer==QMessageBox.StandardButton.Yes:self.close_pending=True;self.cancel_job()
            event.ignore();return
        if not self.maybe_save():event.ignore();return
        if self.loader and self.loader.isRunning():self.loader.wait(5000)
        if hasattr(self,"checker") and self.checker.isRunning():self.checker.wait(15000)
        self.player.stop();self.clear_recovery();event.accept()
