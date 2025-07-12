#!/bin/bash

# Install dependencies
pip install --target build/usr/lib/python3 requests

# Create AppDir structure
mkdir -p build/usr/bin
mkdir -p build/usr/share/applications
mkdir -p build/usr/share/icons

# Copy scripts
cp src/snpedia_scraper.py build/usr/bin/
cp src/gui.py build/usr/bin/snpedia-scraper-gui
chmod +x build/usr/bin/snpedia-scraper-gui

# Create desktop entry
cat > build/usr/share/applications/snpedia-scraper.desktop << DESKTOP
[Desktop Entry]
Type=Application
Name=SNPedia Scraper
Exec=snpedia-scraper-gui
Icon=snpedia-scraper
Categories=Science;Biology;
DESKTOP

# Create AppRun
cat > build/AppRun << APPRUN
#!/bin/bash
export PYTHONPATH="\$APPDIR/usr/lib/python3:\$PYTHONPATH"
exec python3 "\$APPDIR/usr/bin/snpedia-scraper-gui"
APPRUN
chmod +x build/AppRun

# Download appimagetool if not present
if [ ! -f appimagetool-x86_64.AppImage ]; then
    wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

# Build AppImage
./appimagetool-x86_64.AppImage build SNPediaScraper.AppImage
