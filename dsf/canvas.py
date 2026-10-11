import math
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QImage
from PySide6.QtWidgets import QWidget
from .motion import Transform, preset
from .safety import SafeArea


class Canvas(QWidget):
    regionAdded=Signal(object)
    focusPicked=Signal(float,float)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setMinimumSize(420,260)
        self.image=QImage()
        self.clip=None
        self.safe=SafeArea()
        self.frame=0
        self.mode="frame"
        self.guides=True
        self.anchor=None
        self.drag=None

    def viewport(self):
        w=min(self.width()-32,(self.height()-40)*16/9)
        h=w*9/16
        return QRectF((self.width()-w)/2,(self.height()-h)/2,w,h)

    def transform(self):
        if self.mode!="frame" or not self.clip or not self.clip.motionResolved: return Transform()
        return self.clip.motionResolved.at(self.frame,self.clip.durationFrames)

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor("#10151e"))
        r=self.viewport()
        p.fillRect(r,QColor("#060a0f"))
        if self.image.isNull():
            p.setPen(QColor("#9baac0"))
            p.drawText(r,Qt.AlignmentFlag.AlignCenter,"Görselleri buraya sürükleyin\nveya Görsel Ekle düğmesini kullanın")
            return
        tr=self.transform()
        p.save(); p.setClipRect(r)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(QRectF(r.x()+tr.tx*r.width(),r.y()+tr.ty*r.height(),r.width()*tr.z,r.height()*tr.z),self.image)
        if self.guides:
            s=self.safe
            # Round toward the safe area, not outward.
            left,top=math.ceil(s.left*1920)/1920,math.ceil(s.top*1080)/1080
            right,bottom=math.floor((1-s.right)*1920)/1920,math.floor((1-s.bottom)*1080)/1080
            safe_rect=QRectF(r.x()+left*r.width(),r.y()+top*r.height(),(right-left)*r.width(),(bottom-top)*r.height())
            p.setPen(QPen(QColor("#ffd166"),1,Qt.PenStyle.DashLine)); p.drawRect(safe_rect)
            p.drawText(safe_rect.topLeft()+QPointF(6,16),"GÜVENLİ ALAN · yalnızca düzenleyici")
            if self.clip:
                for u0,v0,u1,v1 in self.clip.protectedRegions:
                    x0,y0=tr.point(u0,v0);x1,y1=tr.point(u1,v1)
                    box=QRectF(r.x()+x0*r.width(),r.y()+y0*r.height(),(x1-x0)*r.width(),(y1-y0)*r.height())
                    p.fillRect(box,QColor(62,211,180,32));p.setPen(QPen(QColor("#3ed3b4"),2));p.drawRect(box)
                x,y=tr.point(*self.clip.focus)
                q=QPointF(r.x()+x*r.width(),r.y()+y*r.height())
                p.setPen(QPen(QColor("#ffffff"),1));p.drawEllipse(q,5,5)
                p.drawLine(q+QPointF(-10,0),q+QPointF(10,0));p.drawLine(q+QPointF(0,-10),q+QPointF(0,10))
        if self.anchor is not None and self.drag is not None:
            p.setPen(QPen(QColor("#3ed3b4"),2));p.drawRect(QRectF(self.anchor,self.drag).normalized())
        p.restore()

    def normalized(self,point):
        r=self.viewport()
        return max(0.,min(1.,(point.x()-r.x())/r.width())),max(0.,min(1.,(point.y()-r.y())/r.height()))

    def mousePressEvent(self,event):
        if not self.clip or not self.viewport().contains(event.position()): return
        if event.button()!=Qt.MouseButton.LeftButton: return
        if self.mode=="focus": self.focusPicked.emit(*self.normalized(event.position()))
        elif self.mode=="region":
            self.anchor=event.position();self.drag=self.anchor;self.update()

    def mouseMoveEvent(self,event):
        if self.anchor is not None:
            r=self.viewport();q=event.position()
            self.drag=QPointF(max(r.left(),min(r.right(),q.x())),max(r.top(),min(r.bottom(),q.y())))
            self.update()


    def mouseReleaseEvent(self,event):
        if self.anchor is not None:
            a=self.normalized(self.anchor);b=self.normalized(self.drag or event.position())
            box=(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))
            self.anchor=self.drag=None
            if box[2]-box[0]>.002 and box[3]-box[1]>.002: self.regionAdded.emit(box)
            self.update()


class MotionIndicator(QWidget):
    """Tiny looping camera-direction demonstration using the common model."""
    def __init__(self,parent=None):
        super().__init__(parent);self.setFixedHeight(52);self.kind="zoom_in";self.frame=0
        self.timer=QTimer(self);self.timer.setInterval(65);self.timer.timeout.connect(self.advance);self.timer.start()

    def advance(self):
        self.frame=(self.frame+1)%100
        if self.isVisible():self.update()

    def set_kind(self,kind):self.kind=kind;self.frame=0;self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r=QRectF(4,4,78,44);p.fillRect(r,QColor("#0c131c"));p.save();p.setClipRect(r)
        t=preset(self.kind if self.kind!="auto" else "zoom_in",.2,max_zoom=1.25).at(self.frame,100)
        p.setPen(QPen(QColor("#4a6b81"),1))
        for v in (.15,.35,.55,.75,.95):
            x,y=t.point(v,v);p.drawLine(QPointF(r.x()+x*r.width(),r.top()),QPointF(r.x()+x*r.width(),r.bottom()))
            p.drawLine(QPointF(r.left(),r.y()+y*r.height()),QPointF(r.right(),r.y()+y*r.height()))
        x,y=t.point(.38,.35);p.fillRect(QRectF(r.x()+x*r.width(),r.y()+y*r.height(),r.width()*.24*t.z,r.height()*.3*t.z),QColor("#48ccb2"))
        p.restore();p.setPen(QColor("#a5b6ca"));p.drawText(QRectF(94,0,self.width()-94,52),Qt.AlignmentFlag.AlignVCenter,"Hareket yönü\nörneği")
