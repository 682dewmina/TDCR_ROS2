from setuptools import find_packages, setup

package_name = 'tdcr_jacobian'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='danushkara',
    maintainer_email='danushkaradewmina2004@gmail.com',
    description='TDCR cable Jacobian and singularity monitoring package',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'jacobian_node = tdcr_jacobian.jacobian_node:main',
        ],
    },
)
