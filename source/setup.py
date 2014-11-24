from setuptools import find_packages, setup

excluded_packages = ['apiisim.tests',
                     'apiisim.test_clients',
]

setup(name='apiisim',
      version='0.1',
      description='Trip planning between multiple heterogeneous'
                  'multi-modal information systems (MIS)',
      author='CanalTP',
      packages=find_packages(exclude=excluded_packages),
      package_data={'': ['*.json', '*.conf']},
      include_package_data=True
)
