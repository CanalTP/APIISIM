from setuptools import find_packages, setup

excluded_packages = ['apiisim.tests',
                     # Uncomment the line below to NOT install stub MIS APIs
                     # 'apiisim.mis_translator.mis_api.stub'
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
