
cmake_minimum_required(VERSION 3.0 FATAL_ERROR)
project(mso5000)

cmake_policy(SET CMP0078 NEW)
cmake_policy(SET CMP0086 NEW)

#shared library
set (LIB mso5000)

#local sources and headers
file(GLOB SRC ${PROJECT_SOURCE_DIR}/src/*.cxx)
include_directories(${PROJECT_SOURCE_DIR}/include)

#ROOT
find_package(ROOT REQUIRED COMPONENTS Core RIO)
include(${ROOT_USE_FILE})

#SWIG
find_package(SWIG REQUIRED)
include(${SWIG_USE_FILE})

find_package(PythonLibs)
include_directories(${PYTHON_INCLUDE_PATH})

set_source_files_properties(mso5000.i PROPERTIES CPLUSPLUS ON)

swig_add_library(${LIB} TYPE SHARED LANGUAGE python SOURCES ${SRC} mso5000.i)
swig_link_libraries(${LIB} ${PYTHON_LIBRARIES} ${ROOT_LIBRARIES})

