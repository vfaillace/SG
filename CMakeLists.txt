cmake_minimum_required(VERSION 3.10)
project(NetworkVisualization)

set(CMAKE_CXX_STANDARD 17)

# Use vcpkg toolchain file if VCPKG_ROOT is set
if(DEFINED ENV{VCPKG_ROOT} AND NOT DEFINED CMAKE_TOOLCHAIN_FILE)
  set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
      CACHE STRING "")
endif()

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(OpenGL REQUIRED)
find_package(glfw3 CONFIG REQUIRED)
find_package(imgui CONFIG REQUIRED)
find_package(implot CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(SQLite3 REQUIRED)

# Include directories
include_directories(${Python3_INCLUDE_DIRS})
include_directories(${SQLite3_INCLUDE_DIRS})

add_executable(NetworkVisualization main.cpp)

# Link libraries
target_link_libraries(NetworkVisualization PRIVATE
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

add_custom_command(TARGET NetworkVisualization POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        ${Python3_RUNTIME_LIBRARY_RELEASE}
        $<TARGET_FILE_DIR:NetworkVisualization>
)
# Copy Python script to output directory
add_custom_command(TARGET NetworkVisualization POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        ${CMAKE_SOURCE_DIR}/simulation_script.py
        $<TARGET_FILE_DIR:NetworkVisualization>/simulation_script.py
)

add_custom_command(TARGET NetworkVisualization POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        ${CMAKE_SOURCE_DIR}/prediction_script.py
        $<TARGET_FILE_DIR:NetworkVisualization>/prediction_script.py
)

add_custom_command(TARGET NetworkVisualization POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        ${CMAKE_SOURCE_DIR}/decision_tree_model.pkl
        $<TARGET_FILE_DIR:NetworkVisualization>/decision_tree_model.pkl
)

add_custom_command(TARGET NetworkVisualization POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        ${CMAKE_SOURCE_DIR}/isolation_forest_model.pkl
        $<TARGET_FILE_DIR:NetworkVisualization>/isolation_forest_model.pkl
)

add_custom_command(TARGET NetworkVisualization POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        ${CMAKE_SOURCE_DIR}/random_forest_model.pkl
        $<TARGET_FILE_DIR:NetworkVisualization>/random_forest_model.pkl
)

add_custom_command(TARGET NetworkVisualization POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        ${CMAKE_SOURCE_DIR}/SimComponents.py
        $<TARGET_FILE_DIR:NetworkVisualization>/SimComponents.py
)

# Set PYTHONPATH environment variable
if(WIN32)
  set_property(TARGET NetworkVisualization PROPERTY VS_DEBUGGER_ENVIRONMENT "PYTHONPATH=${CMAKE_BINARY_DIR}")
else()
  set_property(TARGET NetworkVisualization PROPERTY ENVIRONMENT "PYTHONPATH=${CMAKE_BINARY_DIR}")
endif()