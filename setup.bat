@echo off
setlocal enabledelayedexpansion

echo Starting Network Visualization Project Setup...

:: Create a log file
set "LOGFILE=%CD%\setup_log.txt"
echo Setup started at %DATE% %TIME% > %LOGFILE%

:: Function to log messages
call :log "Checking system requirements..."

:: Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    call :log "ERROR: Administrative privileges required. Please run as administrator."
    echo Please run this script as administrator.
    pause
    exit /b 1
)

:: Check Windows version
ver | findstr /i "10\.0\." >nul
if %errorlevel% neq 0 (
    call :log "WARNING: This script is optimized for Windows 10 and above."
    echo WARNING: This script is optimized for Windows 10 and above.
    timeout /t 5
)

:: Check Python installation and version
call :log "Checking Python installation..."
python --version > temp.txt 2>&1
set /p PYTHON_VERSION=<temp.txt
del temp.txt
echo Found Python: %PYTHON_VERSION%
echo %PYTHON_VERSION% | findstr /i "3.11" >nul
if %errorlevel% neq 0 (
    call :log "WARNING: Python 3.11 is recommended. Found: %PYTHON_VERSION%"
    echo WARNING: Python 3.11 is recommended. Current version may cause compatibility issues.
    choice /C YN /M "Continue anyway?"
    if !errorlevel! equ 2 exit /b 1
)

:: Check Git installation
call :log "Checking Git installation..."
git --version > temp.txt 2>&1
if %errorlevel% neq 0 (
    call :log "ERROR: Git is not installed."
    echo Git is not installed. Please install Git from https://git-scm.com/download/win
    echo After installing Git, please restart this script.
    pause
    exit /b 1
)
set /p GIT_VERSION=<temp.txt
del temp.txt
echo Found Git: %GIT_VERSION%

:: Check CMake installation
call :log "Checking CMake installation..."
cmake --version > temp.txt 2>&1
if %errorlevel% neq 0 (
    call :log "ERROR: CMake is not installed."
    echo CMake is not installed. Please install CMake from https://cmake.org/download/
    echo After installing CMake, please restart this script.
    pause
    exit /b 1
)
set /p CMAKE_VERSION=<temp.txt
del temp.txt
echo Found CMake: %CMAKE_VERSION%

:: Check Visual Studio installation using vswhere
call :log "Checking Visual Studio installation..."
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
    set "VSWHERE=%ProgramFiles%\Microsoft Visual Studio\Installer\vswhere.exe"
)

if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
        set "VS_PATH=%%i"
    )
    if defined VS_PATH (
        :: Check for specific VS version and initialize environment
        if exist "!VS_PATH!\Common7\Tools\VsDevCmd.bat" (
            echo Found Visual Studio at: !VS_PATH!
            call "!VS_PATH!\Common7\Tools\VsDevCmd.bat" >nul 2>&1
            call :log "Visual Studio environment initialized"
        ) else (
            call :log "WARNING: VsDevCmd.bat not found in expected location"
        )
    )
) else (
    :: Try to find VS2022 Build Tools directly
    if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" (
        call "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1
        call :log "Found and initialized VS2022 Build Tools"
    ) else if exist "%ProgramFiles%\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" (
        call "%ProgramFiles%\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1
        call :log "Found and initialized VS2022 Build Tools"
    ) else (
        :: Final check for cl.exe in PATH
        where cl.exe >nul 2>&1
        if !errorlevel! neq 0 (
            call :log "ERROR: Visual Studio C++ compiler not found."
            echo Visual Studio with C++ components is required.
            echo Please install Visual Studio with C++ development tools or Visual Studio Build Tools.
            echo Download from: https://visualstudio.microsoft.com/downloads/
            pause
            exit /b 1
        )
    )
)

:: Verify compiler is accessible
cl.exe >nul 2>&1
if %errorlevel% equ 9009 (
    call :log "ERROR: Visual Studio environment is not properly initialized."
    echo Failed to initialize Visual Studio environment.
    echo Please ensure Visual Studio or Build Tools are properly installed with C++ components.
    pause
    exit /b 1
)

echo Visual Studio C++ compiler found and environment initialized.

:: Set up vcpkg with retry mechanism
call :log "Setting up vcpkg..."
set RETRY_COUNT=0
:VCPKG_RETRY
if not exist vcpkg (
    echo Cloning vcpkg...
    git clone https://github.com/Microsoft/vcpkg.git
    if %errorlevel% neq 0 (
        set /a RETRY_COUNT+=1
        if !RETRY_COUNT! lss 3 (
            call :log "WARNING: vcpkg clone failed. Retrying..."
            timeout /t 5
            goto VCPKG_RETRY
        )
        call :log "ERROR: Failed to clone vcpkg after 3 attempts."
        echo Failed to clone vcpkg. Please check your internet connection.
        pause
        exit /b 1
    )
)

:: Bootstrap vcpkg
cd vcpkg
call :log "Bootstrapping vcpkg..."
call bootstrap-vcpkg.bat
if %errorlevel% neq 0 (
    call :log "ERROR: vcpkg bootstrap failed."
    cd ..
    echo Failed to bootstrap vcpkg.
    pause
    exit /b 1
)
cd ..

:: Set and persist VCPKG_ROOT
set "VCPKG_ROOT=%CD%\vcpkg"
setx VCPKG_ROOT "%VCPKG_ROOT%" >nul
call :log "Set VCPKG_ROOT to %VCPKG_ROOT%"

:: Install packages with retry mechanism
call :log "Installing vcpkg packages..."
set RETRY_COUNT=0
:PACKAGE_RETRY
"%VCPKG_ROOT%\vcpkg" install opengl glfw3 imgui[opengl3-binding,glfw-binding] implot nlohmann-json sqlite3 --triplet x64-windows
if %errorlevel% neq 0 (
    set /a RETRY_COUNT+=1
    if !RETRY_COUNT! lss 3 (
        call :log "WARNING: Package installation failed. Retrying..."
        timeout /t 5
        goto PACKAGE_RETRY
    )
    call :log "ERROR: Failed to install packages after 3 attempts."
    echo Failed to install required packages.
    pause
    exit /b 1
)

:: Install Python requirements with error handling
call :log "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    call :log "ERROR: Failed to install Python packages."
    echo Failed to install Python packages. Please check requirements.txt
    pause
    exit /b 1
)

call :log "Copying ImGui files..."
set "IMGUI_SOURCE=%VCPKG_ROOT%\installed\x64-windows"
set "IMGUI_PACKAGE_SOURCE=%VCPKG_ROOT%\packages\imgui_x64-windows"

echo Searching for ImGui files...

:: Array of possible file locations and destinations
set "files_to_copy="
set "files_to_copy=!files_to_copy! include\imgui_impl_glfw.h:imgui_impl_glfw.h"
set "files_to_copy=!files_to_copy! include\imgui_impl_opengl3.h:imgui_impl_opengl3.h"

:: Try multiple possible locations
for %%F in (%files_to_copy%) do (
    for /f "tokens=1,2 delims=:" %%a in ("%%F") do (
        set "found=0"
        
        :: Try installed directory
        if exist "%IMGUI_SOURCE%\%%a" (
            echo Found %%b in installed directory
            copy "%IMGUI_SOURCE%\%%a" "%%b" >nul 2>&1
            set "found=1"
        )
        
        :: Try package directory
        if !found! equ 0 if exist "%IMGUI_PACKAGE_SOURCE%\%%a" (
            echo Found %%b in package directory
            copy "%IMGUI_PACKAGE_SOURCE%\%%a" "%%b" >nul 2>&1
            set "found=1"
        )
        
        :: Try share directory
        if !found! equ 0 if exist "%IMGUI_SOURCE%\share\imgui\%%~nxb" (
            echo Found %%b in share directory
            copy "%IMGUI_SOURCE%\share\imgui\%%~nxb" "%%b" >nul 2>&1
            set "found=1"
        )
        
        if !found! equ 0 (
            echo WARNING: Could not find %%b in any standard location
            call :log "WARNING: Could not find %%b"
        )
    )
)

:: Verify if we have all necessary files for compilation
set "missing_files="
for %%F in (
    imgui_impl_glfw.h
    imgui_impl_opengl3.h
) do (
    if not exist "%%F" (
        set "missing_files=!missing_files! %%F"
    )
)

if not "!missing_files!"=="" (
    echo.
    echo WARNING: Some ImGui files could not be found:!missing_files!
    echo This might cause compilation issues.
    echo.
    choice /C YN /M "Do you want to continue anyway?"
    if !errorlevel! equ 2 (
        call :log "Setup cancelled by user due to missing ImGui files"
        exit /b 1
    )
)

call :log "Setting up build directory..."
if exist build (
    echo Cleaning build directory...
    
    :: First attempt: Basic removal
    rmdir /s /q build >nul 2>&1
    
    :: If first attempt failed, try closing any processes that might lock files
    if exist build (
        echo First cleanup attempt failed, trying to force close any locks...
        :: Try to force close any open handles to the directory
        handle.exe build -accepteula >nul 2>&1
        if !errorlevel! neq 0 (
            :: If handle.exe isn't available, try taskkill on common processes
            taskkill /F /IM NetworkVisualization.exe >nul 2>&1
            taskkill /F /IM cl.exe >nul 2>&1
            taskkill /F /IM link.exe >nul 2>&1
            taskkill /F /IM cmake.exe >nul 2>&1
        )
        
        :: Second attempt after closing processes
        rmdir /s /q build >nul 2>&1
    )
    
    :: If directory still exists, try using del with force
    if exist build (
        echo Second cleanup attempt failed, trying forced deletion...
        del /f /s /q build\* >nul 2>&1
        rmdir /s /q build >nul 2>&1
    )
    
    :: If still exists, try using robocopy to empty directory
    if exist build (
        echo Third cleanup attempt failed, trying robocopy method...
        if not exist empty mkdir empty
        robocopy empty build /MIR /NFL /NDL /NJH /NJS /nc /ns /np >nul 2>&1
        rmdir /s /q build >nul 2>&1
        rmdir /s /q empty >nul 2>&1
    )
    
    :: Final check
    if exist build (
        call :log "WARNING: Could not fully clean build directory."
        echo WARNING: Build directory could not be fully cleaned.
        echo This might be because some files are in use.
        echo.
        choice /C YN /M "Do you want to continue anyway?"
        if !errorlevel! equ 2 (
            call :log "Setup cancelled by user due to build directory cleaning failure"
            exit /b 1
        )
    ) else (
        echo Build directory successfully cleaned.
    )
)

:: Create new build directory
mkdir build
if !errorlevel! neq 0 (
    call :log "ERROR: Failed to create build directory."
    echo Failed to create build directory.
    exit /b 1
)
cd build

:: Configure CMake
call :log "Configuring CMake..."
cmake -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%/scripts/buildsystems/vcpkg.cmake" ^
      -DCMAKE_PREFIX_PATH="%VCPKG_ROOT%/installed/x64-windows" ^
      -DCMAKE_BUILD_TYPE=Release ..
if %errorlevel% neq 0 (
    call :log "ERROR: CMake configuration failed."
    cd ..
    echo CMake configuration failed.
    pause
    exit /b 1
)

:: Build project
call :log "Building project..."
cmake --build . --config Release --parallel
if %errorlevel% neq 0 (
    call :log "ERROR: Build failed."
    cd ..
    echo Build failed.
    pause
    exit /b 1
)

cd ..

if not exist "build\Release\NetworkVisualization.exe" (
    call :log "ERROR: Build completed but executable not found."
    echo ERROR: Build completed but executable not found.
    echo Press any key to exit...
    pause >nul
    exit /b 1
) else (
    call :log "Setup completed successfully!"
    echo.
    echo ========================================
    echo Setup completed successfully!
    echo.
    echo Your executable is located at:
    echo build\Release\NetworkVisualization.exe
    echo.
    echo You can now:
    echo 1. Run the application directly from build\Release\NetworkVisualization.exe
    echo 2. Copy the Release folder to your desired location
    echo.
    echo Note: Keep the Release folder intact as it contains required DLLs
    echo ========================================
    echo.
)

exit /b 0

:log
echo %~1 >> %LOGFILE%
goto :eof