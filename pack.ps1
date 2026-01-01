rm -r dist/pytoolbox_pack
cp -r dist/pytoolbox dist/pytoolbox_pack -Force
rm dist/pytoolbox_pack/.port
rm -r dist/pytoolbox_pack/_internal/data/*
Compress-Archive -Path dist/pytoolbox_pack/ -DestinationPath dist/pytoolbox-windows-x64.zip -Force