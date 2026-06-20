cmake_minimum_required(VERSION 3.8)
project(tdcr_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  urdf
  assets
  launch
  rviz
  meshes
  DESTINATION share/${PROJECT_NAME}
  OPTIONAL
)

install(FILES
  robot.urdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
