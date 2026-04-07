@echo off
echo Cerrando instancias de WSL y Docker...
wsl --shutdown

echo Preparando script de reduccion para DiskPart...
echo select vdisk file="C:\Users\Lenovo\AppData\Local\Docker\wsl\disk\docker_data.vhdx" > compact.txt
echo attach vdisk readonly >> compact.txt
echo compact vdisk >> compact.txt
echo detach vdisk >> compact.txt

echo Ejecutando DiskPart (esto puede tardar unos minutos)...
diskpart /s compact.txt

echo Limpiando archivos temporales...
del compact.txt

echo.
echo Proceso finalizado. El espacio en C:\ deberia haber aumentado.
pause
