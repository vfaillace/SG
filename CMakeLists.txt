cmake_minimum_required(VERSION 3.15)
project(NetworkVisualization VERSION 1.0.0 LANGUAGES CXX)

# Ensure proper Visual Studio configuration
if(MSVC)
    add_compile_options(/W4 /MP)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
endif()

# Set C++ standard and enforce it
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Enable folder organization in IDE
set_property(GLOBAL PROPERTY USE_FOLDERS ON)

# Handle vcpkg integration
if(DEFINED ENV{VCPKG_ROOT} AND NOT DEFINED CMAKE_TOOLCHAIN_FILE)
    set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
        CACHE STRING "Vcpkg toolchain file")
endif()

# Find required packages with version checks
find_package(Python3 3.11 COMPONENTS Interpreter Development REQUIRED)
find_package(OpenGL REQUIRED)
find_package(glfw3 CONFIG REQUIRED)
find_package(imgui CONFIG REQUIRED)
find_package(implot CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(SQLite3 REQUIRED)

# Define source files
set(SOURCES
    main.cpp
    # Add other source files here
)

# Create executable
add_executable(${PROJECT_NAME} ${SOURCES})

# Set output directories
set_target_properties(${PROJECT_NAME} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/Debug"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/Release"
)

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE
    ${Python3_INCLUDE_DIRS}
    ${SQLite3_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Link libraries
target_link_libraries(${PROJECT_NAME} PRIVATE
    Python3::Python
    OpenGL::GL
    glfw
    imgui::imgui
    implot::implot
    nlohmann_json::nlohmann_json
    SQLite::SQLite3
    ws2_32
    comctl32
)

# Copy Python runtime
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${Python3_RUNTIME_LIBRARY_RELEASE}
        $<TARGET_FILE_DIR:${PROJECT_NAME}>
)

# Function to copy files with error checking
function(copy_project_file filename)
    if(EXISTS "${CMAKE_SOURCE_DIR}/${filename}")
        add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${CMAKE_SOURCE_DIR}/${filename}"
                "$<TARGET_FILE_DIR:${PROJECT_NAME}>/${filename}"
            COMMENT "Copying ${filename}"
        )
    else()
        message(WARNING "Required file not found: ${filename}")
    endif()
endfunction()

# Copy required Python scripts and models
set(REQUIRED_FILES
    simulation_script.py
    prediction_script.py
    decision_tree_model.pkl
    isolation_forest_model.pkl
    random_forest_model.pkl
    kmeans_model.pkl
    SimComponents.py
)

foreach(file ${REQUIRED_FILES})
    copy_project_file(${file})
endforeach()

# Set PYTHONPATH
if(WIN32)
    set_property(TARGET ${PROJECT_NAME} PROPERTY 
        VS_DEBUGGER_ENVIRONMENT "PYTHONPATH=${CMAKE_BINARY_DIR}")
else()
    set_property(TARGET ${PROJECT_NAME} PROPERTY 
        ENVIRONMENT "PYTHONPATH=${CMAKE_BINARY_DIR}")
endif()

# Installation rules
install(TARGETS ${PROJECT_NAME}
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

# Copy dependencies to install directory
install(FILES ${REQUIRED_FILES} DESTINATION bin)