import argparse
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from dsf.ui import MainWindow


def main():
    parser=argparse.ArgumentParser(description="DSF Studio")
    parser.add_argument("project",nargs="?")
    parser.add_argument("--smoke-test",action="store_true")
    parser.add_argument("--screenshot")
    parser.add_argument("--data-dir")
    parser.add_argument("--verify-package",metavar="OUTPUT_DIR")
    args=parser.parse_args()
    app=QApplication(sys.argv[:1]);app.setApplicationName("DSF Studio");app.setOrganizationName("DSF Studio")
    if args.verify_package:
        from dsf.packagecheck import verify
        return verify(app,args.verify_package)
    window=MainWindow(args.data_dir);window.show()
    if args.project:window.load_path(args.project)
    elif not args.smoke_test:QTimer.singleShot(500,window.offer_recovery)
    if args.smoke_test:
        def finish():
            if window.importer and window.importer.isRunning():
                QTimer.singleShot(100,finish);return
            if args.screenshot:window.grab().save(args.screenshot)
            window.dirty=False;window.close();app.quit()
        QTimer.singleShot(4000,finish)
    return app.exec()


if __name__=="__main__":sys.exit(main())
