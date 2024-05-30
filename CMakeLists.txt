cmake_minimum_required(VERSION 3.10)

# Project name
project(InstrumentCluster)

# C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Find SDL2 and SDL2_ttf
find_package(SDL2 REQUIRED)

# Include SDL2 and SDL2_ttf directories
include_directories(/usr/include/SDL2)

# Source files
set(SOURCES main.cpp)

# Add executable
add_executable(InstrumentCluster ${SOURCES})

# Link SDL2 and SDL2_ttf libraries
target_link_libraries(InstrumentCluster -lSDL2 -lSDL2_ttf -lSDL2_gfx -lstdc++fs -lpthread)
