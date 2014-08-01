from setuptools import find_packages, setup

setup(name='apiisim',
      version='0.1',
      description='Trip planning between multiple heterogeneous'
                  'multi-modal information systems (MIS)',
      author='CanalTP',
      packages=find_packages(exclude=['apiisim.tests',
                                      'apiisim.mis_translator.mis_api.stub']),
      package_data={'': ['*.json', '*.conf']},
      include_package_data=True
)
