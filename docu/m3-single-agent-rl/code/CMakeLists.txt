include_directories(${CMAKE_BINARY_DIR}/include)

build_lib_example(
  NAME congestiq
  SOURCE_FILES congestiq-sim.cc my-gym-env.cc
  LIBRARIES_TO_LINK
    ${libapplications}
    ${libcore}
    ${libflow-monitor}
    ${libinternet}
    ${libopengym}
    ${libpoint-to-point}
)