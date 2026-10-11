import sys
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint,Qt
from PySide6.QtTest import QTest
from dsf.ui import MainWindow

root=Path(__file__).resolve().parents[1]
app=QApplication([]);w=MainWindow(root/"artifacts"/"ui_quick",check_tools=False);w.show()
errors=[];w.error=errors.append
w.import_paths([str(root/"examples"/"assets"/"haber_01_örnek.png")])
start=time.monotonic()
while w.importer.isRunning() or len(w.project.clips)!=1:
    QTest.qWait(20)
    assert time.monotonic()-start<20
QTest.qWait(100)
w.view_mode.setCurrentIndex(1);r=w.canvas.viewport()
a=QPoint(round(r.x()+r.width()*.2),round(r.y()+r.height()*.2));b=QPoint(round(r.x()+r.width()*.7),round(r.y()+r.height()*.7))
QTest.mousePress(w.canvas,Qt.MouseButton.LeftButton,pos=a);QTest.mouseMove(w.canvas,b,100);QTest.mouseRelease(w.canvas,Qt.MouseButton.LeftButton,pos=b)
assert len(w.current().protectedRegions)==1
w.motion.setCurrentIndex(w.motion.findData("pan_left"));w.apply(False)
assert w.motion_demo.kind=="pan_left" and w.current().motionResolved.kind=="pan_left"
w.undo();assert w.current().motionResolved.kind=="zoom_in"
w.redo();assert w.current().motionResolved.kind=="pan_left"
w.dirty=False;w.import_item(w.current().__class__(str(root/"examples"/"assets"/"haber_02_örnek.png")),b"",b"")
assert w.dirty and not errors
keep=root/"artifacts"/"ui_quick"/"should_keep.dsfproj";keep.write_bytes(b"keep-original")
with patch("dsf.ui.QFileDialog.getSaveFileName",return_value=(str(keep.with_suffix(".txt")),"")):
    assert not w.save(True)
assert keep.read_bytes()==b"keep-original" and "uzantısıyla" in errors.pop()
w.dirty=False;w.close()
print("Final GUI: rectangle drawing, animated direction, apply, undo/redo, import dirty state, overwrite-target safety PASS")
