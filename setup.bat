@echo off
setlocal enabledelayedexpansion

echo Setting up Network Visualization Project...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.11 and add it to your PATH.
    exit /b 1
)

:: Check if Git is installed
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Git is not installed or not in PATH. Please install Git and add it to your PATH.
    exit /b 1
)

:: Check if CMake is installed
cmake --version >nul 2>&1
if %errorlevel% neq 0 (
    echo CMake is not installed or not in PATH. Please install CMake and add it to your PATH.
    exit /b 1
)

:: Clone vcpkg if it doesn't exist
if not exist vcpkg (
    echo Cloning vcpkg...
    git clone https://github.com/Microsoft/vcpkg.git
    if %errorlevel% neq 0 (
        echo Failed to clone vcpkg.
        exit /b 1
    )
)

:: Bootstrap vcpkg
echo Bootstrapping vcpkg...
cd vcpkg
call bootstrap-vcpkg.bat
if %errorlevel% neq 0 (
    echo Failed to bootstrap vcpkg.
    exit /b 1
)
cd ..

:: Set VCPKG_ROOT environment variable
set "VCPKG_ROOT=%CD%\vcpkg"
setx VCPKG_ROOT "%VCPKG_ROOT%"

:: Install required packages
echo Installing required packages...
"%VCPKG_ROOT%\vcpkg" install opengl glfw3 imgui[opengl3-binding,glfw-binding] implot nlohmann-json sqlite3 --triplet x64-windows
if %errorlevel% neq 0 (
    echo Failed to install required packages.
    exit /b 1
)

:: Install required Python packages
echo Installing required Python packages...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install required Python packages.
    exit /b 1
)

:: Copy ImGui backend files
echo Copying ImGui backend files...
copy "%VCPKG_ROOT%\installed\x64-windows\include\imgui_impl_glfw.h" .
copy "%VCPKG_ROOT%\installed\x64-windows\include\imgui_impl_opengl3.h" .
copy "%VCPKG_ROOT%\installed\x64-windows\lib\imgui_impl_glfw.cpp" .
copy "%VCPKG_ROOT%\installed\x64-windows\lib\imgui_impl_opengl3.cpp" .

:: Clean build directory
echo Cleaning build directory...
if exist build rmdir /s /q build
mkdir build
cd build

:: Configure with CMake
echo Configuring with CMake...
cmake -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%/scripts/buildsystems/vcpkg.cmake" -DCMAKE_PREFIX_PATH="%VCPKG_ROOT%/installed/x64-windows" ..
if %errorlevel% neq 0 (
    echo Failed to configure with CMake.
    exit /b 1
)

:: Build the project
echo Building the project...
cmake --build . --config Release
if %errorlevel% neq 0 (
    echo Failed to build the project.
    exit /b 1
)

echo Setup completed successfully!
echo You can now run the application by executing: .\Release\NetworkVisualization.exe

endlocal